"""Who may open the Staff-only checkout page (US-01 AC5; US-02 will extend this)."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_student_gets_403_on_checkout(client, student):
    """AC5: a Student cannot open the checkout form."""
    client.force_login(student)
    assert client.get(reverse("inventory:checkout")).status_code == 403


def test_signed_out_visitor_sent_to_sign_in(client):
    response = client.get(reverse("inventory:checkout"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_staff_can_open_checkout(client, staff):
    client.force_login(staff)
    assert client.get(reverse("inventory:checkout")).status_code == 200
