from django.urls import path

from . import views

app_name = "inventory"
urlpatterns = [
    path("catalog/", views.CatalogView.as_view(), name="catalog"),
    path("checkout/", views.checkout, name="checkout"),
]
