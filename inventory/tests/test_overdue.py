"""US-06: Staff overdue list and in-app event log."""

from datetime import timedelta

import pytest
from django.urls import reverse

from inventory.models import LoanEvent
from inventory.services import LoanService
from inventory.tests.conftest import NOON

pytestmark = pytest.mark.django_db


@pytest.fixture
def late_loan(staff, student, assets):
    """Checked out three and a half days ago with a 4-hour policy: 4 days overdue, counting part days."""
    return LoanService.checkout(staff, student.username, "CHG-001", now=NOON - timedelta(days=3, hours=12))


def test_student_gets_403_on_overdue_and_log(client, student):
    """AC1: a Student requesting the overdue list or event log receives HTTP 403."""
    client.force_login(student)
    assert client.get(reverse("inventory:overdue")).status_code == 403
    assert client.get(reverse("inventory:event_log")).status_code == 403


def test_overdue_list_columns(client, staff, late_loan):
    """AC2: the list shows tag, type, borrower, name, Panther ID, email, phone, due, days overdue."""
    client.force_login(staff)
    html = client.get(reverse("inventory:overdue")).content.decode()
    for value in ("CHG-001", "Charger", "zquin001", "Zelda Quintero", "6000001",
                  "zquin001@mock.fiu.edu", "305-555-0101", "Days overdue"):
        assert value in html


def test_days_overdue_and_not_yet_due(staff, student, late_loan, adapter):
    assert late_loan.days_overdue(NOON) == 4
    fresh = LoanService.checkout(staff, student.username, "ADPT-001", now=NOON)
    assert fresh.days_overdue(NOON) == 0
    assert list(LoanService.overdue_loans(NOON)) == [late_loan]


def test_each_transaction_appends_a_log_row(staff, admin_user, late_loan):
    """AC3: checkout, return, damage-to-Repair, and overdue flags append a row to the log."""
    assert LoanService.flag_overdue(NOON) == 1
    LoanService.return_item(staff, "CHG-001", damaged=True, note="Bent pin", now=NOON)
    kinds = list(LoanEvent.objects.order_by("id").values_list("kind", flat=True))
    assert kinds == ["CHECKOUT", "OVERDUE_FLAG", "RETURN", "DAMAGE_TO_REPAIR"]


def test_overdue_flag_logged_once(late_loan):
    LoanService.flag_overdue(NOON)
    LoanService.flag_overdue(NOON + timedelta(hours=1))  # a refresh of the list
    assert LoanEvent.objects.filter(kind=LoanEvent.Kind.OVERDUE_FLAG).count() == 1
    late_loan.refresh_from_db()
    assert late_loan.overdue_flagged_at == NOON


def test_opening_overdue_page_flags(client, staff, late_loan):
    client.force_login(staff)
    client.get(reverse("inventory:overdue"))
    assert LoanEvent.objects.filter(kind=LoanEvent.Kind.OVERDUE_FLAG, loan=late_loan).exists()


def test_log_is_staff_only_and_names_no_borrower(client, staff, student, late_loan):
    """AC4: the log is in-app only, and is not a report of who borrowed which device type."""
    client.force_login(staff)
    html = client.get(reverse("inventory:event_log")).content.decode()
    assert "Checkout" in html and "CHG-001" in html and "deskstaff" in html
    for secret in ("zquin001", "Zelda", "6000001", "305-555-0101"):
        assert secret not in html
