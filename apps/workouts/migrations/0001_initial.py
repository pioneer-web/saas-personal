import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        ("students", "0001_initial"),
        ("exercises", "0001_initial"),
    ]

    operations = [

        migrations.CreateModel(
            name="WorkoutPlan",
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
                    "name",
                    models.CharField(
                        max_length=160,
                        verbose_name="Nome do plano",
                    ),
                ),
                (
                    "objective",
                    models.CharField(
                        blank=True,
                        max_length=160,
                        verbose_name="Objetivo",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Rascunho"),
                            ("active", "Ativo"),
                            ("paused", "Pausado"),
                            ("finished", "Finalizado"),
                        ],
                        default="active",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "start_date",
                    models.DateField(
                        blank=True,
                        null=True,
                        verbose_name="Início",
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        blank=True,
                        null=True,
                        verbose_name="Fim",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        verbose_name="Observações",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="workout_plans",
                        to="students.student",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),

        migrations.CreateModel(
            name="WorkoutRoutine",
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
                    "name",
                    models.CharField(
                        max_length=80,
                        verbose_name="Nome",
                    ),
                ),
                (
                    "order",
                    models.PositiveSmallIntegerField(
                        default=1,
                        verbose_name="Ordem",
                    ),
                ),
                (
                    "instructions",
                    models.TextField(
                        blank=True,
                        verbose_name="Orientações",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="routines",
                        to="workouts.workoutplan",
                    ),
                ),
            ],
            options={
                "ordering": ["order", "name"],
            },
        ),

        migrations.CreateModel(
            name="WorkoutExercise",
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
                    "order",
                    models.PositiveSmallIntegerField(
                        default=1,
                    ),
                ),
                (
                    "sets",
                    models.PositiveSmallIntegerField(
                        default=3,
                        verbose_name="Séries",
                    ),
                ),
                (
                    "reps",
                    models.CharField(
                        default="10-12",
                        max_length=40,
                        verbose_name="Repetições",
                    ),
                ),
                (
                    "load_kg",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=7,
                        null=True,
                        verbose_name="Carga (kg)",
                    ),
                ),
                (
                    "rest_seconds",
                    models.PositiveIntegerField(
                        default=60,
                        verbose_name="Descanso (segundos)",
                    ),
                ),
                (
                    "cadence",
                    models.CharField(
                        blank=True,
                        max_length=40,
                        verbose_name="Cadência",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        verbose_name="Observações",
                    ),
                ),
                (
                    "exercise",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="workout_items",
                        to="exercises.exercise",
                    ),
                ),
                (
                    "routine",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="workouts.workoutroutine",
                    ),
                ),
            ],
            options={
                "ordering": ["order"],
            },
        ),
    ]
