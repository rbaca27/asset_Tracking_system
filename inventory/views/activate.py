"""US-08: a rostered student activates once with a one-time code, then signs in normally.

Later sign-ins use Django's LoginView (config/urls.py), which refuses deactivated accounts and
shows one generic error for a wrong username or password.
"""

from django.contrib.auth import login
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from inventory.forms import ActivationForm
from inventory.services import AccountService, ActivationFailed

GENERIC_FAILURE = "Could not activate. Check your username and code, or ask the desk for a new code."


def activate(request):
    form = ActivationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            user = AccountService.activate(data["username"], data["code"], data["password1"])
        except ActivationFailed:
            form.add_error(None, GENERIC_FAILURE)
        except ValidationError as weak:
            form.add_error("password1", weak)
        else:
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("inventory:my_loans")
    return render(request, "registration/activate.html", {"form": form})
