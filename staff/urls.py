from django.urls import path, reverse_lazy
from django.views.generic import RedirectView

from .views import (
    AssignmentCreateView,
    AssignmentDeleteFutureView,
    AssignmentDeleteView,
    AssignmentModalView,
    AssignmentPersonOptionsView,
    AssignmentReleaseAllView,
    AssignmentReleaseView,
    AssignmentsView,
    PositionCreateView,
    PositionDeactivateView,
    PositionListView,
    PositionUpdateView,
    ShiftCreateView,
    ShiftDeactivateView,
    ShiftListView,
    ShiftPackageCreateView,
    ShiftTypeActivateView,
    ShiftTypeCreateView,
    ShiftTypeDeactivateView,
    ShiftTypeListView,
    ShiftTypePatternPreviewView,
    ShiftTypeUpdateView,
    ShiftUpdateView,
    StaffHomeView,
    StaffingPlanActivateView,
    StaffingPlanCreateView,
    StaffingPlanDeactivateView,
    StaffingPlanListView,
    StaffingPlanUpdateView,
    StaffRosterView,
    StaffShiftMembershipView,
)

app_name = "staff"

urlpatterns = [
    path("", StaffHomeView.as_view(), name="index"),
    path("roster/", StaffRosterView.as_view(), name="roster"),
    path("staff-members/", StaffShiftMembershipView.as_view(), name="staff_members"),
    path("positions/", PositionListView.as_view(), name="positions_list"),
    path("positions/add/", PositionCreateView.as_view(), name="positions_add"),
    path(
        "positions/<int:pk>/edit/",
        PositionUpdateView.as_view(),
        name="positions_edit",
    ),
    path(
        "positions/<int:pk>/delete/",
        PositionDeactivateView.as_view(),
        name="positions_delete",
    ),
    path(
        "positions/<int:pk>/jd/",
        RedirectView.as_view(url=reverse_lazy("under_construction")),
        name="positions_jd",
    ),
    path("shift-types/", ShiftTypeListView.as_view(), name="shift_types_list"),
    path("shift-types/add/", ShiftTypeCreateView.as_view(), name="shift_types_add"),
    path(
        "shift-types/<int:pk>/edit/",
        ShiftTypeUpdateView.as_view(),
        name="shift_types_edit",
    ),
    path(
        "shift-types/<int:pk>/activate/",
        ShiftTypeActivateView.as_view(),
        name="shift_types_activate",
    ),
    path(
        "shift-types/<int:pk>/delete/",
        ShiftTypeDeactivateView.as_view(),
        name="shift_types_delete",
    ),
    path(
        "shift-types/pattern-preview/",
        ShiftTypePatternPreviewView.as_view(),
        name="shift_types_pattern_preview",
    ),
    path("shifts/", ShiftListView.as_view(), name="shifts_list"),
    path("shifts/add/", ShiftCreateView.as_view(), name="shifts_add"),
    path(
        "shifts/package/add/",
        ShiftPackageCreateView.as_view(),
        name="shifts_package_add",
    ),
    path("shifts/<int:pk>/edit/", ShiftUpdateView.as_view(), name="shifts_edit"),
    path(
        "shifts/<int:pk>/delete/",
        ShiftDeactivateView.as_view(),
        name="shifts_delete",
    ),
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
        "staffing-plans/<int:pk>/activate/",
        StaffingPlanActivateView.as_view(),
        name="staffing_plans_activate",
    ),
    path(
        "staffing-plans/<int:pk>/delete/",
        StaffingPlanDeactivateView.as_view(),
        name="staffing_plans_delete",
    ),
    path("assignments/", AssignmentsView.as_view(), name="assignments"),
    path(
        "assignments/item/<int:item_pk>/modal/",
        AssignmentModalView.as_view(),
        name="assignment_modal",
    ),
    path(
        "assignments/item/<int:item_pk>/person-options/",
        AssignmentPersonOptionsView.as_view(),
        name="assignment_person_options",
    ),
    path(
        "assignments/item/<int:item_pk>/assign/",
        AssignmentCreateView.as_view(),
        name="assignment_add",
    ),
    path(
        "assignments/<int:assignment_pk>/release/",
        AssignmentReleaseView.as_view(),
        name="assignment_release",
    ),
    path(
        "assignments/<int:assignment_pk>/delete/",
        AssignmentDeleteView.as_view(),
        name="assignment_delete",
    ),
    path(
        "assignments/<int:assignment_pk>/delete-future/",
        AssignmentDeleteFutureView.as_view(),
        name="assignment_delete_future",
    ),
    path(
        "assignments/release-all/",
        AssignmentReleaseAllView.as_view(),
        name="assignment_release_all",
    ),
]
