"""US-03: Staff checkout. Only the access rule is real so far."""

from django.http import HttpResponse

from inventory.permissions import staff_required


@staff_required
def checkout(request):
    # Placeholder so the Staff-only rule can be tested now.
    # US-03: replace the body, keep the @staff_required decorator.
    return HttpResponse("Checkout form: built in US-03")
