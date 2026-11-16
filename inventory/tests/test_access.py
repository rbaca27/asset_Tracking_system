"""Who may open which page. Each Staff and Admin page checks its own access rule (D-14)."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

STAFF_PAGES = ["inventory:checkout", "inventory:return", "inventory:overdue", "inventory:event_log"]
ADMIN_PAGES = ["inventory:roster_import", "inventory:staff_roles"]


def test_student_gets_403_on_checkout(client, student):
    """US-01 AC5: a Student cannot open the checkout form."""
    client.force_login(student)
    assert client.get(reverse("inventory:checkout")).status_code == 403


@pytest.mark.parametrize("page", STAFF_PAGES + ADMIN_PAGES + ["inventory:my_loans"])
def test_signed_out_visitor_sent_to_sign_in(client, page):
    response = client.get(reverse(page))
    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


@pytest.mark.parametrize("page", STAFF_PAGES + ADMIN_PAGES)
def test_student_gets_403_on_staff_and_admin_pages(client, student, page):
    client.force_login(student)
    assert client.get(reverse(page)).status_code == 403


@pytest.mark.parametrize("page", STAFF_PAGES)
def test_staff_can_open_staff_pages(client, staff, page):
    client.force_login(staff)
    assert client.get(reverse(page)).status_code == 200


@pytest.mark.parametrize("page", ADMIN_PAGES)
def test_staff_gets_403_on_admin_pages(client, staff, page):
    client.force_login(staff)
    assert client.get(reverse(page)).status_code == 403


@pytest.mark.parametrize("page", STAFF_PAGES + ADMIN_PAGES)
def test_admin_can_open_every_staff_and_admin_page(client, admin_user, page):
    client.force_login(admin_user)
    assert client.get(reverse(page)).status_code == 200
