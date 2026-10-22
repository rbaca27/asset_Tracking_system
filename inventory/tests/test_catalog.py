import pytest
from django.core.management import call_command
from django.urls import reverse

from inventory.models import Asset

pytestmark = pytest.mark.django_db


def catalog_html(client, **filters):
    return client.get(reverse("inventory:catalog"), filters).content.decode()


def test_catalog_row_shows_four_fields(client, assets):
    html = catalog_html(client)
    for value in ("CHG-001", "Charger", "CS Lab Desk", ">Available</span>"):
        assert value in html


def test_unavailable_items_visible_and_badged(client, assets):
    html = catalog_html(client)
    assert "CALC-001" in html and "Unavailable: Checked Out" in html
    assert "HDMI-001" in html and "Unavailable: Repair" in html


def test_catalog_hides_borrower_fields(client, assets, student):
    html = catalog_html(client)
    for secret in ("zquintero", "Zelda", "Quintero", "zquin001@mock.fiu.edu"):
        assert secret not in html


def test_student_gets_403_on_checkout(client, student):
    client.force_login(student)
    assert client.get(reverse("inventory:checkout")).status_code == 403


def test_signed_out_visitor_sent_to_sign_in(client):
    response = client.get(reverse("inventory:checkout"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_staff_can_open_checkout(client, staff):
    client.force_login(staff)
    assert client.get(reverse("inventory:checkout")).status_code == 200


def test_catalog_reflects_status_change(client, assets):
    charger = assets["available"]
    charger.status = Asset.Status.CHECKED_OUT
    charger.save()
    assert "Unavailable: Checked Out" in catalog_html(client, q="CHG-001")


def test_retired_items_hidden(client, assets):
    assert "CAM-001" not in catalog_html(client)


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


def test_seed_fixture_loads(client):
    call_command("loaddata", "assets", verbosity=0)
    assert Asset.objects.count() == 15
    assert "CAM-001" not in catalog_html(client)
