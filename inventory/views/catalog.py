"""US-01: the public catalog. Anyone can view it; it never reads borrower data."""

from django.views.generic import ListView

from inventory.forms import CatalogFilterForm
from inventory.models import Asset

# The only columns the public catalog may read. Borrower data never reaches this page.
PUBLIC_FIELDS = ("asset_tag", "asset_type", "location", "status")


class CatalogView(ListView):
    template_name = "inventory/catalog.html"
    context_object_name = "assets"

    def get_queryset(self):
        assets = Asset.objects.filter(is_retired=False).only(*PUBLIC_FIELDS)
        self.form = CatalogFilterForm(self.request.GET or None)
        if self.form.is_valid():
            assets = self.apply_filters(assets, self.form.cleaned_data)
        return assets

    @staticmethod
    def apply_filters(assets, data):
        """Narrow the query one filled-in box at a time; blank boxes are ignored."""
        if data["q"]:
            assets = assets.filter(asset_tag__icontains=data["q"])
        if data["asset_type"]:
            assets = assets.filter(asset_type__icontains=data["asset_type"])
        if data["location"]:
            assets = assets.filter(location__icontains=data["location"])
        if data["status"]:
            assets = assets.filter(status=data["status"])
        return assets

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = self.form  # keeps what the user typed in the filter boxes
        return context
