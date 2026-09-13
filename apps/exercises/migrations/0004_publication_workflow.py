import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def mark_globals_approved(apps, schema_editor):
    Exercise = apps.get_model(
        "exercises",
        "Exercise",
    )

    Exercise.objects.filter(
        organization__isnull=True
    ).update(
        publication_status="approved"
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            "exercises",
            "0003_exercise_media_personalization",
        ),
        migrations.swappable_dependency(
            settings.AUTH_USER_MODEL
        ),
    ]

    operations = [
        migrations.RemoveField(
            model_name="exercise",
            name="custom_image",
        ),
        migrations.RemoveField(
            model_name="exercise",
            name="custom_video",
        ),
        migrations.AddField(
            model_name="exercise",
            name="published_from",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=
                    django.db.models.deletion.SET_NULL,
                related_name="published_versions",
                to="exercises.exercise",
            ),
        ),
        migrations.AddField(
            model_name="exercise",
            name="publication_status",
            field=models.CharField(
                choices=[
                    ("private", "Privado"),
                    (
                        "pending",
                        "Aguardando aprovação",
                    ),
                    ("approved", "Aprovado"),
                    ("rejected", "Rejeitado"),
                ],
                default="private",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="exercise",
            name="publication_requested_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="exercise",
            name="publication_reviewed_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="exercise",
            name="publication_rejection_reason",
            field=models.TextField(
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name="exercise",
            name="publication_reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=
                    django.db.models.deletion.SET_NULL,
                related_name=
                    "reviewed_exercises",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(
            mark_globals_approved,
            migrations.RunPython.noop,
        ),
    ]
