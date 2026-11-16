"""US-03: walk-up checkout at the desk. Staff only; one screen, typed input."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.formats import date_format

from inventory.forms import CheckoutForm
from inventory.permissions import staff_required
from inventory.services import BorrowerNotFound, CheckoutBlocked, LoanService


@staff_required
def checkout(request):
    form = CheckoutForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            loan = LoanService.checkout(
                request.user, form.cleaned_data["borrower"], form.cleaned_data["asset_tag"]
            )
        except BorrowerNotFound:
            form.add_error("borrower", "No active student account matches.")
        except CheckoutBlocked as blocked:
            form.add_error("asset_tag", str(blocked))
        else:
            due = date_format(timezone.localtime(loan.due_at), "DATETIME_FORMAT")
            messages.success(
                request,
                f"{loan.asset.asset_tag} checked out to {loan.borrower.username}. Due {due}.",
            )
            return redirect("inventory:checkout")
    return render(request, "inventory/checkout.html", {"form": form})
