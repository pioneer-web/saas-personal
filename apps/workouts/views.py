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
from apps.organizations.permissions import trainer_or_owner_required

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
@trainer_or_owner_required
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
@trainer_or_owner_required
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
@trainer_or_owner_required
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
@trainer_or_owner_required
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
@trainer_or_owner_required
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
@trainer_or_owner_required
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
@trainer_or_owner_required
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
@trainer_or_owner_required
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
@trainer_or_owner_required
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
@trainer_or_owner_required
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
@trainer_or_owner_required
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
