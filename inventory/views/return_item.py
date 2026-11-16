"""US-04: return an item, with an optional damage note that moves it to Repair. Staff only."""

from django.contrib import messages
from django.shortcuts import redirect, render

from inventory.forms import ReturnForm
from inventory.models import Asset
from inventory.permissions import staff_required
from inventory.services import CheckoutBlocked, DamageNoteRequired, LoanService


@staff_required
def return_item(request):
    form = ReturnForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            loan = LoanService.return_item(
                request.user, data["asset_tag"], data["damaged"], data["condition_note"]
            )
        except DamageNoteRequired:
            form.add_error("condition_note", "A damage note is required.")
        except CheckoutBlocked as blocked:
            form.add_error("asset_tag", str(blocked))
        else:
            if loan.asset.status == Asset.Status.REPAIR:
                messages.warning(request, f"{loan.asset.asset_tag} returned and moved to Repair.")
            else:
                messages.success(request, f"{loan.asset.asset_tag} returned. It is Available.")
            return redirect("inventory:return")
    return render(request, "inventory/return.html", {"form": form})
