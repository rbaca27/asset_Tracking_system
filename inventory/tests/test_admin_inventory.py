"""US-07: Administrative inventory management and seed data."""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.urls import reverse

from inventory.models import Asset, Loan, LoanEvent, Profile
from inventory.services import LoanService
from inventory.tests.conftest import NOON

pytestmark = pytest.mark.django_db

ADD_URL = reverse("admin:inventory_asset_add")


def change_url(asset):
    return reverse("admin:inventory_asset_change", args=[asset.pk])


def asset_form(**overrides):
    data = {"asset_tag": "WEB-010", "asset_type": "Webcam", "location": "CS Lab Desk",
            "loan_duration": "1 00:00:00"}
    data.update(overrides)
    return data


@pytest.mark.parametrize("who", ["student", "staff"])
def test_student_and_staff_cannot_create_edit_or_retire(client, request, assets, who):
    """AC1: Student and Staff accounts cannot create, edit, or retire assets."""
    user = request.getfixturevalue(who)
    user.is_staff = True  # even if someone opened the admin site door, the group check holds
    user.save()
    client.force_login(user)
    charger = assets["available"]
    assert client.post(ADD_URL, asset_form()).status_code == 403
    response = client.post(change_url(charger), asset_form(asset_tag="CHG-001", is_retired="on"))
    assert response.status_code == 403
    charger.refresh_from_db()
    assert not charger.is_retired and not Asset.objects.filter(asset_tag="WEB-010").exists()


def test_admin_adds_asset_with_all_fields(client, admin_user):
    """AC2: each asset stores tag, type, location, status, and a loan duration in hours or days."""
    client.force_login(admin_user)
    assert client.post(ADD_URL, asset_form()).status_code == 302
    webcam = Asset.objects.get(asset_tag="WEB-010")
    assert (webcam.asset_type, webcam.location, webcam.status) == ("Webcam", "CS Lab Desk", "AVAILABLE")
    assert webcam.loan_duration == timedelta(days=1)
    client.post(change_url(webcam), asset_form(loan_duration="06:00:00"))
    webcam.refresh_from_db()
    assert webcam.loan_duration == timedelta(hours=6)


def test_retire_hides_from_search_keeps_history(client, admin_user, staff, student, assets):
    """AC3: retiring an asset hides it from student search without deleting historical loans."""
    LoanService.checkout(staff, student.username, "CHG-001")
    LoanService.return_item(staff, "CHG-001")
    client.force_login(admin_user)
    client.post(reverse("admin:inventory_asset_changelist"),
                {"action": "retire", "_selected_action": [assets["available"].pk]})
    assets["available"].refresh_from_db()
    assert assets["available"].is_retired
    assert "CHG-001" not in client.get(reverse("inventory:catalog")).content.decode()
    assert Loan.objects.filter(asset=assets["available"]).count() == 1


def test_checked_out_item_cannot_be_retired(admin_user, staff, student, assets):
    LoanService.checkout(staff, student.username, "CHG-001")
    charger = Asset.objects.get(asset_tag="CHG-001")
    charger.is_retired = True
    with pytest.raises(ValidationError):
        charger.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        charger.save()


def test_admin_clears_repair_keeping_history(client, admin_user, staff, student, assets):
    """AC4: an Admin can change status from Repair back to Available without deleting loan history."""
    LoanService.checkout(staff, student.username, "CHG-001")
    LoanService.return_item(staff, "CHG-001", damaged=True, note="Loose port")
    charger = Asset.objects.get(asset_tag="CHG-001")
    client.force_login(admin_user)
    client.post(reverse("admin:inventory_asset_changelist"),
                {"action": "clear_repair", "_selected_action": [charger.pk]})
    charger.refresh_from_db()
    assert charger.status == Asset.Status.AVAILABLE
    loan = Loan.objects.get(asset=charger)
    assert loan.damaged and loan.condition_note == "Loose port"
    assert LoanEvent.objects.filter(kind=LoanEvent.Kind.REPAIR_CLEARED, actor=admin_user).exists()


def test_status_not_editable_in_admin_form(client, admin_user, assets):
    client.force_login(admin_user)
    repair = assets["repair"]
    client.post(change_url(repair), asset_form(asset_tag="HDMI-001", status="AVAILABLE"))
    repair.refresh_from_db()
    assert repair.status == Asset.Status.REPAIR


def test_seed_loads_inventory_and_mock_roster(client):
    """AC5: seed data loads demo inventory and a sample mock roster that US-02 imports."""
    call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))
    assert Asset.objects.count() == 15
    assert Profile.objects.count() == 6
    assert Loan.objects.filter(returned_at__isnull=True).count() == 3
    assert client.login(username="zquin001", password="demo-pass-123")
    call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))  # safe to re-run
    assert Profile.objects.count() == 6 and Loan.objects.count() == 3


def test_only_admin_sets_loan_duration(client, admin_user, staff, assets):
    """AC6: only Admin can set or edit an item's loan-policy duration."""
    charger = assets["available"]
    staff.is_staff = True
    staff.save()
    client.force_login(staff)
    client.post(change_url(charger), asset_form(asset_tag="CHG-001", loan_duration="9 00:00:00"))
    charger.refresh_from_db()
    assert charger.loan_duration == timedelta(hours=4)
    client.force_login(admin_user)
    client.post(change_url(charger), asset_form(asset_tag="CHG-001", loan_duration="2 00:00:00"))
    charger.refresh_from_db()
    assert charger.loan_duration == timedelta(days=2)


def test_checkout_uses_stored_duration(staff, student, assets):
    """AC7: checkout uses that stored duration to compute due time."""
    charger = assets["available"]
    charger.loan_duration = timedelta(days=2)
    charger.save()
    loan = LoanService.checkout(staff, student.username, "CHG-001", now=NOON)
    assert loan.due_at == NOON + timedelta(days=2)


def test_zero_duration_rejected(assets):
    charger = assets["available"]
    charger.loan_duration = timedelta(0)
    with pytest.raises(ValidationError):
        charger.full_clean()
