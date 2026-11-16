"""US-09: Staff accounts and role assignment (Admin)."""

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from inventory.permissions import is_staff_member

pytestmark = pytest.mark.django_db

PAGE = reverse("inventory:staff_roles")
STAFF_PAGES = ["inventory:checkout", "inventory:return", "inventory:overdue"]


def create_staff(client, username, password="desk-Shift-2027"):
    return client.post(PAGE, {"create": "1", "create-username": username, "create-password": password})


def add_role(client, username):
    return client.post(PAGE, {"add": "1", "role-username": username})


def remove_role(client, username):
    return client.post(reverse("inventory:remove_staff_role"), {"username": username})


@pytest.mark.parametrize("who", ["student", "staff"])
def test_only_admin_creates_staff_or_changes_groups(client, request, student, who):
    """AC1: only an Admin can create a Staff account or change a user's groups."""
    client.force_login(request.getfixturevalue(who))
    assert create_staff(client, "newdesk").status_code == 403
    assert add_role(client, student.username).status_code == 403
    assert remove_role(client, "deskstaff").status_code == 403
    assert not User.objects.filter(username="newdesk").exists()
    assert not is_staff_member(student)


def test_admin_creates_staff_account(client, admin_user):
    client.force_login(admin_user)
    assert create_staff(client, "newdesk").status_code == 302
    user = User.objects.get(username="newdesk")
    assert user.groups.filter(name="Staff").exists() and not user.is_staff
    assert user.check_password("desk-Shift-2027")


def test_added_staff_opens_desk_pages(client, admin_user):
    """AC2: a user added to the Staff group can open the checkout, return, and overdue pages."""
    client.force_login(admin_user)
    create_staff(client, "newdesk")
    client.force_login(User.objects.get(username="newdesk"))
    for page in STAFF_PAGES:
        assert client.get(reverse(page)).status_code == 200


def test_removed_staff_gets_403(client, admin_user, staff):
    """AC3: a user removed from the Staff group receives HTTP 403 on those pages."""
    client.force_login(admin_user)
    assert remove_role(client, staff.username).status_code == 302
    client.force_login(staff)
    for page in STAFF_PAGES:
        assert client.get(reverse(page)).status_code == 403


def test_student_worker_holds_both_groups(client, admin_user, student):
    """AC4: a student worker can belong to both the Student and Staff groups."""
    client.force_login(admin_user)
    add_role(client, student.username)
    names = set(student.groups.values_list("name", flat=True))
    assert names == {"Student", "Staff"}
    client.force_login(student)
    assert client.get(reverse("inventory:checkout")).status_code == 200
    assert client.get(reverse("inventory:my_loans")).status_code == 200


def test_duplicate_username_refused(client, admin_user, student):
    client.force_login(admin_user)
    html = create_staff(client, student.username).content.decode()
    assert "already exists" in html
