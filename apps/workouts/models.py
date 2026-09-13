import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.exercises.models import Exercise
from apps.organizations.models import TenantModel
from apps.students.models import Student


class WorkoutPlan(TenantModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        ACTIVE = "active", "Ativo"
        PAUSED = "paused", "Pausado"
        FINISHED = "finished", "Finalizado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="workout_plans")
    name = models.CharField("Nome do plano", max_length=160)
    objective = models.CharField("Objetivo", max_length=160, blank=True)
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField("Início", null=True, blank=True)
    end_date = models.DateField("Fim", null=True, blank=True)
    notes = models.TextField("Observações", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.student.name}"


class WorkoutRoutine(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE, related_name="routines")
    name = models.CharField("Nome", max_length=80)
    order = models.PositiveSmallIntegerField("Ordem", default=1)
    instructions = models.TextField("Orientações", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class WorkoutExercise(TenantModel):
    class Method(models.TextChoices):
        NORMAL = "normal", "Normal"
        WARMUP = "warmup", "Aquecimento"
        SUPERSET = "superset", "Supersérie"
        BISET = "biset", "Bi-set"
        TRISET = "triset", "Tri-set"
        DROPSET = "dropset", "Drop-set"
        CIRCUIT = "circuit", "Circuito"
        TIME = "time", "Por tempo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    routine = models.ForeignKey(WorkoutRoutine, on_delete=models.CASCADE, related_name="items")
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name="workout_items")
    order = models.PositiveSmallIntegerField(default=1)
    sets = models.PositiveSmallIntegerField("Séries", default=3)
    reps = models.CharField("Repetições", max_length=40, default="10-12")
    load_kg = models.DecimalField("Carga (kg)", max_digits=7, decimal_places=2, null=True, blank=True)
    rest_seconds = models.PositiveIntegerField("Descanso (segundos)", default=60)
    cadence = models.CharField("Cadência", max_length=40, blank=True)
    notes = models.TextField("Observações", blank=True)

    method = models.CharField("Método", max_length=20, choices=Method.choices, default=Method.NORMAL)
    group_code = models.CharField("Grupo/Bloco", max_length=20, blank=True)
    target_seconds = models.PositiveIntegerField("Tempo alvo (segundos)", null=True, blank=True)
    rpe_target = models.PositiveSmallIntegerField(
        "RPE alvo", null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    rir_target = models.PositiveSmallIntegerField(
        "RIR alvo", null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    progression_enabled = models.BooleanField("Sugerir progressão", default=True)
    progression_increment_kg = models.DecimalField(
        "Incremento sugerido (kg)", max_digits=5, decimal_places=2, default=2.50
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.exercise.display_name


class WorkoutSession(TenantModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Em andamento"
        COMPLETED = "completed", "Concluído"
        CANCELED = "canceled", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="workout_sessions")
    routine = models.ForeignKey(WorkoutRoutine, on_delete=models.PROTECT, related_name="sessions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]


class WorkoutSetLog(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name="set_logs")
    workout_exercise = models.ForeignKey(WorkoutExercise, on_delete=models.PROTECT, related_name="set_logs")
    set_number = models.PositiveSmallIntegerField()
    reps_done = models.CharField("Repetições realizadas", max_length=40, blank=True)
    load_kg = models.DecimalField("Carga utilizada", max_digits=7, decimal_places=2, null=True, blank=True)
    rpe_actual = models.PositiveSmallIntegerField(
        "RPE realizado", null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    rir_actual = models.PositiveSmallIntegerField(
        "RIR realizado", null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["workout_exercise__order", "set_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "workout_exercise", "set_number"],
                name="unique_workout_set_log",
            )
        ]


class WorkoutTemplate(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_plan = models.ForeignKey(
        WorkoutPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="saved_templates"
    )
    name = models.CharField("Nome do modelo", max_length=160)
    objective = models.CharField("Objetivo", max_length=160, blank=True)
    notes = models.TextField("Observações", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class WorkoutTemplateRoutine(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(WorkoutTemplate, on_delete=models.CASCADE, related_name="routines")
    name = models.CharField(max_length=80)
    order = models.PositiveSmallIntegerField(default=1)
    instructions = models.TextField(blank=True)

    class Meta:
        ordering = ["order", "name"]


class WorkoutTemplateExercise(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    routine = models.ForeignKey(WorkoutTemplateRoutine, on_delete=models.CASCADE, related_name="items")
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name="template_items")
    order = models.PositiveSmallIntegerField(default=1)
    sets = models.PositiveSmallIntegerField(default=3)
    reps = models.CharField(max_length=40, default="10-12")
    load_kg = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    rest_seconds = models.PositiveIntegerField(default=60)
    cadence = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)
    method = models.CharField(max_length=20, choices=WorkoutExercise.Method.choices, default=WorkoutExercise.Method.NORMAL)
    group_code = models.CharField(max_length=20, blank=True)
    target_seconds = models.PositiveIntegerField(null=True, blank=True)
    rpe_target = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    rir_target = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    progression_enabled = models.BooleanField(default=True)
    progression_increment_kg = models.DecimalField(max_digits=5, decimal_places=2, default=2.50)

    class Meta:
        ordering = ["order"]


class WorkoutSchedule(TenantModel):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Segunda"
        TUESDAY = 1, "Terça"
        WEDNESDAY = 2, "Quarta"
        THURSDAY = 3, "Quinta"
        FRIDAY = 4, "Sexta"
        SATURDAY = 5, "Sábado"
        SUNDAY = 6, "Domingo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    routine = models.ForeignKey(WorkoutRoutine, on_delete=models.CASCADE, related_name="schedules")
    weekday = models.PositiveSmallIntegerField("Dia da semana", choices=Weekday.choices)
    time = models.TimeField("Horário", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["weekday", "time"]
        constraints = [
            models.UniqueConstraint(
                fields=["routine", "weekday"],
                name="unique_routine_weekday",
            )
        ]
