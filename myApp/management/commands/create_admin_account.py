from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ensure a local admin user (username=admin, password=admin) exists. DO NOT use in production."

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True},
        )
        user.is_staff = True
        user.is_superuser = True
        if created:
            user.set_password("admin")
            user.save()
            self.stdout.write(self.style.SUCCESS("Created admin user with password 'admin'"))
        else:
            user.save(update_fields=["is_staff", "is_superuser"])
            self.stdout.write(
                self.style.WARNING("Admin user already exists. (Password unchanged)")
            )
