import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria/atualiza o superadmin a partir do .env"

    def handle(self, *args, **options):
        email = os.getenv("SUPERADMIN_EMAIL", "").strip().lower()
        password = os.getenv("SUPERADMIN_PASSWORD", "").strip()
        name = os.getenv("SUPERADMIN_NAME", "Administrador").strip()

        if not email or not password:
            self.stdout.write(self.style.WARNING("SUPERADMIN_EMAIL/SUPERADMIN_PASSWORD não definidos; ignorando."))
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(email=email, defaults={"name": name})
        user.name = name
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()
        action = "criado" if created else "atualizado"
        self.stdout.write(self.style.SUCCESS(f"Superadmin {action}: {email}"))
