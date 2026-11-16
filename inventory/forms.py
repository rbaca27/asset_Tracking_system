from django import forms

from .models import Asset


def text_box(placeholder, **attrs):
    return forms.TextInput(attrs={"class": "form-control", "placeholder": placeholder, **attrs})


class CatalogFilterForm(forms.Form):
    q = forms.CharField(required=False, widget=text_box("Asset tag"))
    asset_type = forms.CharField(required=False, widget=text_box("Type"))
    location = forms.CharField(required=False, widget=text_box("Location"))
    status = forms.ChoiceField(
        required=False,
        choices=[("", "Any status")] + list(Asset.Status.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )


# --- US-03 / US-04: desk forms, one screen each, typed input only ----------------


class CheckoutForm(forms.Form):
    # One typed field for the borrower (D-12): no list of students is ever rendered.
    borrower = forms.CharField(
        label="Borrower username or mock Panther ID", max_length=150,
        widget=text_box("e.g. zquin001 or 6000001", autofocus=True, autocomplete="off"),
    )
    asset_tag = forms.CharField(
        label="Asset tag", max_length=32, widget=text_box("e.g. CHG-001", autocomplete="off")
    )


class ReturnForm(forms.Form):
    asset_tag = forms.CharField(
        label="Asset tag", max_length=32,
        widget=text_box("e.g. CHG-001", autofocus=True, autocomplete="off"),
    )
    damaged = forms.BooleanField(
        label="Damaged", required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    condition_note = forms.CharField(
        label="Condition note (required if damaged)", required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )

    def clean(self):
        data = super().clean()
        if data.get("damaged") and not (data.get("condition_note") or "").strip():
            self.add_error("condition_note", "A damage note is required.")
        return data


# --- US-02 / US-08 / US-09: accounts -------------------------------------------


class RosterImportForm(forms.Form):
    term = forms.CharField(label="Term", max_length=32, widget=text_box("e.g. Spring 2027"))
    roster = forms.FileField(
        label="Roster CSV",
        help_text="Columns: panther_id, username, display_name, email, phone.",
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".csv"}),
    )


class ActivationForm(forms.Form):
    username = forms.CharField(max_length=150, widget=text_box("Username", autofocus=True))
    code = forms.CharField(label="One-time activation code", max_length=32, widget=text_box("Code"))
    password1 = forms.CharField(
        label="Choose a password", widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    password2 = forms.CharField(
        label="Type it again", widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    def clean(self):
        data = super().clean()
        if data.get("password1") and data.get("password1") != data.get("password2"):
            self.add_error("password2", "The two passwords do not match.")
        return data


class CreateStaffForm(forms.Form):
    username = forms.CharField(max_length=150, widget=text_box("Username"))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))


class StaffRoleForm(forms.Form):
    username = forms.CharField(max_length=150, widget=text_box("Existing username"))
