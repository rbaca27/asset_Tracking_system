"""US-06: the Staff overdue list and the in-app event log.

Opening the overdue list first flags loans that became late since the last visit (one
OVERDUE_FLAG event per loan, D-08). The event log never shows borrowers: Staff see a borrower and
an item together only on the checkout, return, and overdue screens (Section 2.5).
"""

from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone

from inventory.models import LoanEvent
from inventory.permissions import staff_required
from inventory.services import LoanService


@staff_required
def overdue(request):
    now = timezone.now()
    LoanService.flag_overdue(now)
    loans = [(loan, loan.days_overdue(now)) for loan in LoanService.overdue_loans(now)]
    return render(request, "inventory/overdue.html", {"loans": loans})


@staff_required
def event_log(request):
    events = LoanEvent.objects.select_related("asset", "actor")
    page = Paginator(events, 50).get_page(request.GET.get("page"))
    return render(request, "inventory/event_log.html", {"page": page})
