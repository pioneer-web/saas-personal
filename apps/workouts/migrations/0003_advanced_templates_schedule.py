import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workouts", "0002_workout_execution"),
    ]

    operations = [
        migrations.AddField(
            model_name="workoutexercise",
            name="method",
            field=models.CharField(
                choices=[
                    ("normal", "Normal"),
                    ("warmup", "Aquecimento"),
                    ("superset", "Supersérie"),
                    ("biset", "Bi-set"),
                    ("triset", "Tri-set"),
                    ("dropset", "Drop-set"),
                    ("circuit", "Circuito"),
                    ("time", "Por tempo"),
                ],
                default="normal",
                max_length=20,
                verbose_name="Método",
            ),
        ),
        migrations.AddField(
            model_name="workoutexercise",
            name="group_code",
            field=models.CharField(blank=True, max_length=20, verbose_name="Grupo/Bloco"),
        ),
        migrations.AddField(
            model_name="workoutexercise",
            name="target_seconds",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="Tempo alvo (segundos)"),
        ),
        migrations.AddField(
            model_name="workoutexercise",
            name="rpe_target",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(10),
                ],
                verbose_name="RPE alvo",
            ),
        ),
        migrations.AddField(
            model_name="workoutexercise",
            name="rir_target",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(10),
                ],
                verbose_name="RIR alvo",
            ),
        ),
        migrations.AddField(
            model_name="workoutexercise",
            name="progression_enabled",
            field=models.BooleanField(default=True, verbose_name="Sugerir progressão"),
        ),
        migrations.AddField(
            model_name="workoutexercise",
            name="progression_increment_kg",
            field=models.DecimalField(
                decimal_places=2,
                default=2.5,
                max_digits=5,
                verbose_name="Incremento sugerido (kg)",
            ),
        ),
        migrations.AddField(
            model_name="workoutsetlog",
            name="rpe_actual",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(10),
                ],
                verbose_name="RPE realizado",
            ),
        ),
        migrations.AddField(
            model_name="workoutsetlog",
            name="rir_actual",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(10),
                ],
                verbose_name="RIR realizado",
            ),
        ),
        migrations.CreateModel(
            name="WorkoutTemplate",
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
                ("name", models.CharField(max_length=160, verbose_name="Nome do modelo")),
                ("objective", models.CharField(blank=True, max_length=160, verbose_name="Objetivo")),
                ("notes", models.TextField(blank=True, verbose_name="Observações")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "source_plan",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="saved_templates",
                        to="workouts.workoutplan",
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="WorkoutTemplateRoutine",
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
                ("name", models.CharField(max_length=80)),
                ("order", models.PositiveSmallIntegerField(default=1)),
                ("instructions", models.TextField(blank=True)),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="routines",
                        to="workouts.workouttemplate",
                    ),
                ),
            ],
            options={"ordering": ["order", "name"]},
        ),
        migrations.CreateModel(
            name="WorkoutTemplateExercise",
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
                ("order", models.PositiveSmallIntegerField(default=1)),
                ("sets", models.PositiveSmallIntegerField(default=3)),
                ("reps", models.CharField(default="10-12", max_length=40)),
                ("load_kg", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ("rest_seconds", models.PositiveIntegerField(default=60)),
                ("cadence", models.CharField(blank=True, max_length=40)),
                ("notes", models.TextField(blank=True)),
                (
                    "method",
                    models.CharField(
                        choices=[
                            ("normal", "Normal"),
                            ("warmup", "Aquecimento"),
                            ("superset", "Supersérie"),
                            ("biset", "Bi-set"),
                            ("triset", "Tri-set"),
                            ("dropset", "Drop-set"),
                            ("circuit", "Circuito"),
                            ("time", "Por tempo"),
                        ],
                        default="normal",
                        max_length=20,
                    ),
                ),
                ("group_code", models.CharField(blank=True, max_length=20)),
                ("target_seconds", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "rpe_target",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(10),
                        ],
                    ),
                ),
                (
                    "rir_target",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(10),
                        ],
                    ),
                ),
                ("progression_enabled", models.BooleanField(default=True)),
                ("progression_increment_kg", models.DecimalField(decimal_places=2, default=2.5, max_digits=5)),
                (
                    "exercise",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="template_items",
                        to="exercises.exercise",
                    ),
                ),
                (
                    "routine",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="workouts.workouttemplateroutine",
                    ),
                ),
            ],
            options={"ordering": ["order"]},
        ),
        migrations.CreateModel(
            name="WorkoutSchedule",
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
                    "weekday",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Segunda"),
                            (1, "Terça"),
                            (2, "Quarta"),
                            (3, "Quinta"),
                            (4, "Sexta"),
                            (5, "Sábado"),
                            (6, "Domingo"),
                        ],
                        verbose_name="Dia da semana",
                    ),
                ),
                ("time", models.TimeField(blank=True, null=True, verbose_name="Horário")),
                ("is_active", models.BooleanField(default=True)),
                (
                    "routine",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="schedules",
                        to="workouts.workoutroutine",
                    ),
                ),
            ],
            options={"ordering": ["weekday", "time"]},
        ),
        migrations.AddConstraint(
            model_name="workoutschedule",
            constraint=models.UniqueConstraint(
                fields=("routine", "weekday"),
                name="unique_routine_weekday",
            ),
        ),
    ]
