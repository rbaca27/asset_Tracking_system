"""The demo data teammates load with `loaddata assets`."""

import pytest
from django.core.management import call_command
from django.urls import reverse

from inventory.models import Asset

pytestmark = pytest.mark.django_db


def test_seed_fixture_loads(client):
    call_command("loaddata", "assets", verbosity=0)
    assert Asset.objects.count() == 15
    html = client.get(reverse("inventory:catalog")).content.decode()
    assert "CAM-001" not in html  # the one retired item
