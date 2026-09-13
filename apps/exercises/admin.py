from django.contrib import admin
from django.utils import timezone

from .models import Exercise


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):

    list_display = (
        "display_name",
        "organization",
        "publication_status",
        "media_provider",
    )

    list_filter = (
        "publication_status",
        "organization",
        "category",
    )

    search_fields = (
        "name",
        "name_ptbr",
        "primary_muscle",
        "primary_muscle_ptbr",
    )

    readonly_fields = (
        "publication_requested_at",
        "publication_reviewed_at",
        "publication_reviewed_by",
    )

    actions = [
        "approve_publication",
        "reject_publication",
    ]

    @admin.action(
        description="Aprovar publicação na biblioteca"
    )
    def approve_publication(
        self,
        request,
        queryset,
    ):
        count = 0

        for exercise in queryset.filter(
            publication_status=
                Exercise.PublicationStatus.PENDING,
            organization__isnull=False,
        ):
            exercise.publish_as_global(
                request.user
            )
            count += 1

        self.message_user(
            request,
            f"{count} exercício(s) aprovado(s).",
        )

    @admin.action(
        description="Rejeitar solicitação"
    )
    def reject_publication(
        self,
        request,
        queryset,
    ):
        updated = queryset.filter(
            publication_status=
                Exercise.PublicationStatus.PENDING,
            organization__isnull=False,
        ).update(
            publication_status=
                Exercise.PublicationStatus.REJECTED,
            publication_reviewed_at=
                timezone.now(),
            publication_reviewed_by=
                request.user,
        )

        self.message_user(
            request,
            f"{updated} solicitação(ões) rejeitada(s).",
        )
