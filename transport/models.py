from django.core.exceptions import ValidationError
from django.db import models

from companies.models import Company


class ParameterDataType(models.TextChoices):
    INTEGER = "integer", "Integer"
    DECIMAL = "decimal", "Decimal"
    TEXT = "text", "Text"
    BOOLEAN = "boolean", "Boolean"


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

    def clean(self):
        errors = {}

        if self.type_id and self.company_id and self.type.company_id != self.company_id:
            errors["type"] = "Selected transport unit type belongs to another company."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.type} | {self.name}"


class TransportTechnicalParameter(models.Model):
    """
    Company-defined dictionary of technical/passport parameters.

    Examples:
    - Fuel tank capacity
    - Water tank capacity
    - Foam tank capacity
    - Max gross weight
    - Axle count
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="transport_technical_parameters",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    data_type = models.CharField(
        max_length=20,
        choices=ParameterDataType.choices,
        default=ParameterDataType.TEXT,
    )
    unit = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Examples: L, kg, t, km, h, persons",
    )
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "name"]
        verbose_name = "Transport technical parameter"
        verbose_name_plural = "Transport technical parameters"
        db_table = "transport_technical_parameters"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="uniq_transport_technical_parameter_per_company_name",
            ),
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uniq_transport_technical_parameter_per_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class TransportOperationalParameter(models.Model):
    """
    Company-defined dictionary of operational/current parameters.

    Examples:
    - Odometer
    - Engine hours
    - Pump hours
    - Current fuel level
    - Current water volume
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="transport_operational_parameters",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    data_type = models.CharField(
        max_length=20,
        choices=ParameterDataType.choices,
        default=ParameterDataType.TEXT,
    )
    unit = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Examples: L, kg, km, h, bar, %",
    )
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "name"]
        verbose_name = "Transport operational parameter"
        verbose_name_plural = "Transport operational parameters"
        db_table = "transport_operational_parameters"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="uniq_transport_operational_parameter_per_company_name",
            ),
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uniq_transport_operational_parameter_per_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class TransportModelTechnicalParameter(models.Model):
    """
    Technical/passport parameter value configured for a transport model.
    Example:
    - Model: MAN TGM 18.320
    - Parameter: Fuel tank capacity
    - Value: 300 L
    """

    model = models.ForeignKey(
        TransportUnitModel,
        on_delete=models.CASCADE,
        related_name="technical_parameter_links",
    )
    parameter = models.ForeignKey(
        TransportTechnicalParameter,
        on_delete=models.PROTECT,
        related_name="model_links",
    )
    is_required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    value_integer = models.IntegerField(blank=True, null=True)
    value_decimal = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        blank=True,
        null=True,
    )
    value_text = models.CharField(max_length=255, blank=True, null=True)
    value_boolean = models.BooleanField(blank=True, null=True)

    class Meta:
        ordering = [
            "model__type__name",
            "model__name",
            "display_order",
            "parameter__name",
        ]
        verbose_name = "Transport model technical parameter"
        verbose_name_plural = "Transport model technical parameters"
        db_table = "transport_model_technical_parameters"
        constraints = [
            models.UniqueConstraint(
                fields=["model", "parameter"],
                name="uniq_transport_model_technical_parameter",
            )
        ]

    def clean(self):
        errors = {}

        if self.model_id and self.parameter_id:
            if self.model.company_id != self.parameter.company_id:
                errors["parameter"] = (
                    "Selected technical parameter belongs to another company."
                )

        values_filled = sum(
            value is not None
            for value in [
                self.value_integer,
                self.value_decimal,
                self.value_text,
                self.value_boolean,
            ]
        )

        if values_filled == 0:
            errors["parameter"] = "Technical parameter value is required."

        if values_filled > 1:
            errors["parameter"] = "Only one technical value field can be filled."

        if self.parameter_id:
            parameter_type = self.parameter.data_type

            if parameter_type == ParameterDataType.INTEGER:
                if self.value_integer is None:
                    errors["value_integer"] = "Integer value is required."
            elif parameter_type == ParameterDataType.DECIMAL:
                if self.value_decimal is None:
                    errors["value_decimal"] = "Decimal value is required."
            elif parameter_type == ParameterDataType.TEXT:
                if not self.value_text:
                    errors["value_text"] = "Text value is required."
            elif parameter_type == ParameterDataType.BOOLEAN:
                if self.value_boolean is None:
                    errors["value_boolean"] = "Boolean value is required."

        if errors:
            raise ValidationError(errors)

    def typed_value(self):
        if self.parameter.data_type == ParameterDataType.INTEGER:
            return self.value_integer
        if self.parameter.data_type == ParameterDataType.DECIMAL:
            return self.value_decimal
        if self.parameter.data_type == ParameterDataType.TEXT:
            return self.value_text
        if self.parameter.data_type == ParameterDataType.BOOLEAN:
            return self.value_boolean
        return None

    def __str__(self):
        return f"{self.model} | {self.parameter}"


class TransportModelOperationalParameter(models.Model):
    """
    Operational parameter configured for a transport model.

    Examples:
    - Odometer, min=0, no upper bound
    - Current fuel level, min=0, max technical parameter = Fuel tank capacity
    - Current water volume, min=0, max technical parameter = Water tank capacity
    """

    model = models.ForeignKey(
        TransportUnitModel,
        on_delete=models.CASCADE,
        related_name="operational_parameter_links",
    )
    parameter = models.ForeignKey(
        TransportOperationalParameter,
        on_delete=models.PROTECT,
        related_name="model_links",
    )
    is_required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    min_value = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        blank=True,
        null=True,
    )
    max_value = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        blank=True,
        null=True,
    )
    max_technical_parameter = models.ForeignKey(
        TransportTechnicalParameter,
        on_delete=models.PROTECT,
        related_name="operational_max_links",
        blank=True,
        null=True,
        help_text="Optional technical parameter defining upper bound.",
    )

    class Meta:
        ordering = [
            "model__type__name",
            "model__name",
            "display_order",
            "parameter__name",
        ]
        verbose_name = "Transport model operational parameter"
        verbose_name_plural = "Transport model operational parameters"
        db_table = "transport_model_operational_parameters"
        constraints = [
            models.UniqueConstraint(
                fields=["model", "parameter"],
                name="uniq_transport_model_operational_parameter",
            )
        ]

    def clean(self):
        errors = {}

        if self.model_id and self.parameter_id:
            if self.model.company_id != self.parameter.company_id:
                errors["parameter"] = (
                    "Selected operational parameter belongs to another company."
                )

        if self.max_value is not None and self.max_technical_parameter_id is not None:
            errors["max_value"] = (
                "Use either fixed max_value or max_technical_parameter, not both."
            )
            errors["max_technical_parameter"] = (
                "Use either fixed max_value or max_technical_parameter, not both."
            )

        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            errors["max_value"] = (
                "max_value must be greater than or equal to min_value."
            )

        if self.max_technical_parameter_id:
            if (
                self.model_id
                and self.max_technical_parameter.company_id != self.model.company_id
            ):
                errors["max_technical_parameter"] = (
                    "Selected technical parameter belongs to another company."
                )
            elif self.model_id:
                exists_for_model = TransportModelTechnicalParameter.objects.filter(
                    model=self.model,
                    parameter=self.max_technical_parameter,
                ).exists()
                if not exists_for_model:
                    errors["max_technical_parameter"] = (
                        "Selected technical parameter is not configured for this transport model."
                    )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.model} | {self.parameter}"


class TransportUnit(models.Model):
    """
    Given transport resource unit.
    """

    class TechnicalStatus(models.TextChoices):
        READY = "ready", "Ready"
        RESERVE = "reserve", "Reserve"
        OUT_OF_SERVICE = "out_of_service", "Out of service"
        MAINTENANCE = "maintenance", "Maintenance"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="transport_units",
    )
    name = models.CharField(max_length=10)
    model = models.ForeignKey(
        TransportUnitModel,
        on_delete=models.PROTECT,
        related_name="transport_units",
    )

    identifier = models.CharField(
        max_length=50,
        blank=True,
    )
    technical_status = models.CharField(
        max_length=20,
        choices=TechnicalStatus.choices,
        default=TechnicalStatus.READY,
    )
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Transport unit"
        verbose_name_plural = "Transport units"
        db_table = "transport_units"

    def clean(self):
        errors = {}

        if self.model_id:
            unit_model = TransportUnitModel.objects.get(pk=self.model_id)

            if self.company_id and unit_model.company_id != self.company_id:
                errors["model"] = (
                    "Selected transport unit model belongs to another company."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name


class TransportUnitOperationalValue(models.Model):
    """
    Stores current value of an operational parameter for a specific transport unit.

    Example:
    - Unit: Engine 1
    - Parameter: Odometer
    - Value: 45231
    """

    unit = models.ForeignKey(
        TransportUnit,
        on_delete=models.CASCADE,
        related_name="operational_values",
    )
    parameter = models.ForeignKey(
        TransportOperationalParameter,
        on_delete=models.PROTECT,
        related_name="unit_values",
    )

    value_integer = models.IntegerField(blank=True, null=True)
    value_decimal = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        blank=True,
        null=True,
    )
    value_text = models.CharField(max_length=255, blank=True, null=True)
    value_boolean = models.BooleanField(blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Transport unit operational value"
        verbose_name_plural = "Transport unit operational values"
        db_table = "transport_unit_operational_values"
        constraints = [
            models.UniqueConstraint(
                fields=["unit", "parameter"],
                name="uniq_transport_unit_operational_value",
            )
        ]

    def clean(self):
        errors = {}

        # 1. Company consistency
        if self.unit_id and self.parameter_id:
            if self.unit.company_id != self.parameter.company_id:
                errors["parameter"] = (
                    "Selected operational parameter belongs to another company."
                )

        # 2. Parameter must be configured for model
        if self.unit_id and self.parameter_id:
            exists = TransportModelOperationalParameter.objects.filter(
                model=self.unit.model,
                parameter=self.parameter,
            ).exists()

            if not exists:
                errors["parameter"] = (
                    "This parameter is not configured for the unit model."
                )

        # 3. Only one value field
        values_filled = sum(
            value is not None
            for value in [
                self.value_integer,
                self.value_decimal,
                self.value_text,
                self.value_boolean,
            ]
        )

        if values_filled == 0:
            errors["parameter"] = "Operational value is required."

        if values_filled > 1:
            errors["parameter"] = "Only one value field can be filled."

        # 4. Data type validation
        if self.parameter_id:
            dtype = self.parameter.data_type

            if dtype == ParameterDataType.INTEGER and self.value_integer is None:
                errors["value_integer"] = "Integer value required."
            elif dtype == ParameterDataType.DECIMAL and self.value_decimal is None:
                errors["value_decimal"] = "Decimal value required."
            elif dtype == ParameterDataType.TEXT and not self.value_text:
                errors["value_text"] = "Text value required."
            elif dtype == ParameterDataType.BOOLEAN and self.value_boolean is None:
                errors["value_boolean"] = "Boolean value required."

        # 5. Range validation
        if self.unit_id and self.parameter_id:
            try:
                model_param = TransportModelOperationalParameter.objects.get(
                    model=self.unit.model,
                    parameter=self.parameter,
                )

                value = self.get_numeric_value()

                if value is not None:
                    if (
                        model_param.min_value is not None
                        and value < model_param.min_value
                    ):
                        errors["parameter"] = "Value is below minimum allowed."

                    if (
                        model_param.max_value is not None
                        and value > model_param.max_value
                    ):
                        errors["parameter"] = "Value exceeds fixed maximum."

                    if model_param.max_technical_parameter:
                        tech = TransportModelTechnicalParameter.objects.get(
                            model=self.unit.model,
                            parameter=model_param.max_technical_parameter,
                        )
                        max_val = tech.typed_value()

                        if max_val is not None and value > max_val:
                            errors["parameter"] = (
                                "Value exceeds technical parameter limit."
                            )

            except TransportModelOperationalParameter.DoesNotExist:
                pass

        if errors:
            raise ValidationError(errors)

    def get_numeric_value(self):
        if self.value_integer is not None:
            return self.value_integer
        if self.value_decimal is not None:
            return self.value_decimal
        return None

    def __str__(self):
        return f"{self.unit} | {self.parameter}"