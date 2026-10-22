import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from inventory.models import Asset

pytestmark = pytest.mark.django_db


def test_status_limited_to_three_choices():
    asset = Asset(asset_tag="T-1", asset_type="Charger", location="Desk", status="LOST")
    with pytest.raises(ValidationError):
        asset.full_clean()


def test_database_refuses_unknown_status():
    with pytest.raises(IntegrityError):
        Asset.objects.create(asset_tag="T-4", asset_type="Charger", location="Desk", status="LOST")


def test_is_available_only_for_available_status():
    asset = Asset.objects.create(asset_tag="T-2", asset_type="Charger", location="Desk")
    assert asset.is_available
    asset.status = Asset.Status.REPAIR
    assert not asset.is_available


def test_asset_tag_must_be_unique():
    Asset.objects.create(asset_tag="T-3", asset_type="Charger", location="Desk")
    with pytest.raises(IntegrityError):
        Asset.objects.create(asset_tag="T-3", asset_type="Webcam", location="Desk")
