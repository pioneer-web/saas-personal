import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Cria o superadmin a partir do .env. "
        "Não redefine senha em todo restart."
    )

    def handle(self, *args, **options):
        email = (
            os.getenv("SUPERADMIN_EMAIL", "")
            .strip()
            .lower()
        )
        password = os.getenv(
            "SUPERADMIN_PASSWORD",
            "",
        ).strip()
        name = os.getenv(
            "SUPERADMIN_NAME",
            "Administrador",
        ).strip()
        rotate = (
            os.getenv(
                "SUPERADMIN_ROTATE_PASSWORD",
                "0",
            )
            .strip()
            .lower()
            in {"1", "true", "yes", "on"}
        )

        if not email:
            self.stdout.write(
                self.style.WARNING(
                    "SUPERADMIN_EMAIL não definido; ignorando."
                )
            )
            return

        User = get_user_model()
        user = User.objects.filter(email=email).first()

        if not user:
            if not password:
                raise CommandError(
                    "SUPERADMIN_PASSWORD é obrigatório "
                    "para criar o superadmin."
                )

            candidate = User(email=email, name=name)

            try:
                validate_password(password, candidate)
            except ValidationError as exc:
                raise CommandError(
                    "Senha do superadmin não atende "
                    "a política de segurança: "
                    + " ".join(exc.messages)
                )

            user = User.objects.create_superuser(
                email=email,
                password=password,
                name=name,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Superadmin criado: {email}"
                )
            )
            return

        changed = False

        if user.name != name:
            user.name = name
            changed = True

        if not user.is_staff:
            user.is_staff = True
            changed = True

        if not user.is_superuser:
            user.is_superuser = True
            changed = True

        if not user.is_active:
            user.is_active = True
            changed = True

        if rotate:
            if not password:
                raise CommandError(
                    "SUPERADMIN_ROTATE_PASSWORD=1 "
                    "exige SUPERADMIN_PASSWORD."
                )

            try:
                validate_password(password, user)
            except ValidationError as exc:
                raise CommandError(
                    "Nova senha do superadmin não atende "
                    "a política: "
                    + " ".join(exc.messages)
                )

            user.set_password(password)
            changed = True

        if changed:
            user.save()

        if rotate:
            message = "Superadmin atualizado e senha rotacionada."
        elif changed:
            message = "Superadmin atualizado sem alterar a senha."
        else:
            message = "Superadmin já existe; senha preservada."

        self.stdout.write(self.style.SUCCESS(message))
