"""URL list for the inventory app. One section per user story."""

from django.urls import path

from .views import catalog, checkout

app_name = "inventory"

urlpatterns = [
    # US-01: public catalog
    path("catalog/", catalog.CatalogView.as_view(), name="catalog"),
    # US-03: Staff checkout (placeholder)
    path("checkout/", checkout.checkout, name="checkout"),
]
