"""US-07: Admin inventory maintenance in the built-in Django admin site.

Only the Admin group (or a superuser) may view, add, or edit assets. Staff and Students never
reach these pages. Assets are retired, never deleted, so loan history stays intact (D-10).

Status is read-only here: it changes only through checkout, return, and the
"Clear Repair" action below, so every change is logged and the state machine holds.
"""

from django.contrib import admin, messages

from .models import Asset
from .permissions import is_admin
from .services import CheckoutBlocked, LoanService


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("asset_tag", "asset_type", "location", "status", "loan_duration", "is_retired")
    list_filter = ("status", "is_retired", "asset_type", "location")
    search_fields = ("asset_tag",)
    fields = ("asset_tag", "asset_type", "location", "status", "loan_duration", "is_retired")
    readonly_fields = ("status",)
    actions = ["clear_repair", "retire"]

    # Group-based access instead of per-model permissions (D-05).
    def has_module_permission(self, request):
        return is_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_admin(request.user)

    def has_add_permission(self, request):
        return is_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return False  # retire instead

    @admin.action(description="Clear Repair (back to Available)")
    def clear_repair(self, request, queryset):
        cleared = skipped = 0
        for asset in queryset:
            try:
                LoanService.clear_repair(request.user, asset)
                cleared += 1
            except CheckoutBlocked:
                skipped += 1
        self.message_user(request, f"{cleared} item(s) moved back to Available.")
        if skipped:
            self.message_user(request, f"{skipped} item(s) skipped: not in Repair.", messages.WARNING)

    @admin.action(description="Retire (hide from the catalog, keep history)")
    def retire(self, request, queryset):
        checked_out = queryset.filter(status=Asset.Status.CHECKED_OUT).count()
        retired = queryset.exclude(status=Asset.Status.CHECKED_OUT).update(is_retired=True)
        self.message_user(request, f"{retired} item(s) retired.")
        if checked_out:
            self.message_user(
                request, f"{checked_out} item(s) skipped: checked out. Return them first.",
                messages.WARNING,
            )
