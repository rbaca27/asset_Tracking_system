from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

# Temporary demo logins for checking the catalog by hand. US-02 owns the real
# accounts and mock profile fields; delete this command once those land.
DEMO_USERS = [
    ("student1", "Student"),
    ("staff1", "Staff"),
    ("admin1", "Admin"),
]
PASSWORD = "demo-pass-123"


class Command(BaseCommand):
    help = "Create Student, Staff and Admin groups and one demo login for each."

    def handle(self, *args, **options):
        for username, group_name in DEMO_USERS:
            group, _ = Group.objects.get_or_create(name=group_name)
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(PASSWORD)
                user.save()
            user.groups.add(group)
            self.stdout.write(f"{username} ({group_name})")
        self.stdout.write(self.style.SUCCESS(f"Demo password for all three: {PASSWORD}"))
