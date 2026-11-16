"""Shared test data. A test asks for one by naming it as an argument."""

from datetime import datetime, timezone as dt_timezone

import pytest
from django.contrib.auth.models import Group, User

from inventory.models import Asset, Profile

# A fixed clock so due-time and overdue tests never depend on when they run.
NOON = datetime(2026, 11, 2, 17, 0, tzinfo=dt_timezone.utc)  # 12:00 in Miami


def make_student(username, panther_id, display_name, phone="305-555-0000", **extra):
    user = User.objects.create_user(
        username, password="pw", email=f"{username}@mock.fiu.edu", **extra
    )
    user.groups.add(Group.objects.get_or_create(name="Student")[0])
    Profile.objects.create(user=user, display_name=display_name, panther_id=panther_id, phone=phone)
    return user


@pytest.fixture
def student(db):
    return make_student(
        "zquin001", "6000001", "Zelda Quintero", phone="305-555-0101",
        first_name="Zelda", last_name="Quintero",
    )


@pytest.fixture
def other_student(db):
    return make_student("mrive002", "6000002", "Marco Rivera", phone="305-555-0102")


@pytest.fixture
def staff(db):
    user = User.objects.create_user("deskstaff", password="pw")
    user.groups.add(Group.objects.get_or_create(name="Staff")[0])
    return user


@pytest.fixture
def admin_user(db):
    # is_staff lets the Admin group into the Django admin site (US-07).
    user = User.objects.create_user("coordinator", password="pw", is_staff=True)
    user.groups.add(Group.objects.get_or_create(name="Admin")[0])
    return user


@pytest.fixture
def assets(db):
    # One item per status, plus a retired one.
    return {
        "available": Asset.objects.create(asset_tag="CHG-001", asset_type="Charger", location="CS Lab Desk"),
        "out": Asset.objects.create(asset_tag="CALC-001", asset_type="Calculator", location="EIC Counter", status=Asset.Status.CHECKED_OUT),
        "repair": Asset.objects.create(asset_tag="HDMI-001", asset_type="HDMI Cable", location="CS Lab Desk", status=Asset.Status.REPAIR),
        "retired": Asset.objects.create(asset_tag="CAM-001", asset_type="Webcam", location="EIC Counter", is_retired=True),
    }


@pytest.fixture
def adapter(db):
    """A second Available item, for multi-loan tests."""
    return Asset.objects.create(asset_tag="ADPT-001", asset_type="USB-C Adapter", location="CS Lab Desk")
