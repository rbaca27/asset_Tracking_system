"""URL list for the inventory app. One section per user story."""

from django.urls import path

from .views import (
    activate, catalog, checkout, my_loans, overdue, return_item, roster_import, staff_roles,
)

app_name = "inventory"

urlpatterns = [
    # US-01: public catalog
    path("catalog/", catalog.CatalogView.as_view(), name="catalog"),
    # US-02: Admin roster import
    path("accounts/roster/", roster_import.roster_import, name="roster_import"),
    # US-03: Staff checkout
    path("checkout/", checkout.checkout, name="checkout"),
    # US-04: Staff return with optional damage note
    path("return/", return_item.return_item, name="return"),
    # US-05: a student's own loans (never takes an account ID)
    path("my-loans/", my_loans.my_loans, name="my_loans"),
    path("my-loans/<int:pk>/", my_loans.loan_detail, name="loan_detail"),
    # US-06: Staff overdue list and event log
    path("overdue/", overdue.overdue, name="overdue"),
    path("event-log/", overdue.event_log, name="event_log"),
    # US-08: one-time account activation
    path("accounts/activate/", activate.activate, name="activate"),
    # US-09: Admin Staff accounts and roles
    path("accounts/staff/", staff_roles.staff_roles, name="staff_roles"),
    path("accounts/staff/remove/", staff_roles.remove_staff_role, name="remove_staff_role"),
]
