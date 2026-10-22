from datetime import timedelta

from django.db import models


class Asset(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        CHECKED_OUT = "CHECKED_OUT", "Checked Out"
        REPAIR = "REPAIR", "Repair"

    asset_tag = models.CharField(max_length=32, unique=True)
    asset_type = models.CharField(max_length=64)
    location = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.AVAILABLE
    )
    loan_duration = models.DurationField(default=timedelta(hours=4))
    is_retired = models.BooleanField(default=False)

    class Meta:
        ordering = ["asset_type", "asset_tag"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["AVAILABLE", "CHECKED_OUT", "REPAIR"]),
                name="asset_status_valid",
            )
        ]

    def __str__(self):
        return f"{self.asset_tag} ({self.asset_type})"

    @property
    def is_available(self):
        return self.status == self.Status.AVAILABLE
