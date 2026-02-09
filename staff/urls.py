from django.urls import path
from django.views.generic import RedirectView

from .views import (
    StaffHomeView,
    # Positions
    PositionListView,
    PositionCreateView,
    PositionUpdateView,
    PositionDeactivateView,
    # Shift types
    ShiftTypeListView,
    ShiftTypeCreateView,
    ShiftTypeUpdateView,
    ShiftTypeDeactivateView,
    # Shifts
    ShiftListView,
    ShiftCreateView,
    ShiftUpdateView,
    ShiftDeactivateView,
    # Staffing Plans
    StaffingPlanListView,
    StaffingPlanCreateView,
    StaffingPlanUpdateView,
    StaffingPlanDeactivateView,
)

app_name = "staff"

urlpatterns = [
    path("", StaffHomeView.as_view(), name="index"),
    # -----------------
    # Positions
    # -----------------
    path("positions/", PositionListView.as_view(), name="positions_list"),
    path("positions/add/", PositionCreateView.as_view(), name="positions_add"),
    path(
        "positions/<int:pk>/edit/", PositionUpdateView.as_view(), name="positions_edit"
    ),
    path(
        "positions/<int:pk>/delete/",
        PositionDeactivateView.as_view(),
        name="positions_delete",
    ),
    path(
        "positions/<int:pk>/jd/",
        RedirectView.as_view(pattern_name="under_construction"),
        name="positions_jd",
    ),
    # -----------------
    # Shift types
    # -----------------
    path("shift-types/", ShiftTypeListView.as_view(), name="shift_types_list"),
    path("shift-types/add/", ShiftTypeCreateView.as_view(), name="shift_types_add"),
    path(
        "shift-types/<int:pk>/edit/",
        ShiftTypeUpdateView.as_view(),
        name="shift_types_edit",
    ),
    path(
        "shift-types/<int:pk>/delete/",
        ShiftTypeDeactivateView.as_view(),
        name="shift_types_delete",
    ),
    # -----------------
    # Shifts
    # -----------------
    path("shifts/", ShiftListView.as_view(), name="shifts_list"),
    path("shifts/add/", ShiftCreateView.as_view(), name="shifts_add"),
    path("shifts/<int:pk>/edit/", ShiftUpdateView.as_view(), name="shifts_edit"),
    path(
        "shifts/<int:pk>/delete/", ShiftDeactivateView.as_view(), name="shifts_delete"
    ),
    # -----------------
    # Staffing plans
    # -----------------
    path("staffing-plans/", StaffingPlanListView.as_view(), name="staffing_plans_list"),
    path(
        "staffing-plans/add/",
        StaffingPlanCreateView.as_view(),
        name="staffing_plans_add",
    ),
    path(
        "staffing-plans/<int:pk>/edit/",
        StaffingPlanUpdateView.as_view(),
        name="staffing_plans_edit",
    ),
    path(
        "staffing-plans/<int:pk>/delete/",
        StaffingPlanDeactivateView.as_view(),
        name="staffing_plans_delete",
    ),
]
