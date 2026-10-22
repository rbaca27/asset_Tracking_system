"""US-01 acceptance criteria for the public catalog page (docs/US-01.md maps each to a test)."""

import pytest
from django.urls import reverse

from inventory.models import Asset

pytestmark = pytest.mark.django_db


def catalog_html(client, **filters):
    """Fetch /catalog/ with the given filters and return the page as text."""
    return client.get(reverse("inventory:catalog"), filters).content.decode()


# --- What each row shows -----------------------------------------------------


def test_catalog_row_shows_four_fields(client, assets):
    """AC1: each row shows asset tag, type, location and status."""
    html = catalog_html(client)
    for value in ("CHG-001", "Charger", "CS Lab Desk", ">Available</span>"):
        assert value in html


def test_unavailable_items_visible_and_badged(client, assets):
    """AC3: Checked Out and Repair items stay visible but are badged unavailable."""
    html = catalog_html(client)
    assert "CALC-001" in html and "Unavailable: Checked Out" in html
    assert "HDMI-001" in html and "Unavailable: Repair" in html


def test_catalog_hides_borrower_fields(client, assets, student):
    """AC4: no borrower name, Panther ID, email or phone appears."""
    html = catalog_html(client)
    for secret in ("zquintero", "Zelda", "Quintero", "zquin001@mock.fiu.edu"):
        assert secret not in html


def test_catalog_reflects_status_change(client, assets):
    """AC6: after a checkout or return is saved, the catalog shows the new status."""
    charger = assets["available"]
    charger.status = Asset.Status.CHECKED_OUT
    charger.save()
    assert "Unavailable: Checked Out" in catalog_html(client, q="CHG-001")


# --- Which items appear ------------------------------------------------------


def test_retired_items_hidden(client, assets):
    assert "CAM-001" not in catalog_html(client)


# --- Search and filters ------------------------------------------------------


def test_status_filter(client, assets):
    html = catalog_html(client, status="REPAIR")
    assert "HDMI-001" in html and "CHG-001" not in html


def test_type_search_ignores_case(client, assets):
    html = catalog_html(client, asset_type="charger")
    assert "CHG-001" in html and "CALC-001" not in html


def test_location_filter(client, assets):
    html = catalog_html(client, location="eic")
    assert "CALC-001" in html and "CHG-001" not in html


def test_unknown_status_shows_everything(client, assets):
    html = catalog_html(client, status="LOST")
    assert "CHG-001" in html and "HDMI-001" in html


def test_no_match_message(client, assets):
    assert "No equipment matches those filters." in catalog_html(client, q="NOPE")
