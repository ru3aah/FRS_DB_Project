from django.db import models


class Position(models.Model):
    """
    Reference table for staff positions.
    """

    TYPE_CHOICES = (
        ("expat", "Expat"),
        ("local", "Local"),
        ("any", "Any"),
    )

    position_id = models.BigAutoField(primary_key=True)

    name_long = models.CharField(max_length=255)
    name_short = models.CharField(max_length=64)

    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default="any",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "staff_positions"
        ordering = ["name_long"]

    def __str__(self) -> str:
        return self.name_long


class ShiftType(models.Model):
    """
    Reference table for shift patterns.
    """

    shift_type_id = models.BigAutoField(primary_key=True)

    shift_type_name = models.CharField(max_length=255)
    shift_type_short = models.CharField(
        max_length=10,
        unique=True,
        help_text="Short code (letters/numbers, max 10 chars)",
    )

    shift_days_on = models.PositiveIntegerField()
    shift_days_off = models.PositiveIntegerField()

    class Meta:
        db_table = "staff_shift_types"
        ordering = ["shift_type_short"]

    def __str__(self) -> str:
        return self.shift_type_short


class Shift(models.Model):
    """
    Concrete shift instances (numbers/groups).
    """

    shift_id = models.BigAutoField(primary_key=True)

    shift_number = models.CharField(
        max_length=2,
        help_text="Two characters (letters or digits)",
    )

    shift_type = models.ForeignKey(
        ShiftType,
        on_delete=models.PROTECT,
        related_name="shifts",
    )

    class Meta:
        db_table = "staff_shifts"
        ordering = ["shift_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["shift_number", "shift_type"],
                name="uq_staff_shift_number_type_fk",
            )
        ]

    def __str__(self) -> str:
        return f"{self.shift_number} ({self.shift_type})"


# =========================
# Staffing Plan
# =========================


class StaffingPlan(models.Model):
    """
    Staffing plan header.
    """

    staffing_plan_id = models.BigAutoField(primary_key=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_staffing_plans"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Staffing plan #{self.staffing_plan_id}"


class StaffingPlanItem(models.Model):
    """
    Lines of staffing plan:
    - position
    - quantity
    - shift type
    """

    staffing_plan_item_id = models.BigAutoField(primary_key=True)

    staffing_plan = models.ForeignKey(
        StaffingPlan,
        on_delete=models.CASCADE,
        related_name="items",
    )

    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name="staffing_plan_items",
    )

    position_qty = models.PositiveIntegerField(
        help_text="Number of positions required",
    )

    shift_type = models.ForeignKey(
        ShiftType,
        on_delete=models.PROTECT,
        related_name="staffing_plan_items",
    )

    class Meta:
        db_table = "staff_staffing_plan_items"
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["staffing_plan", "position", "shift_type"],
                name="uq_staffing_plan_position_shift",
            )
        ]

    def __str__(self) -> str:
        return f"{self.position} x{self.position_qty} ({self.shift_type})"
