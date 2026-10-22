from django.http import HttpResponse
from django.views.generic import ListView

from .forms import CatalogFilterForm
from .models import Asset
from .permissions import staff_required

# The only columns the public catalog may read. Borrower data never reaches this page.
PUBLIC_FIELDS = ("asset_tag", "asset_type", "location", "status")


class CatalogView(ListView):
    template_name = "inventory/catalog.html"
    context_object_name = "assets"

    def get_queryset(self):
        assets = Asset.objects.filter(is_retired=False).only(*PUBLIC_FIELDS)
        self.form = CatalogFilterForm(self.request.GET or None)
        if self.form.is_valid():
            data = self.form.cleaned_data
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
        context["form"] = self.form
        return context


@staff_required
def checkout(request):
    # Placeholder so the Staff-only rule can be tested now. US-03 replaces the body.
    return HttpResponse("Checkout form: built in US-03")
