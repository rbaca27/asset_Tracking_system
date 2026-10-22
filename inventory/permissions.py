from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def staff_required(view):
    """Signed-out visitors go to sign-in; signed-in non-Staff/Admin users get 403."""

    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.groups.filter(name__in=["Staff", "Admin"]).exists():
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper
