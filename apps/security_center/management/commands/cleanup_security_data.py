from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.security_center.models import SecurityEvent, SecurityThrottle


class Command(BaseCommand):
    help = "Remove dados temporários/antigos do módulo de segurança."

    def handle(self, *args, **options):
        now = timezone.now()

        throttles_deleted, _ = SecurityThrottle.objects.filter(
            updated_at__lt=now - timedelta(days=2)
        ).delete()

        events_deleted, _ = SecurityEvent.objects.filter(
            created_at__lt=now - timedelta(days=90)
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Limpeza concluída: "
                f"{throttles_deleted} throttles e "
                f"{events_deleted} eventos removidos."
            )
        )
