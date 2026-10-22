from django.contrib import admin

from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("asset_tag", "asset_type", "location", "status", "is_retired")
    list_filter = ("status", "asset_type", "location")
    search_fields = ("asset_tag",)
