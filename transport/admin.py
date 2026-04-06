from django.contrib import admin

from .models import (
    TransportModelOperationalParameter,
    TransportModelTechnicalParameter,
    TransportOperationalParameter,
    TransportTechnicalParameter,
    TransportUnit,
    TransportUnitModel,
    TransportUnitOperationalValue,
    TransportUnitType,
)


# =========================
# Transport Unit Type
# =========================
@admin.register(TransportUnitType)
class TransportUnitTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "code", "is_active")
    search_fields = ("name", "code", "company__name")
    list_filter = ("company", "is_active")
    ordering = ("company__name", "name")


# =========================
# Technical Parameters
# =========================
@admin.register(TransportTechnicalParameter)
class TransportTechnicalParameterAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "code", "data_type", "unit", "is_active")
    search_fields = ("name", "code", "company__name")
    list_filter = ("company", "data_type", "is_active")
    ordering = ("company__name", "name")


# =========================
# Operational Parameters
# =========================
@admin.register(TransportOperationalParameter)
class TransportOperationalParameterAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "code", "data_type", "unit", "is_active")
    search_fields = ("name", "code", "company__name")
    list_filter = ("company", "data_type", "is_active")
    ordering = ("company__name", "name")


# =========================
# Inline: Technical Parameters for Model
# =========================
class TransportModelTechnicalParameterInline(admin.TabularInline):
    model = TransportModelTechnicalParameter
    extra = 1
    fields = (
        "parameter",
        "display_order",
        "is_required",
        "value_integer",
        "value_decimal",
        "value_text",
        "value_boolean",
    )
    ordering = ("display_order",)


# =========================
# Inline: Operational Parameters for Model
# =========================
class TransportModelOperationalParameterInline(admin.TabularInline):
    model = TransportModelOperationalParameter
    extra = 1
    fields = (
        "parameter",
        "display_order",
        "is_required",
        "min_value",
        "max_value",
        "max_technical_parameter",
    )
    ordering = ("display_order",)


# =========================
# Transport Unit Model
# =========================
@admin.register(TransportUnitModel)
class TransportUnitModelAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "type", "code", "is_active")
    search_fields = ("name", "code", "company__name", "type__name", "type__code")
    list_filter = ("company", "type", "is_active")
    ordering = ("company__name", "type__name", "name")

    inlines = [
        TransportModelTechnicalParameterInline,
        TransportModelOperationalParameterInline,
    ]


# =========================
# Inline: Operational values for Unit
# =========================
class TransportUnitOperationalValueInline(admin.TabularInline):
    model = TransportUnitOperationalValue
    extra = 1
    fields = (
        "parameter",
        "value_integer",
        "value_decimal",
        "value_text",
        "value_boolean",
        "updated_at",
    )
    readonly_fields = ("updated_at",)
    ordering = ("parameter__name",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parameter":
            obj = getattr(request, "_transport_unit_obj", None)

            if obj and obj.model_id:
                kwargs["queryset"] = (
                    TransportOperationalParameter.objects.filter(
                        model_links__model=obj.model
                    )
                    .distinct()
                    .order_by("name")
                )
            else:
                kwargs["queryset"] = TransportOperationalParameter.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# =========================
# Transport Unit
# =========================
@admin.register(TransportUnit)
class TransportUnitAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "model",
        "technical_status",
        "identifier",
        "is_active",
        "created_at",
    )
    search_fields = (
        "name",
        "identifier",
        "company__name",
        "model__name",
        "model__code",
        "model__type__name",
        "model__type__code",
    )
    list_filter = ("company", "model", "technical_status", "is_active")
    ordering = ("company__name", "name")

    inlines = [
        TransportUnitOperationalValueInline,
    ]

    def get_form(self, request, obj=None, **kwargs):
        request._transport_unit_obj = obj
        return super().get_form(request, obj, **kwargs)