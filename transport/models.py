from django.db import models

from companies.models import Company


class TransportUnitType(models.Model):
    """
    Reference table for transport unit types.
    Example: fire truck, ambulance, boat, drone, bus, pickup, etc.
    """

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Transport unit type"
        verbose_name_plural = "Transport unit types"
        db_table = "transport_unit_types"

    def __str__(self):
        return self.name


class TransportUnit(models.Model):
    """
    Generic transport resource unit.
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="transport_units",
    )
    name = models.CharField(max_length=100)
    type = models.ForeignKey(
        TransportUnitType, on_delete=models.PROTECT, related_name="transport_units"
    )
    identifier = models.CharField(
        max_length=50, blank=True
    )  # e.g. license plate or fleet number
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Transport unit"
        verbose_name_plural = "Transport units"
        db_table = "transport_units"

    def __str__(self):
        return self.name