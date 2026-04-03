from django.db import models

from companies.models import Company


class TransportUnitType(models.Model):
    """
    Functional class of transport unit within a company.
    Examples: Engine, Tanker, Pickup, Ambulance, Tricycle, Golf Cart.
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="transport_unit_types",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "name"]
        verbose_name = "Transport unit type"
        verbose_name_plural = "Transport unit types"
        db_table = "transport_unit_types"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="uniq_transport_unit_type_per_company_name",
            ),
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uniq_transport_unit_type_per_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class TransportUnitModel(models.Model):
    """
    Technical model/configuration within one transport unit type.
    Examples:
    - Engine -> MAN TGM 18.320
    - Tanker -> IVECO Water Tanker 12000L
    - Pickup -> Toyota Hilux
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="transport_unit_models",
    )
    type = models.ForeignKey(
        TransportUnitType,
        on_delete=models.PROTECT,
        related_name="models",
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "type__name", "name"]
        verbose_name = "Transport unit model"
        verbose_name_plural = "Transport unit models"
        db_table = "transport_unit_models"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "type", "name"],
                name="uniq_transport_unit_model_per_company_type_name",
            )
        ]

    def __str__(self):
        return f"{self.type} | {self.name}"


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
        TransportUnitType,
        on_delete=models.PROTECT,
        related_name="transport_units",
    )
    identifier = models.CharField(
        max_length=50,
        blank=True,
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