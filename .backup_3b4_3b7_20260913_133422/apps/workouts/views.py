from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Max
from django.utils import timezone
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from .forms import (
    WorkoutExerciseForm,
    WorkoutPlanForm,
    WorkoutRoutineForm,
)
from .models import (
    WorkoutExercise,
    WorkoutPlan,
    WorkoutRoutine,
    WorkoutSession,
    WorkoutSetLog,
)


def organization_or_403(request):
    if not request.organization:
        raise PermissionDenied(
            "Usuário sem organização ativa."
        )

    return request.organization


@login_required
def plan_list(request):
    organization = organization_or_403(request)

    plans = (
        WorkoutPlan.objects
        .filter(organization=organization)
        .select_related("student")
        .prefetch_related("routines")
    )

    if request.method == "POST":

        plan = get_object_or_404(
            WorkoutPlan,
            pk=request.POST.get("plan_id"),
            organization=organization,
        )

        request.session["editing_workout_plan_id"] = str(
            plan.pk
        )

        return redirect("workouts:edit")

    return render(
        request,
        "workouts/list.html",
        {"plans": plans},
    )


@login_required
def plan_create(request):
    organization = organization_or_403(request)

    if request.method == "POST":

        form = WorkoutPlanForm(
            request.POST,
            organization=organization,
        )

        if form.is_valid():

            plan = form.save(commit=False)
            plan.organization = organization
            plan.save()

            request.session[
                "editing_workout_plan_id"
            ] = str(plan.pk)

            return redirect("workouts:edit")

    else:

        form = WorkoutPlanForm(
            organization=organization
        )

    return render(
        request,
        "workouts/plan_form.html",
        {
            "form": form,
            "title": "Novo plano de treino",
        },
    )


@login_required
def plan_edit(request):
    organization = organization_or_403(request)

    plan_id = request.session.get(
        "editing_workout_plan_id"
    )

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

    routines = plan.routines.filter(
        organization=organization
    )

    routine_form = WorkoutRoutineForm()

    return render(
        request,
        "workouts/plan_edit.html",
        {
            "plan": plan,
            "form": form,
            "routines": routines,
            "routine_form": routine_form,
        },
    )


@login_required
def routine_add(request):
    organization = organization_or_403(request)

    plan_id = request.session.get(
        "editing_workout_plan_id"
    )

    plan = get_object_or_404(
        WorkoutPlan,
        pk=plan_id,
        organization=organization,
    )

    if request.method == "POST":

        form = WorkoutRoutineForm(request.POST)

        if form.is_valid():

            routine = form.save(commit=False)

            last_order = (
                plan.routines.aggregate(
                    max_order=Max("order")
                )["max_order"]
                or 0
            )

            routine.organization = organization
            routine.plan = plan
            routine.order = last_order + 1
            routine.save()

    return redirect("workouts:edit")


@login_required
def routine_builder(request):
    organization = organization_or_403(request)

    if (
        request.method == "POST"
        and request.POST.get("select_routine_id")
    ):

        routine = get_object_or_404(
            WorkoutRoutine,
            pk=request.POST["select_routine_id"],
            organization=organization,
        )

        request.session[
            "editing_workout_routine_id"
        ] = str(routine.pk)

        return redirect("workouts:builder")

    routine_id = request.session.get(
        "editing_workout_routine_id"
    )

    if not routine_id:
        return redirect("workouts:list")

    routine = get_object_or_404(
        WorkoutRoutine,
        pk=routine_id,
        organization=organization,
    )

    if request.method == "POST":

        action = request.POST.get("action")

        if action == "add":

            form = WorkoutExerciseForm(
                request.POST,
                organization=organization,
            )

            if form.is_valid():

                item = form.save(commit=False)

                last_order = (
                    routine.items.aggregate(
                        max_order=Max("order")
                    )["max_order"]
                    or 0
                )

                item.organization = organization
                item.routine = routine
                item.order = last_order + 1
                item.save()

                return redirect(
                    "workouts:builder"
                )

        elif action == "remove":

            item = get_object_or_404(
                WorkoutExercise,
                pk=request.POST.get("item_id"),
                routine=routine,
                organization=organization,
            )

            item.delete()

            return redirect(
                "workouts:builder"
            )

    else:

        form = WorkoutExerciseForm(
            organization=organization
        )

    items = (
        routine.items
        .filter(organization=organization)
        .select_related("exercise")
    )

    return render(
        request,
        "workouts/builder.html",
        {
            "routine": routine,
            "items": items,
            "form": form,
        },
    )



@login_required
def student_workout_preview(request):
    organization = organization_or_403(request)

    if (
        request.method == "POST"
        and request.POST.get("select_student_routine_id")
    ):
        routine = get_object_or_404(
            WorkoutRoutine,
            pk=request.POST[
                "select_student_routine_id"
            ],
            organization=organization,
        )

        request.session[
            "student_preview_routine_id"
        ] = str(routine.pk)

        request.session.pop(
            "active_workout_session_id",
            None,
        )

        return redirect(
            "workouts:student_workout"
        )

    routine_id = request.session.get(
        "student_preview_routine_id"
    )

    if not routine_id:
        return redirect("workouts:list")

    routine = get_object_or_404(
        WorkoutRoutine.objects.select_related(
            "plan",
            "plan__student",
        ),
        pk=routine_id,
        organization=organization,
    )

    items = (
        routine.items
        .filter(organization=organization)
        .select_related("exercise")
    )

    session = None

    session_id = request.session.get(
        "active_workout_session_id"
    )

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

                request.session[
                    "active_workout_session_id"
                ] = str(session.pk)

            return redirect(
                "workouts:student_workout"
            )

        if action == "complete_set":

            if not session:
                return redirect(
                    "workouts:student_workout"
                )

            item = get_object_or_404(
                WorkoutExercise,
                pk=request.POST.get("item_id"),
                routine=routine,
                organization=organization,
            )

            try:
                set_number = int(
                    request.POST.get(
                        "set_number",
                        "0",
                    )
                )
            except ValueError:
                set_number = 0

            if (
                set_number < 1
                or set_number > item.sets
            ):
                raise PermissionDenied(
                    "Série inválida."
                )

            reps_done = (
                request.POST
                .get("reps_done", "")
                .strip()
            )

            load = (
                request.POST
                .get("load_kg", "")
                .strip()
            )

            WorkoutSetLog.objects.update_or_create(
                organization=organization,
                session=session,
                workout_exercise=item,
                set_number=set_number,
                defaults={
                    "reps_done": reps_done,
                    "load_kg": load or None,
                },
            )

            return redirect(
                "workouts:student_workout"
            )

        if action == "finish":

            if session:
                session.status = (
                    WorkoutSession.Status.COMPLETED
                )

                session.completed_at = timezone.now()

                session.save(
                    update_fields=[
                        "status",
                        "completed_at",
                    ]
                )

                request.session.pop(
                    "active_workout_session_id",
                    None,
                )

            return redirect(
                "workouts:student_workout"
            )

    completed = {}

    if session:
        for log in session.set_logs.all():
            completed[
                (
                    str(log.workout_exercise_id),
                    log.set_number,
                )
            ] = log

    workout_data = []

    for item in items:

        sets = []

        for number in range(
            1,
            item.sets + 1,
        ):
            sets.append(
                {
                    "number": number,
                    "log": completed.get(
                        (
                            str(item.pk),
                            number,
                        )
                    ),
                }
            )

        last_log = (
            WorkoutSetLog.objects
            .filter(
                organization=organization,
                session__student=routine.plan.student,
                session__status=WorkoutSession.Status.COMPLETED,
                workout_exercise__exercise=item.exercise,
            )
            .exclude(
                load_kg__isnull=True
            )
            .order_by(
                "-completed_at"
            )
            .first()
        )

        workout_data.append(
            {
                "item": item,
                "sets": sets,
                "last_load":
                    last_log.load_kg
                    if last_log
                    else None,
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

    student_id = request.session.get(
        "workout_history_student_id"
    )

    if (
        request.method == "POST"
        and request.POST.get("student_id")
    ):
        student = get_object_or_404(
            __import__(
                "apps.students.models",
                fromlist=["Student"],
            ).Student,
            pk=request.POST["student_id"],
            organization=organization,
        )

        request.session[
            "workout_history_student_id"
        ] = str(student.pk)

        return redirect("workouts:history")

    from apps.students.models import Student

    students = Student.objects.filter(
        organization=organization
    ).order_by("name")

    student = None
    sessions = []

    if student_id:
        student = Student.objects.filter(
            pk=student_id,
            organization=organization,
        ).first()

    if student:
        sessions = (
            WorkoutSession.objects
            .filter(
                organization=organization,
                student=student,
                status=WorkoutSession.Status.COMPLETED,
            )
            .select_related(
                "routine",
                "routine__plan",
            )
            .annotate(
                completed_sets=Count("set_logs")
            )
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

    from apps.students.models import Student
    from apps.exercises.models import Exercise

    student_id = request.session.get(
        "progress_student_id"
    )

    exercise_id = request.session.get(
        "progress_exercise_id"
    )

    if request.method == "POST":

        if request.POST.get("student_id"):
            student = get_object_or_404(
                Student,
                pk=request.POST["student_id"],
                organization=organization,
            )

            request.session[
                "progress_student_id"
            ] = str(student.pk)

            request.session.pop(
                "progress_exercise_id",
                None,
            )

            return redirect(
                "workouts:progress"
            )

        if request.POST.get("exercise_id"):
            exercise = get_object_or_404(
                Exercise,
                pk=request.POST["exercise_id"],
            )

            request.session[
                "progress_exercise_id"
            ] = str(exercise.pk)

            return redirect(
                "workouts:progress"
            )

    students = Student.objects.filter(
        organization=organization
    ).order_by("name")

    student = None
    exercise = None
    exercises = []
    progression = []

    if student_id:
        student = Student.objects.filter(
            pk=student_id,
            organization=organization,
        ).first()

    if student:
        exercise_ids = (
            WorkoutSetLog.objects
            .filter(
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
        ).order_by(
            "name_ptbr",
            "name",
        )

    if student and exercise_id:

        exercise = Exercise.objects.filter(
            pk=exercise_id
        ).first()

        if exercise:

            logs = (
                WorkoutSetLog.objects
                .filter(
                    organization=organization,
                    session__student=student,
                    workout_exercise__exercise=exercise,
                    session__status=
                        WorkoutSession.Status.COMPLETED,
                )
                .select_related(
                    "session",
                )
                .order_by(
                    "completed_at"
                )
            )

            for log in logs:
                progression.append(
                    {
                        "date":
                            log.completed_at,
                        "load":
                            log.load_kg,
                        "reps":
                            log.reps_done,
                        "set_number":
                            log.set_number,
                    }
                )

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
