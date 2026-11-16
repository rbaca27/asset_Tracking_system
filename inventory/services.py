"""Every write that changes more than one table (design decision D-02).

LoanService     checkout, return, overdue flags, clearing Repair   (US-03, US-04, US-06, US-07)
AccountService  roster import, activation, Staff role assignment   (US-02, US-08, US-09)

Each operation runs inside one database transaction and raises one named exception per blocked
case, so views only translate exceptions into messages and pytest can test the rules directly.
Operations that depend on the clock take an optional `now` so tests can pass a fixed time.
"""

import csv
import io
import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from .models import Asset, Loan, LoanEvent, Profile, RosterImport
from .permissions import ADMIN, STAFF, STUDENT


# --- Exceptions --------------------------------------------------------------


class BorrowerNotFound(Exception):
    """No active Student account matches the typed username or mock Panther ID."""


class CheckoutBlocked(Exception):
    """The asset tag is unknown or retired, the item is not Available, or it is not checked out."""


class DamageNoteRequired(Exception):
    """A return marked damaged arrived with an empty condition note."""


class RosterInvalid(Exception):
    """At least one roster row is invalid; nothing was saved."""

    def __init__(self, errors):
        super().__init__(f"{len(errors)} invalid roster row(s)")
        self.errors = errors


class ActivationFailed(Exception):
    """Wrong, used, or expired code, or no such active account. Always shown generically."""


class RoleChangeRefused(Exception):
    """A Staff role change that is not allowed (unknown user, duplicate username, ...)."""


# --- Loans -------------------------------------------------------------------


def _log(kind, asset, *, loan=None, actor=None, note="", now=None):
    return LoanEvent.objects.create(
        kind=kind, asset=asset, loan=loan, actor=actor, note=note,
        created_at=now or timezone.now(),
    )


def _lock_asset(asset_tag):
    """Lock the asset row for the rest of the transaction, or return None if the tag is unknown."""
    return (
        Asset.objects.select_for_update()
        .filter(asset_tag__iexact=asset_tag.strip())
        .first()
    )


class LoanService:
    @staticmethod
    def resolve_borrower(key):
        """Match the typed key against a username first, then a mock Panther ID (D-12).

        Only active accounts in the Student group can borrow.
        """
        key = (key or "").strip()
        if not key:
            raise BorrowerNotFound
        students = User.objects.filter(is_active=True, groups__name=STUDENT)
        borrower = students.filter(username__iexact=key).first()
        if borrower is None:
            borrower = students.filter(profile__panther_id=key).first()
        if borrower is None:
            raise BorrowerNotFound
        return borrower

    @staticmethod
    @transaction.atomic
    def checkout(staff, borrower_key, asset_tag, now=None):
        now = now or timezone.now()
        borrower = LoanService.resolve_borrower(borrower_key)
        asset = _lock_asset(asset_tag)
        if asset is None or asset.is_retired:
            raise CheckoutBlocked("Unknown asset tag.")
        if asset.status == Asset.Status.CHECKED_OUT:
            raise CheckoutBlocked(f"{asset.asset_tag} is already checked out.")
        if asset.status == Asset.Status.REPAIR:
            raise CheckoutBlocked(f"{asset.asset_tag} is in Repair and cannot be checked out.")

        loan = Loan.objects.create(
            asset=asset, borrower=borrower, checked_out_by=staff,
            checked_out_at=now, due_at=asset.due_time(now),
        )
        asset.status = Asset.Status.CHECKED_OUT
        asset.save(update_fields=["status"])
        _log(LoanEvent.Kind.CHECKOUT, asset, loan=loan, actor=staff, now=now)
        return loan

    @staticmethod
    def return_item(staff, asset_tag, damaged=False, note="", now=None):
        note = (note or "").strip()
        if damaged and not note:
            raise DamageNoteRequired
        return LoanService._close_loan(staff, asset_tag, damaged, note, now or timezone.now())

    @staticmethod
    @transaction.atomic
    def _close_loan(staff, asset_tag, damaged, note, now):
        asset = _lock_asset(asset_tag)
        loan = asset and Loan.objects.filter(asset=asset, returned_at__isnull=True).first()
        if loan is None:
            raise CheckoutBlocked("That item is not checked out.")

        loan.returned_at = now
        loan.returned_to = staff
        loan.damaged = damaged
        loan.condition_note = note
        loan.save(update_fields=["returned_at", "returned_to", "damaged", "condition_note"])

        asset.status = Asset.Status.REPAIR if damaged else Asset.Status.AVAILABLE
        asset.save(update_fields=["status"])
        _log(LoanEvent.Kind.RETURN, asset, loan=loan, actor=staff, now=now)
        if damaged:
            _log(LoanEvent.Kind.DAMAGE_TO_REPAIR, asset, loan=loan, actor=staff, note=note, now=now)
        return loan

    @staticmethod
    def overdue_loans(now=None):
        now = now or timezone.now()
        return (
            Loan.objects.filter(returned_at__isnull=True, due_at__lt=now)
            .select_related("asset", "borrower", "borrower__profile")
            .order_by("due_at")
        )

    @staticmethod
    @transaction.atomic
    def flag_overdue(now=None):
        """Log one OVERDUE_FLAG event per loan the first time it is late (D-08). Idempotent."""
        now = now or timezone.now()
        newly_late = (
            Loan.objects.select_for_update()
            .filter(returned_at__isnull=True, due_at__lt=now, overdue_flagged_at__isnull=True)
            .select_related("asset")
        )
        count = 0
        for loan in newly_late:
            loan.overdue_flagged_at = now
            loan.save(update_fields=["overdue_flagged_at"])
            _log(LoanEvent.Kind.OVERDUE_FLAG, loan.asset, loan=loan, now=now)
            count += 1
        return count

    @staticmethod
    @transaction.atomic
    def clear_repair(admin, asset, now=None):
        """Admin moves a Repair item back to Available; loan history is untouched (US-07)."""
        asset = Asset.objects.select_for_update().get(pk=asset.pk)
        if asset.status != Asset.Status.REPAIR:
            raise CheckoutBlocked(f"{asset.asset_tag} is not in Repair.")
        asset.status = Asset.Status.AVAILABLE
        asset.save(update_fields=["status"])
        _log(LoanEvent.Kind.REPAIR_CLEARED, asset, actor=admin, now=now)
        return asset


# --- Accounts ----------------------------------------------------------------

ROSTER_COLUMNS = ("panther_id", "username", "display_name", "email", "phone")


def _new_activation_code():
    # Short enough to hand out on paper, long enough not to guess: 10 characters, no look-alikes.
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(10))


def _issue_code(profile, now):
    code = _new_activation_code()
    profile.activation_code_hash = make_password(code)
    profile.activation_expires = now + settings.ACTIVATION_CODE_LIFETIME
    return code


class AccountService:
    @staticmethod
    def parse_roster(file):
        """Read and validate every row before anything is saved. Returns (rows, errors).

        Row numbers match the line in the CSV file, so the header is row 1 and the first student
        is row 2, the same numbers a spreadsheet shows.
        """
        raw = file.read()
        text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
        reader = csv.DictReader(io.StringIO(text))
        headers = [h.strip() for h in (reader.fieldnames or [])]
        missing_columns = [c for c in ROSTER_COLUMNS if c not in headers]
        if missing_columns:
            return [], [f"Row 1: missing column(s) {', '.join(missing_columns)}."]
        reader.fieldnames = headers

        rows, errors = [], []
        seen_ids, seen_usernames = {}, {}
        for row_number, raw_row in enumerate(reader, start=2):
            row = {c: (raw_row.get(c) or "").strip() for c in ROSTER_COLUMNS}
            if not any(row.values()):
                continue  # skip blank lines
            problems = [f"missing {c}" for c in ROSTER_COLUMNS if not row[c]]
            if row["email"]:
                try:
                    validate_email(row["email"])
                except ValidationError:
                    problems.append("malformed email")
            pid, uname = row["panther_id"], row["username"].lower()
            if pid and pid in seen_ids:
                problems.append(f"duplicate Panther ID (also row {seen_ids[pid]})")
            if uname and uname in seen_usernames:
                problems.append(f"duplicate username (also row {seen_usernames[uname]})")
            if pid and uname:
                clash = (
                    User.objects.filter(username__iexact=uname)
                    .exclude(profile__panther_id=pid)
                    .exists()
                )
                if clash:
                    problems.append("username already belongs to a different account")
            seen_ids.setdefault(pid, row_number)
            seen_usernames.setdefault(uname, row_number)
            if problems:
                errors.append(f"Row {row_number}: {'; '.join(problems)}.")
            else:
                row["username"] = uname
                rows.append(row)
        if not rows and not errors:
            errors.append("The file has no student rows.")
        return rows, errors

    @staticmethod
    def import_roster(admin, file, term, now=None):
        """Create, update, and deactivate Student accounts from a semester roster CSV (US-02).

        Returns (RosterImport, codes) where codes lists (username, display_name, code) for every
        account that still needs activating. Codes are shown once and stored only as hashes.
        """
        now = now or timezone.now()
        rows, errors = AccountService.parse_roster(file)
        if errors:
            raise RosterInvalid(errors)
        with transaction.atomic():
            return AccountService._apply_roster(admin, rows, term.strip(), now)

    @staticmethod
    def _apply_roster(admin, rows, term, now):
        student_group, _ = Group.objects.get_or_create(name=STUDENT)
        created = updated = 0
        codes = []
        for row in rows:
            profile = Profile.objects.select_related("user").filter(panther_id=row["panther_id"]).first()
            if profile is None:
                user = User(username=row["username"], email=row["email"])
                user.set_unusable_password()
                user.save()
                user.groups.add(student_group)
                profile = Profile(user=user, panther_id=row["panther_id"])
                created += 1
            else:
                user = profile.user
                user.is_active = True
                user.email = row["email"]
                user.save(update_fields=["is_active", "email"])
                user.groups.add(student_group)
                updated += 1
            profile.display_name = row["display_name"]
            profile.phone = row["phone"]
            profile.roster_term = term
            # New accounts, and returning ones that never activated, get a fresh one-time code.
            if not user.has_usable_password():
                codes.append((user.username, profile.display_name, _issue_code(profile, now)))
            profile.save()

        roster_ids = [row["panther_id"] for row in rows]
        # Students who left the roster lose sign-in but keep their loan history.
        # Student workers in the Staff or Admin group are never deactivated by an import.
        leaving = (
            User.objects.filter(groups__name=STUDENT, is_active=True, is_superuser=False)
            .exclude(profile__panther_id__in=roster_ids)
            .exclude(groups__name__in=[STAFF, ADMIN])
        )
        deactivated = User.objects.filter(pk__in=list(leaving.values_list("pk", flat=True))).update(
            is_active=False
        )

        record = RosterImport.objects.create(
            term=term, uploaded_by=admin, uploaded_at=now,
            created=created, updated=updated, deactivated=deactivated,
        )
        return record, codes

    @staticmethod
    @transaction.atomic
    def activate(username, code, password, now=None):
        """First sign-in for a rostered student: check the one-time code, then set a password (US-08).

        Every failure raises the same ActivationFailed so the page never confirms a username.
        """
        now = now or timezone.now()
        # Look up through Profile (an inner join) so PostgreSQL can lock the row: it refuses
        # FOR UPDATE on the nullable side of the outer join that User -> profile would need.
        profile = (
            Profile.objects.select_for_update()
            .select_related("user")
            .filter(user__username__iexact=(username or "").strip(), user__is_active=True)
            .first()
        )
        user = profile.user if profile else None
        if (
            profile is None
            or not profile.activation_code_hash
            or profile.activation_expires is None
            or profile.activation_expires < now
            or not check_password((code or "").strip().upper(), profile.activation_code_hash)
        ):
            raise ActivationFailed
        validate_password(password, user)  # raises ValidationError with the usual Django messages
        user.set_password(password)
        user.save(update_fields=["password"])
        profile.activation_code_hash = ""
        profile.activation_expires = None
        profile.save(update_fields=["activation_code_hash", "activation_expires"])
        return user

    @staticmethod
    @transaction.atomic
    def create_staff(admin, username, password):
        """Admin creates a desk-worker account in the Staff group (US-09)."""
        username = (username or "").strip().lower()
        if not username:
            raise RoleChangeRefused("Enter a username.")
        if User.objects.filter(username__iexact=username).exists():
            raise RoleChangeRefused(
                "That username already exists. Use “Add Staff role” to give it Staff access."
            )
        user = User(username=username)
        validate_password(password, user)
        user.set_password(password)
        user.save()
        user.groups.add(Group.objects.get_or_create(name=STAFF)[0])
        return user

    @staticmethod
    def set_staff_role(admin, username, on):
        """Add or remove the Staff group. A student worker may hold both Student and Staff (US-09)."""
        user = User.objects.filter(username__iexact=(username or "").strip()).first()
        if user is None:
            raise RoleChangeRefused("No account has that username.")
        staff_group, _ = Group.objects.get_or_create(name=STAFF)
        if on:
            user.groups.add(staff_group)
        else:
            user.groups.remove(staff_group)
        return user

