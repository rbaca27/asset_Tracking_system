"""US-09: an Admin creates Staff accounts and adds or removes the Staff role."""

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from inventory.forms import CreateStaffForm, StaffRoleForm
from inventory.permissions import STAFF, admin_required
from inventory.services import AccountService, RoleChangeRefused


@admin_required
def staff_roles(request):
    create_form = CreateStaffForm(prefix="create")
    role_form = StaffRoleForm(prefix="role")
    if request.method == "POST":
        if "create" in request.POST:
            create_form = CreateStaffForm(request.POST, prefix="create")
            if create_form.is_valid():
                try:
                    user = AccountService.create_staff(
                        request.user,
                        create_form.cleaned_data["username"],
                        create_form.cleaned_data["password"],
                    )
                except RoleChangeRefused as refused:
                    create_form.add_error("username", str(refused))
                except ValidationError as weak:
                    create_form.add_error("password", weak)
                else:
                    messages.success(request, f"Staff account {user.username} created.")
                    return redirect("inventory:staff_roles")
        else:
            role_form = StaffRoleForm(request.POST, prefix="role")
            if role_form.is_valid():
                try:
                    user = AccountService.set_staff_role(
                        request.user, role_form.cleaned_data["username"], on=True
                    )
                except RoleChangeRefused as refused:
                    role_form.add_error("username", str(refused))
                else:
                    messages.success(request, f"{user.username} now has the Staff role.")
                    return redirect("inventory:staff_roles")
    return render(request, "inventory/staff_roles.html", {
        "create_form": create_form,
        "role_form": role_form,
        "staff_members": User.objects.filter(groups__name=STAFF).order_by("username"),
    })


@admin_required
@require_POST
def remove_staff_role(request):
    try:
        user = AccountService.set_staff_role(request.user, request.POST.get("username"), on=False)
    except RoleChangeRefused as refused:
        messages.error(request, str(refused))
    else:
        messages.success(request, f"Removed the Staff role from {user.username}.")
    return redirect("inventory:staff_roles")
