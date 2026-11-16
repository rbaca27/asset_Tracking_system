"""Database tables for the inventory app (class diagram, Graphic 7 of the design paper).

Asset         one row per physical item (US-01 reads it, US-03/US-04 change `status`, US-07 edits it)
Profile       mock roster fields for a Student account (US-02, US-05, US-08)
RosterImport  one row per semester roster upload (US-02)
Loan          one asset lent to one borrower (US-03, US-04, US-05, US-06)
LoanEvent     the in-app event log (US-03, US-04, US-06, US-07)

Single-record rules live here as model methods. Anything that changes more than one table goes
through inventory/services.py so it runs inside one transaction.

After any change here run `python manage.py makemigrations`, commit the new file in
inventory/migrations/, and tell teammates to run `migrate`.
"""

import math
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Asset(models.Model):
    """One piece of loanable equipment."""

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        CHECKED_OUT = "CHECKED_OUT", "Checked Out"
        REPAIR = "REPAIR", "Repair"

    asset_tag = models.CharField(max_length=32, unique=True)  # typed at the desk, e.g. CHG-001
    asset_type = models.CharField(max_length=64)
    location = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.AVAILABLE
    )
    # Loan-policy duration, set by an Admin (US-07). Checkout adds it to the checkout time.
    loan_duration = models.DurationField(
        default=timedelta(hours=4),
        help_text="How long one loan lasts, e.g. 4:00:00 for 4 hours or 3 00:00:00 for 3 days.",
    )
    is_retired = models.BooleanField(default=False)  # hides the item without deleting its history

    class Meta:
        ordering = ["asset_type", "asset_tag"]
        constraints = [
            models.CheckConstraint(
                # Same rule as Status.choices, enforced inside PostgreSQL too.
                condition=models.Q(status__in=["AVAILABLE", "CHECKED_OUT", "REPAIR"]),
                name="asset_status_valid",
            ),
            models.CheckConstraint(
                # State machine note: an item cannot be retired while it is Checked Out.
                condition=~models.Q(is_retired=True, status="CHECKED_OUT"),
                name="asset_not_retired_while_checked_out",
            ),
        ]

    def __str__(self):
        return f"{self.asset_tag} ({self.asset_type})"

    def clean(self):
        if self.is_retired and self.status == self.Status.CHECKED_OUT:
            raise ValidationError(
                {"is_retired": "This item is checked out. Process its return before retiring it."}
            )
        if self.loan_duration is not None and self.loan_duration <= timedelta(0):
            raise ValidationError({"loan_duration": "The loan duration must be longer than zero."})

    @property
    def is_available(self):
        return self.status == self.Status.AVAILABLE

    def can_check_out(self):
        """Only an Available item that is still in circulation can be lent (US-03, US-04)."""
        return self.is_available and not self.is_retired

    def due_time(self, checked_out_at):
        """Due time = checkout time + this item's loan-policy duration (US-03, US-07)."""
        return checked_out_at + self.loan_duration


class Profile(models.Model):
    """Mock roster fields for one account. Not registrar records, not live campus credentials."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    display_name = models.CharField(max_length=128)
    panther_id = models.CharField("mock Panther ID", max_length=16, unique=True)
    phone = models.CharField("mock phone", max_length=32)
    roster_term = models.CharField(max_length=32, blank=True)
    # Hash of the one-time activation code from the roster import; cleared once used (US-08).
    activation_code_hash = models.CharField(max_length=128, blank=True)
    activation_expires = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self):
        return f"{self.display_name} ({self.panther_id})"


class RosterImport(models.Model):
    """One semester roster upload and what it changed (US-02)."""

    term = models.CharField(max_length=32)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="roster_imports"
    )
    uploaded_at = models.DateTimeField(default=timezone.now)
    created = models.PositiveIntegerField(default=0)
    updated = models.PositiveIntegerField(default=0)
    deactivated = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.term} roster ({self.uploaded_at:%Y-%m-%d})"


class Loan(models.Model):
    """One asset lent to one borrower. Active while returned_at is empty."""

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="loans")
    borrower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="loans"
    )
    checked_out_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    checked_out_at = models.DateTimeField(default=timezone.now)
    due_at = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)
    returned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", null=True, blank=True
    )
    damaged = models.BooleanField(default=False)
    condition_note = models.TextField(blank=True)
    # Set the first time the loan shows up on the overdue list, so it is logged only once (US-06).
    overdue_flagged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["due_at"]
        constraints = [
            # Backstop for the row lock in LoanService.checkout: one active loan per asset (D-04).
            models.UniqueConstraint(
                fields=["asset"],
                condition=models.Q(returned_at__isnull=True),
                name="one_active_loan_per_asset",
            ),
            # A damaged return must carry a condition note (US-04).
            models.CheckConstraint(
                condition=models.Q(damaged=False) | ~models.Q(condition_note=""),
                name="damaged_loan_has_note",
            ),
        ]

    def __str__(self):
        return f"{self.asset.asset_tag} to {self.borrower.username}"

    @property
    def is_active(self):
        return self.returned_at is None

    def is_overdue(self, now=None):
        now = now or timezone.now()
        return self.is_active and now > self.due_at

    def days_overdue(self, now=None):
        """Whole days late, counting a part day as a day; 0 when not overdue."""
        now = now or timezone.now()
        if not self.is_overdue(now):
            return 0
        return math.ceil((now - self.due_at) / timedelta(days=1))


class LoanEvent(models.Model):
    """The in-app event log. Staff-only; it never lists borrowers (Section 2.5)."""

    class Kind(models.TextChoices):
        CHECKOUT = "CHECKOUT", "Checkout"
        RETURN = "RETURN", "Return"
        DAMAGE_TO_REPAIR = "DAMAGE_TO_REPAIR", "Damaged, moved to Repair"
        OVERDUE_FLAG = "OVERDUE_FLAG", "Overdue"
        REPAIR_CLEARED = "REPAIR_CLEARED", "Repair cleared"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    created_at = models.DateTimeField(default=timezone.now)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="events")
    loan = models.ForeignKey(
        Loan, on_delete=models.PROTECT, related_name="events", null=True, blank=True
    )
    # Who did it; empty for events the system raises itself (overdue flags).
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", null=True, blank=True
    )
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_kind_display()} {self.asset.asset_tag} at {self.created_at:%Y-%m-%d %H:%M}"
