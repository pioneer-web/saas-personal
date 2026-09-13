import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workouts", "0001_initial"),
    ]

    operations = [

        migrations.CreateModel(
            name="WorkoutSession",
            fields=[
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="organizations.organization",
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("in_progress", "Em andamento"),
                            ("completed", "Concluído"),
                            ("canceled", "Cancelado"),
                        ],
                        default="in_progress",
                        max_length=20,
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "routine",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sessions",
                        to="workouts.workoutroutine",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="workout_sessions",
                        to="students.student",
                    ),
                ),
            ],
            options={
                "ordering": ["-started_at"],
            },
        ),

        migrations.CreateModel(
            name="WorkoutSetLog",
            fields=[
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="organizations.organization",
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "set_number",
                    models.PositiveSmallIntegerField(),
                ),
                (
                    "reps_done",
                    models.CharField(
                        blank=True,
                        max_length=40,
                        verbose_name="Repetições realizadas",
                    ),
                ),
                (
                    "load_kg",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=7,
                        null=True,
                        verbose_name="Carga utilizada",
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="set_logs",
                        to="workouts.workoutsession",
                    ),
                ),
                (
                    "workout_exercise",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="set_logs",
                        to="workouts.workoutexercise",
                    ),
                ),
            ],
            options={
                "ordering": [
                    "workout_exercise__order",
                    "set_number",
                ],
            },
        ),

        migrations.AddConstraint(
            model_name="workoutsetlog",
            constraint=models.UniqueConstraint(
                fields=(
                    "session",
                    "workout_exercise",
                    "set_number",
                ),
                name="unique_workout_set_log",
            ),
        ),
    ]
