"""US-02: Semester roster import (Admin)."""

import io

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from inventory.models import Asset, Loan, Profile, RosterImport
from inventory.services import AccountService, LoanService, RosterInvalid
from inventory.tests.conftest import make_student

pytestmark = pytest.mark.django_db

HEADER = "panther_id,username,display_name,email,phone\n"
GOOD = HEADER + (
    "6000001,zquin001,Zelda Quintero,zquin001@mock.fiu.edu,305-555-0101\n"
    "6000002,mrive002,Marco Rivera,mrive002@mock.fiu.edu,305-555-0102\n"
)


def roster(text):
    return io.BytesIO(text.encode())


def upload(client, text, term="Spring 2027"):
    file = SimpleUploadedFile("roster.csv", text.encode(), content_type="text/csv")
    return client.post(reverse("inventory:roster_import"), {"term": term, "roster": file})


@pytest.mark.parametrize("who", ["student", "staff"])
def test_only_admin_opens_import_page(client, request, who):
    """AC1: only an Admin can open the roster import page; Staff and Students receive HTTP 403."""
    client.force_login(request.getfixturevalue(who))
    assert client.get(reverse("inventory:roster_import")).status_code == 403
    assert upload(client, GOOD).status_code == 403
    assert not RosterImport.objects.exists()
    assert not User.objects.filter(username="mrive002").exists()


def test_valid_row_creates_student_account(admin_user):
    """AC2: each valid row creates a Student account with display name, Panther ID, email, phone."""
    AccountService.import_roster(admin_user, roster(GOOD), "Spring 2027")
    user = User.objects.get(username="zquin001")
    assert user.groups.filter(name="Student").exists()
    assert user.email == "zquin001@mock.fiu.edu"
    assert (user.profile.display_name, user.profile.panther_id, user.profile.phone) == (
        "Zelda Quintero", "6000001", "305-555-0101",
    )
    assert user.profile.roster_term == "Spring 2027"


def test_new_account_has_no_usable_password(admin_user):
    """AC3: a new account has no usable password until the student activates it."""
    _, codes = AccountService.import_roster(admin_user, roster(GOOD), "Spring 2027")
    assert not User.objects.get(username="zquin001").has_usable_password()
    assert {username for username, _, _ in codes} == {"zquin001", "mrive002"}


def test_reimport_updates_instead_of_duplicating(admin_user):
    """AC4: re-importing a student updates that account, matched by mock Panther ID."""
    AccountService.import_roster(admin_user, roster(GOOD), "Fall 2026")
    changed = GOOD.replace("305-555-0101", "305-555-9999").replace("Zelda Quintero", "Zelda Q.")
    record, _ = AccountService.import_roster(admin_user, roster(changed), "Spring 2027")
    assert Profile.objects.filter(panther_id="6000001").count() == 1
    assert User.objects.filter(username="zquin001").count() == 1
    profile = Profile.objects.get(panther_id="6000001")
    assert (profile.phone, profile.display_name, profile.roster_term) == (
        "305-555-9999", "Zelda Q.", "Spring 2027",
    )
    assert (record.created, record.updated) == (0, 2)


def test_invalid_file_rejected_whole_with_row_numbers(admin_user):
    """AC5: a file with any invalid row is rejected as a whole; errors name each row number."""
    bad = HEADER + (
        "6000001,zquin001,Zelda Quintero,zquin001@mock.fiu.edu,305-555-0101\n"  # row 2 fine
        "6000002,mrive002,,mrive002@mock.fiu.edu,305-555-0102\n"                # row 3 missing name
        "6000001,jchen003,Jia Chen,jchen003@mock.fiu.edu,305-555-0103\n"        # row 4 duplicate ID
        "6000004,apate004,Asha Patel,not-an-email,305-555-0104\n"               # row 5 bad email
    )
    with pytest.raises(RosterInvalid) as rejected:
        AccountService.import_roster(admin_user, roster(bad), "Spring 2027")
    errors = rejected.value.errors
    assert [e.split(":")[0] for e in errors] == ["Row 3", "Row 4", "Row 5"]
    assert "missing display_name" in errors[0]
    assert "duplicate Panther ID" in errors[1]
    assert "malformed email" in errors[2]
    assert not Profile.objects.exists() and not RosterImport.objects.exists()


def test_invalid_file_page_lists_rows(client, admin_user):
    client.force_login(admin_user)
    html = upload(client, HEADER + "6000001,zquin001,Zelda,bad-email,305\n").content.decode()
    assert "Nothing was saved" in html and "Row 2" in html


def test_missing_students_deactivated_history_kept(admin_user, staff):
    """AC6: accounts missing from the new roster are deactivated and their loan history is kept."""
    AccountService.import_roster(admin_user, roster(GOOD), "Fall 2026")
    marco = User.objects.get(username="mrive002")
    Asset.objects.create(asset_tag="CHG-009", asset_type="Charger", location="Desk")
    LoanService.checkout(staff, "mrive002", "CHG-009")

    only_zelda = HEADER + "6000001,zquin001,Zelda Quintero,zquin001@mock.fiu.edu,305-555-0101\n"
    record, _ = AccountService.import_roster(admin_user, roster(only_zelda), "Spring 2027")
    marco.refresh_from_db()
    assert not marco.is_active
    assert Loan.objects.filter(borrower=marco).count() == 1
    assert record.deactivated == 1


def test_student_workers_never_deactivated(admin_user, staff):
    worker = make_student("kjohn006", "6000006", "Kayla Johnson")
    worker.groups.add(staff.groups.get(name="Staff"))
    AccountService.import_roster(admin_user, roster(GOOD), "Spring 2027")
    worker.refresh_from_db()
    assert worker.is_active


def test_import_shows_counts(client, admin_user):
    """AC7: the import shows how many accounts were created, updated, and deactivated."""
    make_student("old0001", "5999999", "Former Student")
    make_student("zquin001", "6000001", "Zelda Quintero")
    client.force_login(admin_user)
    html = upload(client, GOOD).content.decode()
    assert "1 created, 1 updated," in html and "1 deactivated" in html
    assert "One-time activation codes" in html
