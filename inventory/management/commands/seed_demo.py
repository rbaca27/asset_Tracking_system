"""US-07: load the demo desk so the whole app can be tried by hand.

    python manage.py seed_demo

Creates the Student, Staff and Admin groups, loads the 15 demo assets, creates `admin1` (Admin)
and `staff1` (Staff), imports the sample mock roster (inventory/fixtures/mock_roster.csv) the same
way US-02 does, activates the first rostered student, and checks out a few items so the overdue
list and event log have something to show. Safe to run more than once.
"""

from datetime import timedelta
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from inventory.models import Loan
from inventory.permissions import ADMIN, STAFF, STUDENT
from inventory.services import AccountService, LoanService

ROSTER = Path(__file__).resolve().parents[2] / "fixtures" / "mock_roster.csv"
PASSWORD = "demo-pass-123"

# (asset tag, borrower username, hours ago it was checked out); the last one is overdue.
DEMO_LOANS = [
    ("CHG-002", "zquin001", 1),
    ("CALC-001", "mrive002", 2),
    ("LAP-001", "jchen003", 80),
]


class Command(BaseCommand):
    help = "Load demo inventory, demo Staff and Admin logins, and the sample mock roster."

    @transaction.atomic
    def handle(self, *args, **options):
        for name in (STUDENT, STAFF, ADMIN):
            Group.objects.get_or_create(name=name)
        if not Loan.objects.exists():
            call_command("loaddata", "assets", verbosity=0)
        self.stdout.write("Demo inventory loaded (15 items).")

        admin = self._login("admin1", ADMIN, is_staff=True)  # is_staff opens the admin site
        staff = self._login("staff1", STAFF)

        with ROSTER.open("rb") as roster:
            record, codes = AccountService.import_roster(admin, roster, "Demo Term")
        self.stdout.write(
            f"Roster: {record.created} created, {record.updated} updated, "
            f"{record.deactivated} deactivated."
        )
        for username, _, code in codes:
            if username == "zquin001":
                AccountService.activate(username, code, PASSWORD)
                self.stdout.write(f"  {username}: activated (password {PASSWORD})")
            else:
                self.stdout.write(f"  {username}: activation code {code}")

        if not Loan.objects.exists():
            now = timezone.now()
            for tag, username, hours_ago in DEMO_LOANS:
                LoanService.checkout(staff, username, tag, now=now - timedelta(hours=hours_ago))
            self.stdout.write(f"{len(DEMO_LOANS)} demo loans created (LAP-001 is overdue).")

        self.stdout.write(self.style.SUCCESS(f"Logins: admin1, staff1, zquin001 / {PASSWORD}"))

    def _login(self, username, group, is_staff=False):
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password(PASSWORD)
        user.is_staff = is_staff
        user.save()
        user.groups.add(Group.objects.get(name=group))
        self.stdout.write(f"{username} ({group})")
        return user
