"""US-03: Walk-up equipment checkout (Staff)."""

from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from inventory.models import Asset, Loan, LoanEvent
from inventory.services import BorrowerNotFound, CheckoutBlocked, LoanService
from inventory.tests.conftest import NOON

pytestmark = pytest.mark.django_db


def post_checkout(client, borrower, tag):
    return client.post(reverse("inventory:checkout"), {"borrower": borrower, "asset_tag": tag})


def test_signed_out_redirected_and_student_403(client, student):
    """AC1: a signed-out visitor is sent to sign-in and a Student receives HTTP 403."""
    response = client.get(reverse("inventory:checkout"))
    assert response.status_code == 302 and response.url.startswith(reverse("login"))
    client.force_login(student)
    assert client.get(reverse("inventory:checkout")).status_code == 403
    assert post_checkout(client, student.username, "CHG-001").status_code == 403


@pytest.mark.parametrize("key", ["zquin001", "ZQUIN001", "6000001"])
def test_resolve_by_username_or_panther_id(student, key):
    """AC2: Staff can resolve an active Student account by local username or mock Panther ID."""
    assert LoanService.resolve_borrower(key) == student


def test_inactive_or_non_student_not_resolved(student, staff):
    student.is_active = False
    student.save()
    for key in ("zquin001", "6000001", staff.username, "", "nobody"):
        with pytest.raises(BorrowerNotFound):
            LoanService.resolve_borrower(key)


def test_unknown_borrower_shows_error(client, staff, assets):
    client.force_login(staff)
    response = post_checkout(client, "nobody", "CHG-001")
    assert response.status_code == 200
    assert "No active student account matches." in response.content.decode()
    assert not Loan.objects.exists()


@pytest.mark.parametrize("which", ["out", "repair"])
def test_checkout_blocked_for_checked_out_or_repair(staff, student, assets, which):
    """AC3: checkout is blocked if the asset status is Checked Out or Repair."""
    with pytest.raises(CheckoutBlocked):
        LoanService.checkout(staff, student.username, assets[which].asset_tag)
    assert not Loan.objects.exists()


@pytest.mark.parametrize("tag", ["CAM-001", "NOPE-999"])
def test_checkout_blocked_for_retired_or_unknown_tag(staff, student, assets, tag):
    with pytest.raises(CheckoutBlocked, match="Unknown asset tag"):
        LoanService.checkout(staff, student.username, tag)


def test_blocked_message_on_page(client, staff, student, assets):
    client.force_login(staff)
    html = post_checkout(client, student.username, "HDMI-001").content.decode()
    assert "in Repair and cannot be checked out" in html


def test_student_may_hold_several_items(staff, student, assets, adapter):
    """AC4: a student may have more than one active loan when the items are different assets."""
    LoanService.checkout(staff, student.username, "CHG-001")
    LoanService.checkout(staff, student.username, "ADPT-001")
    assert Loan.objects.filter(borrower=student, returned_at__isnull=True).count() == 2


def test_same_asset_cannot_be_lent_twice(staff, student, other_student, assets):
    LoanService.checkout(staff, student.username, "CHG-001")
    with pytest.raises(CheckoutBlocked):
        LoanService.checkout(staff, other_student.username, "CHG-001")


def test_database_backstop_one_active_loan_per_asset(staff, student, assets):
    """D-04: the partial unique constraint refuses a second active loan that skips the service."""
    asset = assets["available"]
    Loan.objects.create(asset=asset, borrower=student, checked_out_by=staff, due_at=NOON)
    with pytest.raises(IntegrityError), transaction.atomic():
        Loan.objects.create(asset=asset, borrower=student, checked_out_by=staff, due_at=NOON)


def test_due_time_from_loan_policy(staff, student, assets):
    """AC5: a checkout writes a loan whose due time comes from the item's loan-policy duration."""
    charger = assets["available"]
    charger.loan_duration = timedelta(hours=6)
    charger.save()
    loan = LoanService.checkout(staff, "6000001", "chg-001", now=NOON)
    assert (loan.borrower, loan.asset, loan.checked_out_by) == (student, charger, staff)
    assert loan.checked_out_at == NOON
    assert loan.due_at == NOON + timedelta(hours=6)


def test_status_becomes_checked_out(client, staff, student, assets):
    """AC6: the asset status becomes Checked Out."""
    client.force_login(staff)
    response = post_checkout(client, student.username, "CHG-001")
    assert response.status_code == 302
    assets["available"].refresh_from_db()
    assert assets["available"].status == Asset.Status.CHECKED_OUT
    assert "checked out to zquin001. Due" in client.get(response.url).content.decode()


def test_checkout_appends_log_row(staff, student, assets):
    """AC7: the transaction appends a row to the in-app notification log."""
    loan = LoanService.checkout(staff, student.username, "CHG-001")
    event = LoanEvent.objects.get()
    assert (event.kind, event.loan, event.asset, event.actor) == (
        LoanEvent.Kind.CHECKOUT, loan, loan.asset, staff,
    )
