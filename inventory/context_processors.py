"""Puts the signed-in user's roles into every template so the navbar shows the right links."""

from .permissions import is_admin, is_staff_member, is_student


def roles(request):
    user = request.user
    return {
        "is_student_user": is_student(user),
        "is_staff_user": is_staff_member(user),
        "is_admin_user": is_admin(user),
    }
