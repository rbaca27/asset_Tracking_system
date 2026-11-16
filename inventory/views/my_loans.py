"""US-05: a signed-in user's own loans and profile.

No account ID is ever read from the URL or the query string: every query is scoped to
request.user (design decision D-07). Another student's loan ID returns 404, not 403, so the page
does not even confirm that the loan exists.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from inventory.models import Loan, Profile


def _own_loans(user):
    return Loan.objects.filter(borrower=user).select_related("asset")


@login_required
def my_loans(request):
    return render(request, "inventory/my_loans.html", {
        "loans": _own_loans(request.user).filter(returned_at__isnull=True).order_by("due_at"),
        "profile": Profile.objects.filter(user=request.user).first(),
        "now": timezone.now(),
    })


@login_required
def loan_detail(request, pk):
    loan = get_object_or_404(_own_loans(request.user), pk=pk)
    return render(request, "inventory/loan_detail.html", {"loan": loan, "now": timezone.now()})
