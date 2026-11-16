"""US-04: Equipment return and optional damage note (Staff)."""

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from inventory.models import Asset, Loan, LoanEvent
from inventory.services import CheckoutBlocked, DamageNoteRequired, LoanService
from inventory.tests.conftest import NOON

pytestmark = pytest.mark.django_db


@pytest.fixture
def loan(staff, student, assets):
    return LoanService.checkout(staff, student.username, "CHG-001", now=NOON)


def post_return(client, tag, damaged=False, note=""):
    data = {"asset_tag": tag, "condition_note": note}
    if damaged:
        data["damaged"] = "on"
    return client.post(reverse("inventory:return"), data)


def test_signed_out_redirected_and_student_403(client, student):
    """AC1: a signed-out visitor is sent to sign-in and a Student receives HTTP 403."""
    response = client.get(reverse("inventory:return"))
    assert response.status_code == 302 and response.url.startswith(reverse("login"))
    client.force_login(student)
    assert client.get(reverse("inventory:return")).status_code == 403
    assert post_return(client, "CHG-001").status_code == 403


def test_plain_return_sets_available_without_note(client, staff, loan):
    """AC2: a return without a damage note sets status to Available and needs no condition note."""
    client.force_login(staff)
    response = post_return(client, "CHG-001")
    assert response.status_code == 302
    loan.refresh_from_db()
    loan.asset.refresh_from_db()
    assert loan.returned_at is not None and loan.returned_to == staff
    assert not loan.damaged and loan.condition_note == ""
    assert loan.asset.status == Asset.Status.AVAILABLE


def test_damaged_return_requires_note(client, staff, loan):
    """AC3a: a return marked damaged requires a non-empty condition note; nothing is saved."""
    with pytest.raises(DamageNoteRequired):
        LoanService.return_item(staff, "CHG-001", damaged=True, note="   ")
    client.force_login(staff)
    html = post_return(client, "CHG-001", damaged=True).content.decode()
    assert "A damage note is required." in html
    loan.refresh_from_db()
    assert loan.is_active


def test_damaged_return_moves_to_repair(staff, loan):
    """AC3b: a damaged return with a note sets asset status to Repair."""
    LoanService.return_item(staff, "CHG-001", damaged=True, note="USB-C port loose")
    loan.refresh_from_db()
    loan.asset.refresh_from_db()
    assert loan.damaged and loan.condition_note == "USB-C port loose"
    assert loan.asset.status == Asset.Status.REPAIR


def test_database_refuses_damaged_loan_without_note(loan):
    with pytest.raises(IntegrityError), transaction.atomic():
        Loan.objects.filter(pk=loan.pk).update(damaged=True, condition_note="")


def test_repair_item_cannot_be_checked_out(staff, student, loan):
    """AC4: an item in Repair cannot be checked out."""
    LoanService.return_item(staff, "CHG-001", damaged=True, note="Frayed")
    with pytest.raises(CheckoutBlocked):
        LoanService.checkout(staff, student.username, "CHG-001")


def test_return_appends_log_rows(staff, loan):
    """AC5: the transaction appends a row to the in-app notification log."""
    LoanService.return_item(staff, "CHG-001")
    assert LoanEvent.objects.filter(kind=LoanEvent.Kind.RETURN, loan=loan, actor=staff).count() == 1


def test_damaged_return_logs_return_and_repair(staff, loan):
    LoanService.return_item(staff, "CHG-001", damaged=True, note="Cracked")
    kinds = set(LoanEvent.objects.filter(loan=loan).values_list("kind", flat=True))
    assert kinds == {LoanEvent.Kind.CHECKOUT, LoanEvent.Kind.RETURN, LoanEvent.Kind.DAMAGE_TO_REPAIR}


def test_return_of_item_not_checked_out(client, staff, assets):
    with pytest.raises(CheckoutBlocked, match="not checked out"):
        LoanService.return_item(staff, "CHG-001")
    client.force_login(staff)
    assert "That item is not checked out." in post_return(client, "NOPE-1").content.decode()
