"""US-08: Student account activation and sign-in."""

import io
import re
from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from inventory.services import AccountService, ActivationFailed

pytestmark = pytest.mark.django_db

ROSTER = (
    "panther_id,username,display_name,email,phone\n"
    "6000001,zquin001,Zelda Quintero,zquin001@mock.fiu.edu,305-555-0101\n"
)
NEW_PASSWORD = "lab-desk-Panther-77"
GENERIC = "Could not activate. Check your username and code"


@pytest.fixture
def code(admin_user):
    _, codes = AccountService.import_roster(admin_user, io.BytesIO(ROSTER.encode()), "Spring 2027")
    return codes[0][2]


def activate(client, username, code, password=NEW_PASSWORD):
    return client.post(reverse("inventory:activate"), {
        "username": username, "code": code, "password1": password, "password2": password,
    })


def sign_in(client, username, password):
    return client.post(reverse("login"), {"username": username, "password": password})


def test_activate_with_valid_code(client, code):
    """AC1: a student activates with a username and a valid one-time code, then picks a password."""
    response = activate(client, "zquin001", code)
    assert response.status_code == 302 and response.url == reverse("inventory:my_loans")
    assert User.objects.get(username="zquin001").check_password(NEW_PASSWORD)


@pytest.mark.parametrize("case", ["wrong", "used", "expired", "unknown user"])
def test_bad_code_rejected_generically(client, code, case):
    """AC2: a wrong, used, or expired code is rejected with a generic message."""
    username, typed = "zquin001", code
    if case == "wrong":
        typed = "AAAAAAAAAA"
    elif case == "used":
        activate(client, "zquin001", code)
        client.logout()
    elif case == "expired":
        user = User.objects.get(username="zquin001")
        user.profile.activation_expires -= timedelta(days=31)
        user.profile.save()
    else:
        username = "nobody"
    response = activate(client, username, typed, password="another-Pass-123")
    assert response.status_code == 200
    assert GENERIC in response.content.decode()
    with pytest.raises(ActivationFailed):
        AccountService.activate(username, typed, "another-Pass-123")


def test_password_stored_as_hash(client, code):
    """AC3: the stored password is a hash, not plaintext."""
    activate(client, "zquin001", code)
    stored = User.objects.get(username="zquin001").password
    assert NEW_PASSWORD not in stored and stored.count("$") >= 2
    assert code not in User.objects.get(username="zquin001").profile.activation_code_hash


def test_sign_in_is_local_username_and_password(client, code):
    """AC4: sign-in uses a local username and password rather than campus single sign-on."""
    activate(client, "zquin001", code)
    client.logout()
    response = sign_in(client, "zquin001", NEW_PASSWORD)
    assert response.status_code == 302
    assert client.get(reverse("inventory:my_loans")).status_code == 200


def test_wrong_password_generic_error(client, code):
    """AC5: a wrong password shows a generic error that does not reveal whether the username exists."""
    activate(client, "zquin001", code)
    client.logout()
    real_user = sign_in(client, "zquin001", "wrong-password").content.decode()
    no_user = sign_in(client, "nobody", "wrong-password").content.decode()
    errors = lambda html: re.findall(r'alert-danger">(.*?)</div>', html)
    assert errors(real_user) == errors(no_user)
    assert "Please enter a correct username and password" in errors(real_user)[0]


def test_deactivated_account_cannot_sign_in(client, code):
    """AC6: a deactivated account cannot sign in."""
    activate(client, "zquin001", code)
    client.logout()
    User.objects.filter(username="zquin001").update(is_active=False)
    response = sign_in(client, "zquin001", NEW_PASSWORD)
    assert response.status_code == 200
    assert "Please enter a correct username and password" in response.content.decode()


def test_signed_in_student_can_sign_out(client, code):
    """AC7: a signed-in student can sign out."""
    activate(client, "zquin001", code)
    assert client.post(reverse("logout")).status_code == 302
    assert client.get(reverse("inventory:my_loans")).status_code == 302  # back to sign-in


def test_weak_password_rejected_and_code_still_usable(client, code):
    response = activate(client, "zquin001", code, password="123")
    assert response.status_code == 200
    assert not User.objects.get(username="zquin001").has_usable_password()
    assert activate(client, "zquin001", code).status_code == 302
