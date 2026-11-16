"""Create the Student, Staff and Admin groups (D-05) so every database starts with them."""

from django.db import migrations

ROLES = ("Student", "Staff", "Admin")


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ROLES:
        Group.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("inventory", "0002_loans_accounts_event_log"),
    ]

    operations = [migrations.RunPython(create_groups, migrations.RunPython.noop)]
