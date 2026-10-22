"""Database tables for the inventory app.

Asset  one row per physical item (US-01 reads it, US-03/US-04 change `status`,
       US-07 edits it). After any change here run `python manage.py makemigrations`,
       commit the new file in inventory/migrations/, and tell teammates to run `migrate`.
"""

from datetime import timedelta

from django.db import models


class Asset(models.Model):
    """One piece of loanable equipment."""

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        CHECKED_OUT = "CHECKED_OUT", "Checked Out"
        REPAIR = "REPAIR", "Repair"

    asset_tag = models.CharField(max_length=32, unique=True)  # typed at the desk, e.g. CHG-001
    asset_type = models.CharField(max_length=64)
    location = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.AVAILABLE
    )
    loan_duration = models.DurationField(default=timedelta(hours=4))  # US-03 adds this to checkout time
    is_retired = models.BooleanField(default=False)  # hides the item without deleting its history

    class Meta:
        ordering = ["asset_type", "asset_tag"]
        constraints = [
            models.CheckConstraint(
                # Same rule as Status.choices, enforced inside PostgreSQL too.
                condition=models.Q(status__in=["AVAILABLE", "CHECKED_OUT", "REPAIR"]),
                name="asset_status_valid",
            )
        ]

    def __str__(self):
        return f"{self.asset_tag} ({self.asset_type})"

    @property
    def is_available(self):
        return self.status == self.Status.AVAILABLE
