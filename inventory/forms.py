from django import forms

from .models import Asset


def text_box(placeholder):
    return forms.TextInput(attrs={"class": "form-control", "placeholder": placeholder})


class CatalogFilterForm(forms.Form):
    q = forms.CharField(required=False, widget=text_box("Asset tag"))
    asset_type = forms.CharField(required=False, widget=text_box("Type"))
    location = forms.CharField(required=False, widget=text_box("Location"))
    status = forms.ChoiceField(
        required=False,
        choices=[("", "Any status")] + list(Asset.Status.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
