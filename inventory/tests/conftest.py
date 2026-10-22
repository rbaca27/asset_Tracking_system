"""Shared test data. A test asks for one by naming it as an argument."""

import pytest
from django.contrib.auth.models import Group, User

from inventory.models import Asset


@pytest.fixture
def student(db):
    # US-02: add mock Panther ID and phone here once the profile exists.
    user = User.objects.create_user(
        "zquintero", password="pw", first_name="Zelda", last_name="Quintero",
        email="zquin001@mock.fiu.edu",
    )
    user.groups.add(Group.objects.get_or_create(name="Student")[0])
    return user


@pytest.fixture
def staff(db):
    user = User.objects.create_user("deskstaff", password="pw")
    user.groups.add(Group.objects.get_or_create(name="Staff")[0])
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
