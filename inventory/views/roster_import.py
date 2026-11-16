"""US-02: an Admin imports the department's semester enrollment roster (CSV)."""

from django.shortcuts import render

from inventory.forms import RosterImportForm
from inventory.permissions import admin_required
from inventory.services import AccountService, RosterInvalid


@admin_required
def roster_import(request):
    form = RosterImportForm(request.POST or None, request.FILES or None)
    context = {"form": form}
    if request.method == "POST" and form.is_valid():
        try:
            record, codes = AccountService.import_roster(
                request.user, form.cleaned_data["roster"], form.cleaned_data["term"]
            )
        except RosterInvalid as invalid:
            context["row_errors"] = invalid.errors
        else:
            # Codes are shown once, here, and stored only as hashes.
            context.update(record=record, codes=codes, form=RosterImportForm())
    return render(request, "inventory/roster_import.html", context)
