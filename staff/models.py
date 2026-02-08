from django.db import models


class Position(models.Model):
    """
    Reference table for staff positions.
    """

    POSITION_TYPE_CHOICES = (
        ("expat", "Expat"),
        ("local", "Local"),
        ("any", "Any"),
    )

    position_id = models.BigAutoField(primary_key=True)

    name_long = models.CharField(
        max_length=255,
        unique=True,
        help_text="Full position name (e.g. Fire Chief, Senior Firefighter)",
    )

    name_short = models.CharField(
        max_length=64,
        unique=True,
        help_text="Short position name (e.g. Chief, FF)",
    )

    type = models.CharField(
        max_length=5,
        choices=POSITION_TYPE_CHOICES,
        default="any",
        help_text="Allowed staff type for this position",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this position is active and selectable",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_positions"
        ordering = ["name_long"]

    def __str__(self) -> str:
        return self.name_long


class ShiftType(models.Model):
    """
    Reference table for shift patterns/types.
    Example: 14/14, 28/28, 7/7 etc.
    """

    shift_type_id = models.BigAutoField(primary_key=True)

    shift_type_name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Long name for this shift type (e.g. Rotation 14/14, Night Shift)",
    )

    shift_type_short = models.CharField(
        max_length=10,
        unique=True,
        help_text="Short code up to 10 chars (letters/digits/signs), e.g. 14/14, NGT, D1",
    )

    shift_days_on = models.PositiveSmallIntegerField(
        help_text="Number of consecutive work days"
    )

    shift_days_off = models.PositiveSmallIntegerField(
        help_text="Number of consecutive off days after the shift"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this shift type is active and selectable",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_shift_types"
        ordering = ["shift_type_short"]
        constraints = [
            models.UniqueConstraint(
                fields=["shift_days_on", "shift_days_off", "shift_type_short"],
                name="uq_shift_type_pattern_short",
            )
        ]

    def __str__(self) -> str:
        return f"{self.shift_type_short} ({self.shift_days_on}/{self.shift_days_off})"


class Shift(models.Model):
    """
    Reference table for actual shifts (e.g., A/B/C) that use a shift type pattern.
    Example: Shift A uses type 14/14.
    """

    shift_id = models.BigAutoField(primary_key=True)

    shift_number = models.CharField(
        max_length=2,
        help_text="Manual code (2 chars): letters or digits, e.g. A1, 01, B2",
    )

    shift_type = models.ForeignKey(
        ShiftType,
        on_delete=models.PROTECT,
        related_name="shifts",
        help_text="Link to shift type (pattern)",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this shift is active and selectable",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_shifts"
        ordering = ["shift_number", "shift_type__shift_type_short"]
        constraints = [
            models.UniqueConstraint(
                fields=["shift_number", "shift_type"],
                name="uq_staff_shift_number_type_fk",
            ),
        ]

    def __str__(self) -> str:
        st = self.shift_type
        return f"{self.shift_number} — {st.shift_type_short} ({st.shift_days_on}/{st.shift_days_off})"
