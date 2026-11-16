"""Role checks. Roles are Django Groups: Student, Staff, Admin (design decision D-05).

An Admin can do everything Staff can do. A Django superuser counts as an Admin.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

STUDENT = "Student"
STAFF = "Staff"
ADMIN = "Admin"


def in_group(user, *names):
    return user.is_authenticated and user.groups.filter(name__in=names).exists()


def is_admin(user):
    return user.is_authenticated and (user.is_superuser or in_group(user, ADMIN))


def is_staff_member(user):
    """Desk workers: the Staff group, plus Admins."""
    return is_admin(user) or in_group(user, STAFF)


def is_student(user):
    return in_group(user, STUDENT)


def _require(check):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not check(request.user):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


# Signed-out visitors go to sign-in; signed-in users without the role get 403.
staff_required = _require(is_staff_member)
admin_required = _require(is_admin)
