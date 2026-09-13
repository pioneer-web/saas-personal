#!/usr/bin/env bash
set -euo pipefail

cd "${1:-$HOME/SaaS/saas-personal}"

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP=".backup_3b4_3b7_${STAMP}"
mkdir -p "$BACKUP"

echo "==> Backup em $BACKUP"
for f in \
  apps/workouts/models.py \
  apps/workouts/forms.py \
  apps/workouts/views.py \
  apps/workouts/urls.py \
  apps/workouts/admin.py \
  apps/workouts/templates/workouts/list.html \
  apps/workouts/templates/workouts/plan_edit.html \
  apps/workouts/templates/workouts/builder.html \
  apps/workouts/templates/workouts/student_workout.html
do
  if [ -f "$f" ]; then
    mkdir -p "$BACKUP/$(dirname "$f")"
    cp "$f" "$BACKUP/$f"
  fi
done

OTHER_0003="$(find apps/workouts/migrations -maxdepth 1 -type f -name '0003_*.py' ! -name '0003_advanced_templates_schedule.py' -print -quit || true)"
if [ -n "$OTHER_0003" ]; then
  echo "ERRO: já existe outra migração 0003: $OTHER_0003"
  echo "Pare aqui e me envie esse nome para eu ajustar a dependência."
  exit 1
fi

echo "==> Gravando models.py"
cat > apps/workouts/models.py <<'PY'
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
PY

echo "==> Gravando forms.py"
cat > apps/workouts/forms.py <<'PY'
from django import forms
from django.db.models import Q

from apps.exercises.models import Exercise
from apps.students.models import Student

from .models import WorkoutExercise, WorkoutPlan, WorkoutRoutine, WorkoutSchedule


class ExerciseChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        parts = [obj.display_name]
        if obj.display_primary_muscle:
            parts.append(obj.display_primary_muscle)
        if obj.display_equipment:
            parts.append(obj.display_equipment)
        return " — ".join(parts)


class WorkoutPlanForm(forms.ModelForm):
    class Meta:
        model = WorkoutPlan
        fields = ["student", "name", "objective", "status", "start_date", "end_date", "notes"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = (
            Student.objects.filter(organization=organization).order_by("name")
            if organization else Student.objects.none()
        )


class WorkoutRoutineForm(forms.ModelForm):
    class Meta:
        model = WorkoutRoutine
        fields = ["name", "instructions"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Ex.: Treino A - Peito e Tríceps"}),
            "instructions": forms.Textarea(attrs={"rows": 2}),
        }


class WorkoutExerciseForm(forms.ModelForm):
    exercise = ExerciseChoiceField(queryset=Exercise.objects.none(), label="Exercício")

    class Meta:
        model = WorkoutExercise
        fields = [
            "exercise", "method", "group_code", "sets", "reps", "load_kg",
            "target_seconds", "rest_seconds", "cadence", "rpe_target", "rir_target",
            "progression_enabled", "progression_increment_kg", "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
            "reps": forms.TextInput(attrs={"placeholder": "Ex.: 10-12"}),
            "cadence": forms.TextInput(attrs={"placeholder": "Ex.: 3-1-2"}),
            "group_code": forms.TextInput(attrs={"placeholder": "Ex.: A1"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["exercise"].queryset = Exercise.objects.filter(
                Q(organization__isnull=True) | Q(organization=organization)
            ).order_by("name_ptbr", "name")


class WorkoutScheduleForm(forms.ModelForm):
    class Meta:
        model = WorkoutSchedule
        fields = ["routine", "weekday", "time"]
        widgets = {"time": forms.TimeInput(attrs={"type": "time"})}

    def __init__(self, *args, organization=None, plan=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["routine"].queryset = (
            WorkoutRoutine.objects.filter(organization=organization, plan=plan).order_by("order")
            if organization and plan else WorkoutRoutine.objects.none()
        )


class TemplateApplyForm(forms.Form):
    students = forms.ModelMultipleChoiceField(
        label="Alunos",
        queryset=Student.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    plan_name = forms.CharField(label="Nome do plano", max_length=160, required=False)
    start_date = forms.DateField(
        label="Data de início",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, organization=None, template=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["students"].queryset = (
            Student.objects.filter(organization=organization).order_by("name")
            if organization else Student.objects.none()
        )
        if template and not self.is_bound:
            self.fields["plan_name"].initial = template.name
PY

echo "==> Gravando views.py"
cat > apps/workouts/views.py <<'PY'
import re
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Max
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.exercises.models import Exercise
from apps.students.models import Student

from .forms import (
    TemplateApplyForm,
    WorkoutExerciseForm,
    WorkoutPlanForm,
    WorkoutRoutineForm,
    WorkoutScheduleForm,
)
from .models import (
    WorkoutExercise,
    WorkoutPlan,
    WorkoutRoutine,
    WorkoutSchedule,
    WorkoutSession,
    WorkoutSetLog,
    WorkoutTemplate,
    WorkoutTemplateExercise,
    WorkoutTemplateRoutine,
)


def organization_or_403(request):
    if not request.organization:
        raise PermissionDenied("Usuário sem organização ativa.")
    return request.organization


def _upper_rep_target(reps):
    numbers = [int(n) for n in re.findall(r"\d+", reps or "")]
    return max(numbers) if numbers else None


def _safe_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def _safe_int(value, minimum, maximum):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if minimum <= number <= maximum else None


def progression_for_item(item, student, organization):
    if not item.progression_enabled:
        return None

    latest_log = (
        WorkoutSetLog.objects.filter(
            organization=organization,
            session__student=student,
            session__status=WorkoutSession.Status.COMPLETED,
            workout_exercise__exercise=item.exercise,
        )
        .select_related("session")
        .order_by("-session__completed_at", "set_number")
        .first()
    )

    if not latest_log or latest_log.load_kg is None:
        return None

    logs = list(
        WorkoutSetLog.objects.filter(
            organization=organization,
            session_id=latest_log.session_id,
            workout_exercise__exercise=item.exercise,
        ).order_by("set_number")
    )

    last_load = max((log.load_kg for log in logs if log.load_kg is not None), default=None)
    if last_load is None:
        return None

    target = _upper_rep_target(item.reps)
    reps_values = []
    for log in logs:
        nums = re.findall(r"\d+", log.reps_done or "")
        if nums:
            reps_values.append(int(nums[0]))

    reached = bool(
        target
        and len(logs) >= item.sets
        and len(reps_values) >= item.sets
        and all(value >= target for value in reps_values[: item.sets])
    )

    suggested = last_load + item.progression_increment_kg if reached else last_load

    return {
        "last_load": last_load,
        "suggested_load": suggested,
        "reached_target": reached,
        "increment": item.progression_increment_kg,
    }


@login_required
def plan_list(request):
    organization = organization_or_403(request)
    plans = (
        WorkoutPlan.objects.filter(organization=organization)
        .select_related("student")
        .prefetch_related("routines")
    )

    if request.method == "POST":
        plan = get_object_or_404(
            WorkoutPlan,
            pk=request.POST.get("plan_id"),
            organization=organization,
        )
        request.session["editing_workout_plan_id"] = str(plan.pk)
        return redirect("workouts:edit")

    return render(request, "workouts/list.html", {"plans": plans})


@login_required
def plan_create(request):
    organization = organization_or_403(request)

    if request.method == "POST":
        form = WorkoutPlanForm(request.POST, organization=organization)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.organization = organization
            plan.save()
            request.session["editing_workout_plan_id"] = str(plan.pk)
            return redirect("workouts:edit")
    else:
        form = WorkoutPlanForm(organization=organization)

    return render(
        request,
        "workouts/plan_form.html",
        {"form": form, "title": "Novo plano de treino"},
    )


@login_required
def plan_edit(request):
    organization = organization_or_403(request)
    plan_id = request.session.get("editing_workout_plan_id")

    if not plan_id:
        return redirect("workouts:list")

    plan = get_object_or_404(
        WorkoutPlan,
        pk=plan_id,
        organization=organization,
    )

    if request.method == "POST":
        form = WorkoutPlanForm(
            request.POST,
            instance=plan,
            organization=organization,
        )
        if form.is_valid():
            form.save()
            return redirect("workouts:edit")
    else:
        form = WorkoutPlanForm(
            instance=plan,
            organization=organization,
        )

    return render(
        request,
        "workouts/plan_edit.html",
        {
            "plan": plan,
            "form": form,
            "routines": plan.routines.filter(organization=organization),
            "routine_form": WorkoutRoutineForm(),
        },
    )


@login_required
def routine_add(request):
    organization = organization_or_403(request)
    plan_id = request.session.get("editing_workout_plan_id")

    if not plan_id:
        return redirect("workouts:list")

    plan = get_object_or_404(
        WorkoutPlan,
        pk=plan_id,
        organization=organization,
    )

    if request.method == "POST":
        form = WorkoutRoutineForm(request.POST)
        if form.is_valid():
            routine = form.save(commit=False)
            last_order = plan.routines.aggregate(max_order=Max("order"))["max_order"] or 0
            routine.organization = organization
            routine.plan = plan
            routine.order = last_order + 1
            routine.save()

    return redirect("workouts:edit")


@login_required
def routine_builder(request):
    organization = organization_or_403(request)

    if request.method == "POST" and request.POST.get("select_routine_id"):
        routine = get_object_or_404(
            WorkoutRoutine,
            pk=request.POST["select_routine_id"],
            organization=organization,
        )
        request.session["editing_workout_routine_id"] = str(routine.pk)
        request.session.pop("editing_workout_item_id", None)
        return redirect("workouts:builder")

    routine_id = request.session.get("editing_workout_routine_id")
    if not routine_id:
        return redirect("workouts:list")

    routine = get_object_or_404(
        WorkoutRoutine,
        pk=routine_id,
        organization=organization,
    )

    editing_item = None
    editing_id = request.session.get("editing_workout_item_id")

    if editing_id:
        editing_item = WorkoutExercise.objects.filter(
            pk=editing_id,
            routine=routine,
            organization=organization,
        ).first()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            form = WorkoutExerciseForm(
                request.POST,
                organization=organization,
            )
            if form.is_valid():
                item = form.save(commit=False)
                last_order = routine.items.aggregate(max_order=Max("order"))["max_order"] or 0
                item.organization = organization
                item.routine = routine
                item.order = last_order + 1
                item.save()
                return redirect("workouts:builder")

        elif action == "start_edit":
            item = get_object_or_404(
                WorkoutExercise,
                pk=request.POST.get("item_id"),
                routine=routine,
                organization=organization,
            )
            request.session["editing_workout_item_id"] = str(item.pk)
            return redirect("workouts:builder")

        elif action == "save_edit" and editing_item:
            form = WorkoutExerciseForm(
                request.POST,
                instance=editing_item,
                organization=organization,
            )
            if form.is_valid():
                form.save()
                request.session.pop("editing_workout_item_id", None)
                return redirect("workouts:builder")

        elif action == "cancel_edit":
            request.session.pop("editing_workout_item_id", None)
            return redirect("workouts:builder")

        elif action == "remove":
            item = get_object_or_404(
                WorkoutExercise,
                pk=request.POST.get("item_id"),
                routine=routine,
                organization=organization,
            )
            item.delete()
            return redirect("workouts:builder")

    if request.method != "POST" or request.POST.get("action") not in {"add", "save_edit"}:
        form = WorkoutExerciseForm(
            instance=editing_item,
            organization=organization,
        )

    return render(
        request,
        "workouts/builder.html",
        {
            "routine": routine,
            "items": routine.items.filter(
                organization=organization
            ).select_related("exercise"),
            "form": form,
            "editing_item": editing_item,
        },
    )


@login_required
def student_workout_preview(request):
    organization = organization_or_403(request)

    if request.method == "POST" and request.POST.get("select_student_routine_id"):
        routine = get_object_or_404(
            WorkoutRoutine,
            pk=request.POST["select_student_routine_id"],
            organization=organization,
        )
        request.session["student_preview_routine_id"] = str(routine.pk)
        request.session.pop("active_workout_session_id", None)
        return redirect("workouts:student_workout")

    routine_id = request.session.get("student_preview_routine_id")
    if not routine_id:
        return redirect("workouts:list")

    routine = get_object_or_404(
        WorkoutRoutine.objects.select_related("plan", "plan__student"),
        pk=routine_id,
        organization=organization,
    )

    items = routine.items.filter(
        organization=organization
    ).select_related("exercise")

    session = None
    session_id = request.session.get("active_workout_session_id")

    if session_id:
        session = WorkoutSession.objects.filter(
            pk=session_id,
            organization=organization,
            routine=routine,
            status=WorkoutSession.Status.IN_PROGRESS,
        ).first()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "start":
            if not session:
                session = WorkoutSession.objects.create(
                    organization=organization,
                    student=routine.plan.student,
                    routine=routine,
                )
                request.session["active_workout_session_id"] = str(session.pk)
            return redirect("workouts:student_workout")

        if action == "complete_set" and session:
            item = get_object_or_404(
                WorkoutExercise,
                pk=request.POST.get("item_id"),
                routine=routine,
                organization=organization,
            )

            try:
                set_number = int(request.POST.get("set_number", "0"))
            except ValueError:
                set_number = 0

            if set_number < 1 or set_number > item.sets:
                raise PermissionDenied("Série inválida.")

            WorkoutSetLog.objects.update_or_create(
                organization=organization,
                session=session,
                workout_exercise=item,
                set_number=set_number,
                defaults={
                    "reps_done": request.POST.get("reps_done", "").strip(),
                    "load_kg": _safe_decimal(request.POST.get("load_kg")),
                    "rpe_actual": _safe_int(request.POST.get("rpe_actual"), 1, 10),
                    "rir_actual": _safe_int(request.POST.get("rir_actual"), 0, 10),
                },
            )

            return redirect("workouts:student_workout")

        if action == "finish" and session:
            session.status = WorkoutSession.Status.COMPLETED
            session.completed_at = timezone.now()
            session.save(update_fields=["status", "completed_at"])
            request.session.pop("active_workout_session_id", None)
            return redirect("workouts:student_workout")

    completed = {}

    if session:
        for log in session.set_logs.all():
            completed[(str(log.workout_exercise_id), log.set_number)] = log

    workout_data = []

    for item in items:
        sets = [
            {
                "number": number,
                "log": completed.get((str(item.pk), number)),
            }
            for number in range(1, item.sets + 1)
        ]

        workout_data.append(
            {
                "item": item,
                "sets": sets,
                "progression": progression_for_item(
                    item,
                    routine.plan.student,
                    organization,
                ),
            }
        )

    return render(
        request,
        "workouts/student_workout.html",
        {
            "routine": routine,
            "session": session,
            "workout_data": workout_data,
        },
    )


@login_required
def workout_history(request):
    organization = organization_or_403(request)
    student_id = request.session.get("workout_history_student_id")

    if request.method == "POST" and request.POST.get("student_id"):
        student = get_object_or_404(
            Student,
            pk=request.POST["student_id"],
            organization=organization,
        )
        request.session["workout_history_student_id"] = str(student.pk)
        return redirect("workouts:history")

    students = Student.objects.filter(
        organization=organization
    ).order_by("name")

    student = (
        Student.objects.filter(
            pk=student_id,
            organization=organization,
        ).first()
        if student_id
        else None
    )

    sessions = []

    if student:
        sessions = (
            WorkoutSession.objects.filter(
                organization=organization,
                student=student,
                status=WorkoutSession.Status.COMPLETED,
            )
            .select_related("routine", "routine__plan")
            .annotate(completed_sets=Count("set_logs"))
            .order_by("-completed_at")
        )

    return render(
        request,
        "workouts/history.html",
        {
            "students": students,
            "student": student,
            "sessions": sessions,
        },
    )


@login_required
def exercise_progress(request):
    organization = organization_or_403(request)
    student_id = request.session.get("progress_student_id")
    exercise_id = request.session.get("progress_exercise_id")

    if request.method == "POST":
        if request.POST.get("student_id"):
            student = get_object_or_404(
                Student,
                pk=request.POST["student_id"],
                organization=organization,
            )
            request.session["progress_student_id"] = str(student.pk)
            request.session.pop("progress_exercise_id", None)
            return redirect("workouts:progress")

        if request.POST.get("exercise_id"):
            exercise = get_object_or_404(
                Exercise,
                pk=request.POST["exercise_id"],
            )
            request.session["progress_exercise_id"] = str(exercise.pk)
            return redirect("workouts:progress")

    students = Student.objects.filter(
        organization=organization
    ).order_by("name")

    student = (
        Student.objects.filter(
            pk=student_id,
            organization=organization,
        ).first()
        if student_id
        else None
    )

    exercise = None
    exercises = []
    progression = []

    if student:
        exercise_ids = (
            WorkoutSetLog.objects.filter(
                organization=organization,
                session__student=student,
            )
            .values_list(
                "workout_exercise__exercise_id",
                flat=True,
            )
            .distinct()
        )

        exercises = Exercise.objects.filter(
            pk__in=exercise_ids
        ).order_by("name_ptbr", "name")

    if student and exercise_id:
        exercise = Exercise.objects.filter(pk=exercise_id).first()

        if exercise:
            logs = WorkoutSetLog.objects.filter(
                organization=organization,
                session__student=student,
                workout_exercise__exercise=exercise,
                session__status=WorkoutSession.Status.COMPLETED,
            ).order_by("completed_at")

            progression = [
                {
                    "date": log.completed_at,
                    "load": log.load_kg,
                    "reps": log.reps_done,
                    "set_number": log.set_number,
                }
                for log in logs
            ]

    return render(
        request,
        "workouts/progress.html",
        {
            "students": students,
            "student": student,
            "exercises": exercises,
            "exercise": exercise,
            "progression": progression,
        },
    )


@login_required
@transaction.atomic
def save_plan_as_template(request):
    organization = organization_or_403(request)

    if request.method != "POST":
        return redirect("workouts:edit")

    plan_id = request.session.get("editing_workout_plan_id")
    if not plan_id:
        return redirect("workouts:list")

    plan = get_object_or_404(
        WorkoutPlan,
        pk=plan_id,
        organization=organization,
    )

    template = WorkoutTemplate.objects.create(
        organization=organization,
        source_plan=plan,
        name=f"{plan.name} - Modelo",
        objective=plan.objective,
        notes=plan.notes,
    )

    for routine in plan.routines.filter(organization=organization):
        template_routine = WorkoutTemplateRoutine.objects.create(
            organization=organization,
            template=template,
            name=routine.name,
            order=routine.order,
            instructions=routine.instructions,
        )

        for item in routine.items.filter(organization=organization):
            WorkoutTemplateExercise.objects.create(
                organization=organization,
                routine=template_routine,
                exercise=item.exercise,
                order=item.order,
                sets=item.sets,
                reps=item.reps,
                load_kg=item.load_kg,
                rest_seconds=item.rest_seconds,
                cadence=item.cadence,
                notes=item.notes,
                method=item.method,
                group_code=item.group_code,
                target_seconds=item.target_seconds,
                rpe_target=item.rpe_target,
                rir_target=item.rir_target,
                progression_enabled=item.progression_enabled,
                progression_increment_kg=item.progression_increment_kg,
            )

    request.session["selected_workout_template_id"] = str(template.pk)
    return redirect("workouts:templates")


@login_required
def template_list(request):
    organization = organization_or_403(request)

    templates = WorkoutTemplate.objects.filter(
        organization=organization,
        is_active=True,
    ).prefetch_related("routines__items")

    if request.method == "POST" and request.POST.get("template_id"):
        template = get_object_or_404(
            WorkoutTemplate,
            pk=request.POST["template_id"],
            organization=organization,
        )

        request.session["selected_workout_template_id"] = str(template.pk)
        return redirect("workouts:template_apply")

    return render(
        request,
        "workouts/templates.html",
        {"templates": templates},
    )


@login_required
@transaction.atomic
def template_apply(request):
    organization = organization_or_403(request)
    template_id = request.session.get("selected_workout_template_id")

    if not template_id:
        return redirect("workouts:templates")

    template = get_object_or_404(
        WorkoutTemplate,
        pk=template_id,
        organization=organization,
    )

    if request.method == "POST":
        form = TemplateApplyForm(
            request.POST,
            organization=organization,
            template=template,
        )

        if form.is_valid():
            created = []

            for student in form.cleaned_data["students"]:
                plan = WorkoutPlan.objects.create(
                    organization=organization,
                    student=student,
                    name=form.cleaned_data.get("plan_name") or template.name,
                    objective=template.objective,
                    notes=template.notes,
                    start_date=form.cleaned_data.get("start_date"),
                    status=WorkoutPlan.Status.ACTIVE,
                )

                for template_routine in template.routines.filter(
                    organization=organization
                ):
                    routine = WorkoutRoutine.objects.create(
                        organization=organization,
                        plan=plan,
                        name=template_routine.name,
                        order=template_routine.order,
                        instructions=template_routine.instructions,
                    )

                    for template_item in template_routine.items.filter(
                        organization=organization
                    ):
                        WorkoutExercise.objects.create(
                            organization=organization,
                            routine=routine,
                            exercise=template_item.exercise,
                            order=template_item.order,
                            sets=template_item.sets,
                            reps=template_item.reps,
                            load_kg=template_item.load_kg,
                            rest_seconds=template_item.rest_seconds,
                            cadence=template_item.cadence,
                            notes=template_item.notes,
                            method=template_item.method,
                            group_code=template_item.group_code,
                            target_seconds=template_item.target_seconds,
                            rpe_target=template_item.rpe_target,
                            rir_target=template_item.rir_target,
                            progression_enabled=template_item.progression_enabled,
                            progression_increment_kg=template_item.progression_increment_kg,
                        )

                created.append(plan)

            if created:
                request.session["editing_workout_plan_id"] = str(created[0].pk)

            return redirect("workouts:list")
    else:
        form = TemplateApplyForm(
            organization=organization,
            template=template,
        )

    return render(
        request,
        "workouts/template_apply.html",
        {
            "template": template,
            "form": form,
        },
    )


@login_required
def schedule_manage(request):
    organization = organization_or_403(request)
    plan_id = request.session.get("editing_workout_plan_id")

    if not plan_id:
        return redirect("workouts:list")

    plan = get_object_or_404(
        WorkoutPlan,
        pk=plan_id,
        organization=organization,
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save":
            form = WorkoutScheduleForm(
                request.POST,
                organization=organization,
                plan=plan,
            )

            if form.is_valid():
                WorkoutSchedule.objects.update_or_create(
                    organization=organization,
                    routine=form.cleaned_data["routine"],
                    weekday=form.cleaned_data["weekday"],
                    defaults={
                        "time": form.cleaned_data["time"],
                        "is_active": True,
                    },
                )
                return redirect("workouts:schedule")

        elif action == "delete":
            schedule = get_object_or_404(
                WorkoutSchedule,
                pk=request.POST.get("schedule_id"),
                organization=organization,
                routine__plan=plan,
            )
            schedule.delete()
            return redirect("workouts:schedule")

        elif action == "toggle":
            schedule = get_object_or_404(
                WorkoutSchedule,
                pk=request.POST.get("schedule_id"),
                organization=organization,
                routine__plan=plan,
            )
            schedule.is_active = not schedule.is_active
            schedule.save(update_fields=["is_active"])
            return redirect("workouts:schedule")
    else:
        form = WorkoutScheduleForm(
            organization=organization,
            plan=plan,
        )

    schedules = WorkoutSchedule.objects.filter(
        organization=organization,
        routine__plan=plan,
    ).select_related("routine")

    return render(
        request,
        "workouts/schedule.html",
        {
            "plan": plan,
            "form": form,
            "schedules": schedules,
        },
    )


@login_required
def weekly_agenda(request):
    organization = organization_or_403(request)
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())

    schedules = list(
        WorkoutSchedule.objects.filter(
            organization=organization,
            is_active=True,
        )
        .select_related(
            "routine",
            "routine__plan",
            "routine__plan__student",
        )
        .order_by("weekday", "time")
    )

    planned = 0
    completed = 0
    days = []

    for weekday, label in WorkoutSchedule.Weekday.choices:
        day_date = week_start + timedelta(days=weekday)
        entries = []

        for schedule in [
            item for item in schedules
            if item.weekday == weekday
        ]:
            status = "programado"

            if day_date <= today:
                planned += 1

                done = WorkoutSession.objects.filter(
                    organization=organization,
                    routine=schedule.routine,
                    student=schedule.routine.plan.student,
                    status=WorkoutSession.Status.COMPLETED,
                    completed_at__date=day_date,
                ).exists()

                if done:
                    completed += 1
                    status = "concluido"
                elif day_date < today:
                    status = "nao_realizado"
                else:
                    status = "pendente"

            entries.append(
                {
                    "schedule": schedule,
                    "status": status,
                }
            )

        days.append(
            {
                "weekday": weekday,
                "label": label,
                "date": day_date,
                "entries": entries,
                "is_today": day_date == today,
            }
        )

    adherence = round((completed / planned) * 100) if planned else 0

    return render(
        request,
        "workouts/agenda.html",
        {
            "days": days,
            "planned": planned,
            "completed": completed,
            "adherence": adherence,
            "today": today,
        },
    )
PY

echo "==> Gravando urls.py"
cat > apps/workouts/urls.py <<'PY'
from django.urls import path

from . import views

app_name = "workouts"

urlpatterns = [
    path("", views.plan_list, name="list"),
    path("novo/", views.plan_create, name="create"),
    path("editar/", views.plan_edit, name="edit"),
    path("adicionar-treino/", views.routine_add, name="routine_add"),
    path("montar/", views.routine_builder, name="builder"),
    path("modo-aluno/", views.student_workout_preview, name="student_workout"),
    path("historico/", views.workout_history, name="history"),
    path("evolucao/", views.exercise_progress, name="progress"),
    path("modelos/", views.template_list, name="templates"),
    path("modelos/aplicar/", views.template_apply, name="template_apply"),
    path("salvar-modelo/", views.save_plan_as_template, name="save_template"),
    path("agenda/", views.schedule_manage, name="schedule"),
    path("agenda-semanal/", views.weekly_agenda, name="weekly_agenda"),
]
PY

echo "==> Gravando admin.py"
cat > apps/workouts/admin.py <<'PY'
from django.contrib import admin

from .models import (
    WorkoutExercise,
    WorkoutPlan,
    WorkoutRoutine,
    WorkoutSchedule,
    WorkoutSession,
    WorkoutSetLog,
    WorkoutTemplate,
    WorkoutTemplateExercise,
    WorkoutTemplateRoutine,
)

admin.site.register(WorkoutPlan)
admin.site.register(WorkoutRoutine)
admin.site.register(WorkoutExercise)
admin.site.register(WorkoutSession)
admin.site.register(WorkoutSetLog)
admin.site.register(WorkoutTemplate)
admin.site.register(WorkoutTemplateRoutine)
admin.site.register(WorkoutTemplateExercise)
admin.site.register(WorkoutSchedule)
PY

echo "==> Gravando migração 0003"
cat > apps/workouts/migrations/0003_advanced_templates_schedule.py <<'PY'
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
PY

mkdir -p apps/workouts/templates/workouts

echo "==> Gravando list.html"
cat > apps/workouts/templates/workouts/list.html <<'HTML'
{% extends "base.html" %}
{% block title %}Treinos | Personal{% endblock %}
{% block content %}
<div class="space-y-6">

<div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
    <div>
        <span class="text-xs font-bold uppercase tracking-[.25em] text-[#ed5d26]">Prescrição</span>
        <h1 class="mt-2 text-3xl font-black">Planos de treino</h1>
        <p class="mt-1 text-sm text-[#b8b3af]">Treinos, modelos e agenda dos alunos.</p>
    </div>

    <div class="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <a href="{% url 'workouts:templates' %}" class="rounded-2xl bg-white/5 px-5 py-3 text-center font-bold">Modelos</a>
        <a href="{% url 'workouts:weekly_agenda' %}" class="rounded-2xl bg-white/5 px-5 py-3 text-center font-bold">Agenda semanal</a>
        <a href="{% url 'workouts:create' %}" class="rounded-2xl bg-gradient-to-r from-[#ce3221] to-[#ed5d26] px-5 py-3 text-center font-bold">+ Novo plano</a>
    </div>
</div>

<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
{% for plan in plans %}
<div class="rounded-[26px] border border-white/10 bg-[#1a1715] p-5">
    <div class="flex items-start justify-between gap-4">
        <div>
            <h2 class="text-xl font-black">{{ plan.name }}</h2>
            <p class="mt-1 text-[#b8b3af]">{{ plan.student.name }}</p>
        </div>
        <span class="rounded-full bg-[#ed5d26]/15 px-3 py-1 text-xs font-bold text-[#ed8e5f]">{{ plan.get_status_display }}</span>
    </div>

    {% if plan.objective %}
    <p class="mt-4 text-sm text-[#b8b3af]">{{ plan.objective }}</p>
    {% endif %}

    <div class="mt-5 text-sm text-[#716b67]">{{ plan.routines.count }} treino(s)</div>

    <form method="post" class="mt-4">
        {% csrf_token %}
        <input type="hidden" name="plan_id" value="{{ plan.id }}">
        <button class="w-full rounded-2xl bg-white/5 px-4 py-3 font-bold">Abrir plano</button>
    </form>
</div>
{% empty %}
<div class="col-span-full rounded-3xl border border-dashed border-white/10 p-12 text-center text-[#b8b3af]">
    Nenhum plano de treino criado.
</div>
{% endfor %}
</div>

</div>
{% endblock %}
HTML

echo "==> Gravando plan_edit.html"
cat > apps/workouts/templates/workouts/plan_edit.html <<'HTML'
{% extends "base.html" %}
{% block content %}
<div class="space-y-7">

<div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
    <div>
        <span class="text-xs font-bold uppercase tracking-[.25em] text-[#ed5d26]">Plano de treino</span>
        <h1 class="mt-2 text-3xl font-black">{{ plan.student.name }}</h1>
        <p class="text-[#b8b3af]">{{ plan.name }}</p>
    </div>

    <div class="grid gap-2 sm:grid-cols-2">
        <form method="post" action="{% url 'workouts:save_template' %}">
            {% csrf_token %}
            <button class="w-full rounded-2xl bg-white/5 px-5 py-3 font-bold">Salvar como modelo</button>
        </form>

        <a href="{% url 'workouts:schedule' %}" class="rounded-2xl bg-[#ed5d26]/15 px-5 py-3 text-center font-bold text-[#ed8e5f]">
            Programar agenda
        </a>
    </div>
</div>

<div class="grid gap-6 xl:grid-cols-[1fr_1.2fr]">

<form method="post" class="space-y-4 rounded-[28px] border border-white/10 bg-[#1a1715] p-5">
    {% csrf_token %}
    <h2 class="text-xl font-black">Dados do plano</h2>

    {% for field in form %}
    <div>
        <label class="mb-1 block text-sm font-bold">{{ field.label }}</label>
        {{ field }}
        {% for error in field.errors %}
        <div class="mt-1 text-sm text-red-400">{{ error }}</div>
        {% endfor %}
    </div>
    {% endfor %}

    <button class="w-full rounded-2xl bg-[#ed5d26] px-5 py-3 font-bold">Salvar alterações</button>
</form>

<div class="space-y-4">
    <div class="rounded-[28px] border border-white/10 bg-[#1a1715] p-5">
        <h2 class="mb-4 text-xl font-black">Adicionar treino</h2>

        <form method="post" action="{% url 'workouts:routine_add' %}" class="space-y-3">
            {% csrf_token %}
            {{ routine_form.name }}
            {{ routine_form.instructions }}
            <button class="w-full rounded-2xl bg-white/10 px-5 py-3 font-bold">+ Adicionar Treino A/B/C</button>
        </form>
    </div>

    {% for routine in routines %}
    <div class="rounded-[24px] border border-white/10 bg-[#1a1715] p-5">
        <div class="flex items-center justify-between">
            <div>
                <div class="text-lg font-black">{{ routine.name }}</div>
                <div class="mt-1 text-sm text-[#b8b3af]">{{ routine.items.count }} exercício(s)</div>
            </div>
            <span class="text-[#ed5d26]">{{ routine.order }}</span>
        </div>

        <form method="post" action="{% url 'workouts:builder' %}" class="mt-4">
            {% csrf_token %}
            <input type="hidden" name="select_routine_id" value="{{ routine.id }}">
            <button class="w-full rounded-2xl bg-gradient-to-r from-[#ce3221] to-[#ed5d26] px-4 py-3 font-bold">
                Montar exercícios
            </button>
        </form>
    </div>
    {% endfor %}
</div>

</div>
</div>

<style>
input, select, textarea {
    width:100%; min-height:48px; border:1px solid rgba(255,255,255,.1);
    border-radius:14px; padding:12px 15px; background:#0c0c09; color:white;
}
</style>
{% endblock %}
HTML

echo "==> Gravando builder.html"
cat > apps/workouts/templates/workouts/builder.html <<'HTML'
{% extends "base.html" %}
{% block content %}

<div class="space-y-6">

<div>
    <a href="{% url 'workouts:edit' %}" class="text-sm text-[#ed8e5f]">← Voltar ao plano</a>
    <h1 class="mt-3 text-3xl font-black">{{ routine.name }}</h1>
    <p class="text-[#b8b3af]">{{ routine.plan.student.name }}</p>

    <form method="post" action="{% url 'workouts:student_workout' %}" class="mt-4">
        {% csrf_token %}
        <input type="hidden" name="select_student_routine_id" value="{{ routine.id }}">
        <button class="rounded-2xl border border-[#ed5d26]/40 bg-[#ed5d26]/10 px-5 py-3 font-bold text-[#ed8e5f]">
            📱 Visualizar como aluno
        </button>
    </form>
</div>

<div class="grid gap-6 xl:grid-cols-[.9fr_1.1fr]">

<form method="post" class="space-y-4 rounded-[28px] border border-white/10 bg-[#1a1715] p-5">
    {% csrf_token %}
    <input type="hidden" name="action" value="{% if editing_item %}save_edit{% else %}add{% endif %}">

    <h2 class="text-xl font-black">
        {% if editing_item %}Editar prescrição{% else %}Adicionar exercício{% endif %}
    </h2>

    {% for field in form %}
    <div>
        <label class="mb-1 block text-sm font-bold">{{ field.label }}</label>

        {% if field.name == "exercise" %}
        <input type="search" id="exercise-search" placeholder="Buscar por exercício, músculo ou equipamento..." autocomplete="off" class="mb-2">
        {{ field }}
        {% else %}
        {{ field }}
        {% endif %}

        {% for error in field.errors %}
        <div class="mt-1 text-sm text-red-400">{{ error }}</div>
        {% endfor %}
    </div>
    {% endfor %}

    <button class="w-full rounded-2xl bg-gradient-to-r from-[#ce3221] to-[#ed5d26] px-5 py-3 font-bold">
        {% if editing_item %}Salvar alterações{% else %}+ Adicionar ao treino{% endif %}
    </button>

    {% if editing_item %}
    <button type="submit" name="action" value="cancel_edit" class="w-full rounded-2xl bg-white/5 px-5 py-3 font-bold">
        Cancelar edição
    </button>
    {% endif %}

    <div class="rounded-2xl bg-white/5 p-4 text-xs leading-5 text-[#b8b3af]">
        Para supersérie, bi-set, tri-set ou circuito, use o mesmo <strong>Grupo/Bloco</strong> nos exercícios relacionados, por exemplo A1.
        RPE/RIR são metas opcionais. A progressão é apenas uma sugestão ao aluno/personal.
    </div>
</form>

<div class="space-y-3">
{% for item in items %}
<div class="rounded-[24px] border border-white/10 bg-[#1a1715] p-4">

    <div class="flex gap-4">
        {% if item.exercise.display_image_url %}
        <img src="{{ item.exercise.display_image_url }}" class="h-20 w-20 rounded-2xl object-cover">
        {% endif %}

        <div class="min-w-0 flex-1">
            <div class="font-black">{{ item.order }}. {{ item.exercise.display_name }}</div>

            <div class="mt-2 flex flex-wrap gap-2 text-xs">
                <span class="rounded-full bg-[#ed5d26]/15 px-3 py-1 text-[#ed8e5f]">{{ item.get_method_display }}</span>

                {% if item.group_code %}
                <span class="rounded-full bg-white/5 px-3 py-1">Grupo {{ item.group_code }}</span>
                {% endif %}

                <span class="rounded-full bg-white/5 px-3 py-1">{{ item.sets }} séries</span>
                <span class="rounded-full bg-white/5 px-3 py-1">{{ item.reps }} reps</span>
                <span class="rounded-full bg-white/5 px-3 py-1">{{ item.rest_seconds }}s</span>

                {% if item.rpe_target %}
                <span class="rounded-full bg-white/5 px-3 py-1">RPE {{ item.rpe_target }}</span>
                {% endif %}

                {% if item.rir_target != None %}
                <span class="rounded-full bg-white/5 px-3 py-1">RIR {{ item.rir_target }}</span>
                {% endif %}
            </div>

            {% if item.load_kg %}
            <div class="mt-2 text-sm font-bold text-[#ed8e5f]">{{ item.load_kg }} kg</div>
            {% endif %}
        </div>
    </div>

    <div class="mt-4 grid grid-cols-2 gap-2">
        <form method="post">
            {% csrf_token %}
            <input type="hidden" name="action" value="start_edit">
            <input type="hidden" name="item_id" value="{{ item.id }}">
            <button class="w-full rounded-2xl bg-white/5 px-4 py-2 font-bold">Editar</button>
        </form>

        <form method="post">
            {% csrf_token %}
            <input type="hidden" name="action" value="remove">
            <input type="hidden" name="item_id" value="{{ item.id }}">
            <button class="w-full rounded-2xl bg-red-500/10 px-4 py-2 font-bold text-red-400">Remover</button>
        </form>
    </div>
</div>
{% empty %}
<div class="rounded-3xl border border-dashed border-white/10 p-10 text-center text-[#b8b3af]">
    Adicione o primeiro exercício deste treino.
</div>
{% endfor %}
</div>

</div>
</div>

<script>
document.addEventListener("DOMContentLoaded", function () {
    const search = document.getElementById("exercise-search");
    const select = document.getElementById("id_exercise");

    if (!search || !select) return;

    const options = Array.from(select.options).map(option => ({
        value: option.value,
        text: option.text,
        selected: option.selected
    }));

    function normalize(text) {
        return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    }

    search.addEventListener("input", function () {
        const term = normalize(search.value.trim());
        const current = select.value;
        select.innerHTML = "";

        options.forEach(item => {
            if (!term || normalize(item.text).includes(term)) {
                const option = document.createElement("option");
                option.value = item.value;
                option.textContent = item.text;
                if (item.value === current) option.selected = true;
                select.appendChild(option);
            }
        });

        if (!select.value && select.options.length) select.selectedIndex = 0;
    });
});
</script>

<style>
input, select, textarea {
    width:100%; min-height:48px; border:1px solid rgba(255,255,255,.1);
    border-radius:14px; padding:12px 15px; background:#0c0c09; color:white;
}
input[type="checkbox"] { width:auto; min-height:auto; }
</style>
{% endblock %}
HTML

echo "==> Gravando student_workout.html"
cat > apps/workouts/templates/workouts/student_workout.html <<'HTML'
{% extends "base.html" %}
{% block title %}{{ routine.name }} | Treino{% endblock %}
{% block content %}

<div class="mx-auto max-w-xl space-y-5">

<div class="rounded-[30px] bg-gradient-to-br from-[#9e1d1f] via-[#ce3221] to-[#ed5d26] p-6">
    <div class="text-sm text-white/70">{{ routine.plan.student.name }}</div>
    <h1 class="mt-1 text-3xl font-black">{{ routine.name }}</h1>
    <div class="mt-2 text-sm text-white/80">{{ routine.plan.name }}</div>

    {% if not session %}
    <form method="post" class="mt-5">
        {% csrf_token %}
        <input type="hidden" name="action" value="start">
        <button class="w-full rounded-2xl bg-white px-5 py-3 font-black text-[#ce3221]">▶ Iniciar treino</button>
    </form>
    {% else %}
    <div class="mt-5 rounded-2xl bg-black/20 px-4 py-3 text-sm font-bold">Treino em andamento</div>
    {% endif %}
</div>

{% for block in workout_data %}
{% with item=block.item %}
<article class="overflow-hidden rounded-[28px] border border-white/10 bg-[#1a1715]">

    {% if item.exercise.embed_video_url %}
    <div class="aspect-video bg-black">
        <iframe src="{{ item.exercise.embed_video_url }}"
                class="h-full w-full"
                frameborder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowfullscreen></iframe>
    </div>
    {% elif item.exercise.display_image_url %}
    <img src="{{ item.exercise.display_image_url }}" class="aspect-video w-full object-cover">
    {% else %}
    <div class="flex aspect-video items-center justify-center bg-[#100e0c] text-[#716b67]">Sem mídia</div>
    {% endif %}

    <div class="p-5">
        <div class="flex flex-wrap gap-2">
            <span class="rounded-full bg-[#ed5d26]/15 px-3 py-1 text-xs font-bold text-[#ed8e5f]">{{ item.get_method_display }}</span>
            {% if item.group_code %}
            <span class="rounded-full bg-white/5 px-3 py-1 text-xs">Grupo {{ item.group_code }}</span>
            {% endif %}
        </div>

        <h2 class="mt-3 text-xl font-black">{{ item.exercise.display_name }}</h2>

        <div class="mt-2 flex flex-wrap gap-2 text-xs">
            <span class="rounded-full bg-white/5 px-3 py-1">{{ item.sets }} séries</span>
            <span class="rounded-full bg-white/5 px-3 py-1">{{ item.reps }} reps</span>
            <span class="rounded-full bg-white/5 px-3 py-1">{{ item.rest_seconds }}s descanso</span>

            {% if item.target_seconds %}
            <span class="rounded-full bg-white/5 px-3 py-1">{{ item.target_seconds }}s alvo</span>
            {% endif %}

            {% if item.rpe_target %}
            <span class="rounded-full bg-white/5 px-3 py-1">RPE alvo {{ item.rpe_target }}</span>
            {% endif %}

            {% if item.rir_target != None %}
            <span class="rounded-full bg-white/5 px-3 py-1">RIR alvo {{ item.rir_target }}</span>
            {% endif %}
        </div>

        {% if block.progression %}
        <div class="mt-4 rounded-2xl border border-[#ed5d26]/20 bg-[#ed5d26]/10 p-4">
            <div class="text-xs font-bold uppercase tracking-wider text-[#ed8e5f]">Sugestão de progressão</div>
            <div class="mt-2 text-sm text-[#b8b3af]">
                Última carga: <strong class="text-white">{{ block.progression.last_load }} kg</strong>
            </div>

            {% if block.progression.reached_target %}
            <div class="mt-1 text-lg font-black text-[#ed8e5f]">
                Sugestão hoje: {{ block.progression.suggested_load }} kg
            </div>
            <div class="mt-1 text-xs text-[#716b67]">
                Meta de repetições foi atingida na última sessão. A sugestão não altera a prescrição do personal.
            </div>
            {% else %}
            <div class="mt-1 text-sm font-bold">Manter {{ block.progression.last_load }} kg</div>
            {% endif %}
        </div>
        {% endif %}

        {% if item.exercise.display_instructions %}
        <details class="mt-4 rounded-2xl bg-white/5 p-4">
            <summary class="cursor-pointer font-bold">Como executar</summary>
            <div class="mt-3 whitespace-pre-line text-sm leading-6 text-[#b8b3af]">{{ item.exercise.display_instructions }}</div>
        </details>
        {% endif %}

        {% if item.notes %}
        <div class="mt-4 rounded-2xl bg-white/5 p-4 text-sm text-[#b8b3af]">
            <strong class="text-white">Orientação do personal:</strong><br>
            {{ item.notes }}
        </div>
        {% endif %}

        {% if session %}
        <div class="mt-5 space-y-3">
            {% for set in block.sets %}
            <div class="rounded-2xl border border-white/10 bg-[#0c0c09] p-4">

                {% if set.log %}
                <div class="flex items-center justify-between">
                    <div>
                        <div class="font-bold">Série {{ set.number }}</div>
                        <div class="mt-1 text-sm text-[#b8b3af]">
                            {{ set.log.reps_done }} reps
                            {% if set.log.load_kg %} • {{ set.log.load_kg }} kg{% endif %}
                            {% if set.log.rpe_actual %} • RPE {{ set.log.rpe_actual }}{% endif %}
                            {% if set.log.rir_actual != None %} • RIR {{ set.log.rir_actual }}{% endif %}
                        </div>
                    </div>
                    <span class="text-2xl">✅</span>
                </div>

                {% else %}
                <form method="post" class="space-y-3" onsubmit="startRestTimer({{ item.rest_seconds }})">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="complete_set">
                    <input type="hidden" name="item_id" value="{{ item.id }}">
                    <input type="hidden" name="set_number" value="{{ set.number }}">

                    <div class="font-bold">Série {{ set.number }}</div>

                    <div class="grid grid-cols-2 gap-2">
                        <input name="reps_done" inputmode="numeric" placeholder="Reps" value="{{ item.reps }}">
                        <input name="load_kg"
                               inputmode="decimal"
                               placeholder="Carga kg"
                               {% if block.progression %}value="{{ block.progression.suggested_load }}"{% elif item.load_kg %}value="{{ item.load_kg }}"{% endif %}>
                    </div>

                    {% if item.rpe_target or item.rir_target != None %}
                    <div class="grid grid-cols-2 gap-2">
                        <input name="rpe_actual" inputmode="numeric" placeholder="RPE realizado">
                        <input name="rir_actual" inputmode="numeric" placeholder="RIR realizado">
                    </div>
                    {% endif %}

                    <button class="w-full rounded-2xl bg-[#ed5d26] px-4 py-3 font-black">✓ Concluir série</button>
                </form>
                {% endif %}

            </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>
</article>
{% endwith %}
{% endfor %}

{% if session %}
<form method="post" class="pb-8">
    {% csrf_token %}
    <input type="hidden" name="action" value="finish">
    <button class="w-full rounded-2xl bg-gradient-to-r from-[#ce3221] to-[#ed5d26] px-5 py-4 text-lg font-black">
        🏁 Finalizar treino
    </button>
</form>
{% endif %}

</div>

<div id="rest-timer" class="fixed bottom-24 left-1/2 z-[100] hidden -translate-x-1/2 rounded-full bg-[#ed5d26] px-6 py-3 font-black shadow-2xl">
    Descanso: <span id="rest-seconds">0</span>s
</div>

<script>
let restInterval = null;

function startRestTimer(seconds) {
    sessionStorage.setItem("restUntil", Date.now() + seconds * 1000);
}

function renderRestTimer() {
    const box = document.getElementById("rest-timer");
    const output = document.getElementById("rest-seconds");

    function update() {
        const until = Number(sessionStorage.getItem("restUntil"));

        if (!until) {
            box.classList.add("hidden");
            return;
        }

        const remaining = Math.ceil((until - Date.now()) / 1000);

        if (remaining <= 0) {
            sessionStorage.removeItem("restUntil");
            box.classList.add("hidden");
            clearInterval(restInterval);
            return;
        }

        output.textContent = remaining;
        box.classList.remove("hidden");
    }

    update();
    restInterval = setInterval(update, 500);
}

document.addEventListener("DOMContentLoaded", renderRestTimer);
</script>

<style>
input {
    width:100%; min-height:46px; border:1px solid rgba(255,255,255,.10);
    border-radius:14px; padding:10px 12px; background:#151310; color:white;
}
</style>
{% endblock %}
HTML

echo "==> Gravando templates.html"
cat > apps/workouts/templates/workouts/templates.html <<'HTML'
{% extends "base.html" %}
{% block title %}Modelos de treino{% endblock %}
{% block content %}

<div class="space-y-6">

<div>
    <span class="text-xs font-bold uppercase tracking-[.25em] text-[#ed5d26]">Produtividade</span>
    <h1 class="mt-2 text-3xl font-black">Modelos de treino</h1>
    <p class="mt-1 text-sm text-[#b8b3af]">Salve uma prescrição pronta e aplique a vários alunos.</p>
</div>

<div class="grid gap-4 lg:grid-cols-2">
{% for template in templates %}
<div class="rounded-[26px] border border-white/10 bg-[#1a1715] p-5">
    <h2 class="text-xl font-black">{{ template.name }}</h2>
    {% if template.objective %}
    <p class="mt-1 text-sm text-[#b8b3af]">{{ template.objective }}</p>
    {% endif %}

    <div class="mt-4 text-sm text-[#716b67]">{{ template.routines.count }} treino(s)</div>

    <form method="post" class="mt-4">
        {% csrf_token %}
        <input type="hidden" name="template_id" value="{{ template.id }}">
        <button class="w-full rounded-2xl bg-gradient-to-r from-[#ce3221] to-[#ed5d26] px-5 py-3 font-bold">
            Aplicar a alunos
        </button>
    </form>
</div>
{% empty %}
<div class="col-span-full rounded-3xl border border-dashed border-white/10 p-12 text-center text-[#b8b3af]">
    Ainda não existem modelos. Abra um plano e use “Salvar como modelo”.
</div>
{% endfor %}
</div>

</div>
{% endblock %}
HTML

echo "==> Gravando template_apply.html"
cat > apps/workouts/templates/workouts/template_apply.html <<'HTML'
{% extends "base.html" %}
{% block title %}Aplicar modelo{% endblock %}
{% block content %}

<div class="mx-auto max-w-3xl space-y-6">

<div>
    <span class="text-xs font-bold uppercase tracking-[.25em] text-[#ed5d26]">Modelo</span>
    <h1 class="mt-2 text-3xl font-black">{{ template.name }}</h1>
    <p class="mt-1 text-sm text-[#b8b3af]">Selecione um ou vários alunos.</p>
</div>

<form method="post" class="space-y-5 rounded-[28px] border border-white/10 bg-[#1a1715] p-5 sm:p-8">
    {% csrf_token %}

    {% for field in form %}
    <div>
        <label class="mb-2 block text-sm font-bold">{{ field.label }}</label>
        {{ field }}
        {% for error in field.errors %}
        <div class="mt-1 text-sm text-red-400">{{ error }}</div>
        {% endfor %}
    </div>
    {% endfor %}

    <button class="w-full rounded-2xl bg-gradient-to-r from-[#ce3221] to-[#ed5d26] px-5 py-4 font-black">
        Aplicar modelo
    </button>
</form>

</div>

<style>
input:not([type="checkbox"]), select, textarea {
    width:100%; min-height:48px; border:1px solid rgba(255,255,255,.1);
    border-radius:14px; padding:12px 15px; background:#0c0c09; color:white;
}
#id_students { display:grid; gap:8px; }
#id_students label {
    display:flex; align-items:center; gap:10px; background:rgba(255,255,255,.04);
    border-radius:14px; padding:12px;
}
</style>
{% endblock %}
HTML

echo "==> Gravando schedule.html"
cat > apps/workouts/templates/workouts/schedule.html <<'HTML'
{% extends "base.html" %}
{% block title %}Agenda do plano{% endblock %}
{% block content %}

<div class="mx-auto max-w-5xl space-y-6">

<div>
    <a href="{% url 'workouts:edit' %}" class="text-sm text-[#ed8e5f]">← Voltar ao plano</a>
    <h1 class="mt-3 text-3xl font-black">Agenda do plano</h1>
    <p class="text-[#b8b3af]">{{ plan.student.name }} • {{ plan.name }}</p>
</div>

<div class="grid gap-6 lg:grid-cols-[.8fr_1.2fr]">

<form method="post" class="space-y-4 rounded-[28px] border border-white/10 bg-[#1a1715] p-5">
    {% csrf_token %}
    <input type="hidden" name="action" value="save">

    <h2 class="text-xl font-black">Programar treino</h2>

    {% for field in form %}
    <div>
        <label class="mb-1 block text-sm font-bold">{{ field.label }}</label>
        {{ field }}
        {% for error in field.errors %}
        <div class="mt-1 text-sm text-red-400">{{ error }}</div>
        {% endfor %}
    </div>
    {% endfor %}

    <button class="w-full rounded-2xl bg-[#ed5d26] px-5 py-3 font-bold">Salvar na agenda</button>
</form>

<div class="space-y-3">
{% for item in schedules %}
<div class="rounded-[24px] border border-white/10 bg-[#1a1715] p-5">
    <div class="flex items-center justify-between gap-4">
        <div>
            <div class="text-lg font-black">{{ item.get_weekday_display }}</div>
            <div class="mt-1 text-sm text-[#b8b3af]">
                {{ item.routine.name }}
                {% if item.time %} • {{ item.time|time:"H:i" }}{% endif %}
            </div>
        </div>

        {% if item.is_active %}
        <span class="rounded-full bg-green-500/10 px-3 py-1 text-xs font-bold text-green-400">Ativo</span>
        {% else %}
        <span class="rounded-full bg-white/5 px-3 py-1 text-xs text-[#716b67]">Pausado</span>
        {% endif %}
    </div>

    <div class="mt-4 grid grid-cols-2 gap-2">
        <form method="post">
            {% csrf_token %}
            <input type="hidden" name="action" value="toggle">
            <input type="hidden" name="schedule_id" value="{{ item.id }}">
            <button class="w-full rounded-2xl bg-white/5 px-4 py-2 font-bold">
                {% if item.is_active %}Pausar{% else %}Ativar{% endif %}
            </button>
        </form>

        <form method="post">
            {% csrf_token %}
            <input type="hidden" name="action" value="delete">
            <input type="hidden" name="schedule_id" value="{{ item.id }}">
            <button class="w-full rounded-2xl bg-red-500/10 px-4 py-2 font-bold text-red-400">Excluir</button>
        </form>
    </div>
</div>
{% empty %}
<div class="rounded-3xl border border-dashed border-white/10 p-10 text-center text-[#b8b3af]">
    Nenhum treino programado.
</div>
{% endfor %}
</div>

</div>
</div>

<style>
input, select {
    width:100%; min-height:48px; border:1px solid rgba(255,255,255,.1);
    border-radius:14px; padding:12px 15px; background:#0c0c09; color:white;
}
</style>
{% endblock %}
HTML

echo "==> Gravando agenda.html"
cat > apps/workouts/templates/workouts/agenda.html <<'HTML'
{% extends "base.html" %}
{% block title %}Agenda semanal{% endblock %}
{% block content %}

<div class="space-y-6">

<div>
    <span class="text-xs font-bold uppercase tracking-[.25em] text-[#ed5d26]">Acompanhamento</span>
    <h1 class="mt-2 text-3xl font-black">Agenda semanal</h1>
    <p class="mt-1 text-sm text-[#b8b3af]">Treinos previstos, concluídos e não realizados.</p>
</div>

<div class="grid gap-3 sm:grid-cols-3">
    <div class="rounded-[24px] border border-white/10 bg-[#1a1715] p-5">
        <div class="text-sm text-[#b8b3af]">Previstos até hoje</div>
        <div class="mt-2 text-3xl font-black">{{ planned }}</div>
    </div>

    <div class="rounded-[24px] border border-white/10 bg-[#1a1715] p-5">
        <div class="text-sm text-[#b8b3af]">Concluídos</div>
        <div class="mt-2 text-3xl font-black text-green-400">{{ completed }}</div>
    </div>

    <div class="rounded-[24px] border border-white/10 bg-[#1a1715] p-5">
        <div class="text-sm text-[#b8b3af]">Adesão semanal</div>
        <div class="mt-2 text-3xl font-black text-[#ed8e5f]">{{ adherence }}%</div>
    </div>
</div>

<div class="grid gap-4 xl:grid-cols-2">
{% for day in days %}
<section class="rounded-[28px] border {% if day.is_today %}border-[#ed5d26]/50{% else %}border-white/10{% endif %} bg-[#1a1715] p-5">
    <div class="flex items-center justify-between">
        <div>
            <h2 class="text-xl font-black">{{ day.label }}</h2>
            <div class="text-sm text-[#716b67]">{{ day.date|date:"d/m" }}</div>
        </div>
        {% if day.is_today %}
        <span class="rounded-full bg-[#ed5d26] px-3 py-1 text-xs font-bold">Hoje</span>
        {% endif %}
    </div>

    <div class="mt-4 space-y-3">
    {% for entry in day.entries %}
        <div class="rounded-2xl bg-[#0c0c09] p-4">
            <div class="flex items-start justify-between gap-4">
                <div>
                    <div class="font-black">{{ entry.schedule.routine.plan.student.name }}</div>
                    <div class="mt-1 text-sm text-[#b8b3af]">
                        {{ entry.schedule.routine.name }}
                        {% if entry.schedule.time %} • {{ entry.schedule.time|time:"H:i" }}{% endif %}
                    </div>
                </div>

                {% if entry.status == "concluido" %}
                <span class="text-xs font-bold text-green-400">Concluído</span>
                {% elif entry.status == "nao_realizado" %}
                <span class="text-xs font-bold text-red-400">Não realizado</span>
                {% elif entry.status == "pendente" %}
                <span class="text-xs font-bold text-yellow-400">Pendente</span>
                {% else %}
                <span class="text-xs font-bold text-[#716b67]">Programado</span>
                {% endif %}
            </div>
        </div>
    {% empty %}
        <div class="text-sm text-[#716b67]">Sem treinos programados.</div>
    {% endfor %}
    </div>
</section>
{% endfor %}
</div>

</div>
{% endblock %}
HTML

echo "==> Compilando arquivos Python"
python3 -m py_compile \
  apps/workouts/models.py \
  apps/workouts/forms.py \
  apps/workouts/views.py \
  apps/workouts/urls.py \
  apps/workouts/admin.py \
  apps/workouts/migrations/0003_advanced_templates_schedule.py

echo "==> Rebuild"
docker compose up -d --build

echo "==> Migrações"
docker compose exec web python manage.py migrate

echo "==> Django check"
docker compose exec web python manage.py check

echo
echo "========================================================="
echo "PACOTE 3B.4 → 3B.7 CONCLUÍDO"
echo "========================================================="
echo "3B.4 Progressão automática: OK"
echo "3B.5 Métodos avançados / RPE / RIR: OK"
echo "3B.6 Modelos reutilizáveis: OK"
echo "3B.7 Agenda semanal / adesão: OK"
echo
echo "Teste:"
echo "  http://localhost:8011/treinos/"
echo "  http://localhost:8011/treinos/modelos/"
echo "  http://localhost:8011/treinos/agenda-semanal/"
echo
echo "Backup: $BACKUP"
