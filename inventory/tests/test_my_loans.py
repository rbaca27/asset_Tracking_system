"""US-05: a Student's own loans, and the privacy rules around them."""

import pytest
from django.urls import reverse

from inventory.services import LoanService

pytestmark = pytest.mark.django_db


@pytest.fixture
def loans(staff, student, other_student, assets, adapter):
    return {
        "mine": LoanService.checkout(staff, student.username, "CHG-001"),
        "theirs": LoanService.checkout(staff, other_student.username, "ADPT-001"),
    }


def my_loans_html(client, as_user, **params):
    client.force_login(as_user)
    return client.get(reverse("inventory:my_loans"), params).content.decode()


def test_student_sees_only_own_loans(client, student, loans):
    """AC1: an authenticated student sees only that student's loans."""
    html = my_loans_html(client, student)
    assert "CHG-001" in html
    assert "ADPT-001" not in html


def test_changing_ids_in_url_reveals_nothing(client, student, other_student, loans):
    """AC2: changing the identifier in the URL does not reveal another student's record."""
    client.force_login(student)
    theirs = loans["theirs"]
    response = client.get(reverse("inventory:loan_detail", args=[theirs.pk]))
    assert response.status_code == 404
    # The list page takes no account ID; tampering with the query string changes nothing.
    html = my_loans_html(client, student, user=other_student.pk, borrower="mrive002", id=other_student.pk)
    for secret in ("ADPT-001", "USB-C Adapter", "Marco", "6000002", "mrive002", "305-555-0102"):
        assert secret not in html


def test_own_loan_detail_opens(client, student, loans):
    client.force_login(student)
    response = client.get(reverse("inventory:loan_detail", args=[loans["mine"].pk]))
    assert response.status_code == 200 and "CHG-001" in response.content.decode()


def test_page_shows_tag_type_checkout_and_due(client, student, loans):
    """AC3: the page shows asset tag, type, checkout time, and due time."""
    html = my_loans_html(client, student)
    for heading in ("Asset tag", "Type", "Checked out", "Due"):
        assert f"<th>{heading}</th>" in html
    assert "CHG-001" in html and "Charger" in html


def test_student_sees_own_contact_fields(client, student, loans):
    """AC4: a Student may see that student's own display name and contact fields."""
    html = my_loans_html(client, student)
    for value in ("Zelda Quintero", "6000001", "zquin001@mock.fiu.edu", "305-555-0101"):
        assert value in html


def test_no_listing_of_others_by_device_type(client, student, loans):
    """AC5: a Student cannot list other students' loans filtered by device type."""
    html = my_loans_html(client, student, asset_type="USB-C Adapter", all="1")
    assert "ADPT-001" not in html
    client.force_login(student)
    assert client.get(reverse("inventory:overdue"), {"asset_type": "Charger"}).status_code == 403
    assert client.get(reverse("inventory:event_log")).status_code == 403


def test_returned_loans_leave_the_list(client, staff, student, loans):
    LoanService.return_item(staff, "CHG-001")
    assert "You have no items checked out." in my_loans_html(client, student)
