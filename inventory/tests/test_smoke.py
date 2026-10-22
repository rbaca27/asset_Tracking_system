import pytest
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_database_is_reachable():
    User.objects.create_user("smoke", password="x")
    assert User.objects.count() == 1
