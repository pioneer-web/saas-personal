import re
import secrets
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import PermissionDenied
from django.db.models import Max
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.exercises.models import Exercise
from apps.students.models import Student
from apps.workouts.models import (
    WorkoutExercise,
    WorkoutPlan,
    WorkoutRoutine,
    WorkoutSchedule,
    WorkoutSession,
    WorkoutSetLog,
)

from .decorators import student_account_required
from .forms import StudentActivationForm, StudentLoginForm
from .models import (
    StudentAccount,
    StudentInvitation,
    StudentNotification,
)


User = get_user_model()


def organization_or_403(request):
    if not request.organization:
        raise PermissionDenied("Usuário sem organização ativa.")
    return request.organization


def safe_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def safe_int(value, minimum, maximum):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if minimum <= value <= maximum else None


def progression_for_item(item, student, organization):
    if not getattr(item, "progression_enabled", False):
        return None

    latest = (
        WorkoutSetLog.objects
        .filter(
            organization=organization,
            session__student=student,
            session__status=WorkoutSession.Status.COMPLETED,
            workout_exercise__exercise=item.exercise,
        )
        .select_related("session")
        .order_by("-session__completed_at", "set_number")
        .first()
    )

    if not latest or latest.load_kg is None:
        return None

    logs = list(
        WorkoutSetLog.objects
        .filter(
            organization=organization,
            session_id=latest.session_id,
            workout_exercise__exercise=item.exercise,
        )
        .order_by("set_number")
    )

    loads = [log.load_kg for log in logs if log.load_kg is not None]
    if not loads:
        return None

    last_load = max(loads)
    rep_values = [int(x) for x in re.findall(r"\d+", item.reps or "")]
    target = max(rep_values) if rep_values else None

    done_reps = []
    for log in logs:
        values = re.findall(r"\d+", log.reps_done or "")
        if values:
            done_reps.append(int(values[0]))

    reached = bool(
        target
        and len(logs) >= item.sets
        and len(done_reps) >= item.sets
        and all(value >= target for value in done_reps[: item.sets])
    )

    increment = getattr(item, "progression_increment_kg", Decimal("2.50"))

    return {
        "last_load": last_load,
        "suggested_load": last_load + increment if reached else last_load,
        "reached_target": reached,
    }


@login_required
def trainer_access_list(request):
    organization = organization_or_403(request)

    students = Student.objects.filter(
        organization=organization
    ).order_by("name")

    return render(
        request,
        "student_portal/trainer_access.html",
        {
            "students": students,
            "access_code": request.session.pop("student_access_code", None),
            "access_student": request.session.pop("student_access_name", None),
            "access_expiry": request.session.pop("student_access_expiry", None),
        },
    )


@login_required
@require_POST
def trainer_generate_access(request):
    organization = organization_or_403(request)

    student = get_object_or_404(
        Student,
        pk=request.POST.get("student_id"),
        organization=organization,
    )

    if not student.email:
        raise PermissionDenied("O aluno precisa ter e-mail cadastrado.")

    if StudentAccount.objects.filter(
        student=student,
        is_active=True,
    ).exists():
        return redirect("student_access:list")

    StudentInvitation.objects.filter(
        student=student,
        used_at__isnull=True,
    ).delete()

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = timezone.now() + timedelta(hours=48)

    StudentInvitation.objects.create(
        organization=organization,
        student=student,
        code_hash=make_password(code),
        expires_at=expires_at,
        created_by=request.user,
    )

    request.session["student_access_code"] = code
    request.session["student_access_name"] = student.name
    request.session["student_access_expiry"] = (
        timezone.localtime(expires_at).strftime("%d/%m/%Y %H:%M")
    )

    return redirect("student_access:list")


def activate(request):
    error = ""

    if request.method == "POST":
        form = StudentActivationForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            code = form.cleaned_data["code"]

            candidates = (
                StudentInvitation.objects
                .select_related("student", "organization")
                .filter(
                    student__email__iexact=email,
                    used_at__isnull=True,
                    expires_at__gt=timezone.now(),
                )
                .order_by("-created_at")
            )

            invitation = next(
                (
                    candidate
                    for candidate in candidates
                    if check_password(code, candidate.code_hash)
                ),
                None,
            )

            if not invitation:
                error = "Código inválido ou expirado."

            elif StudentAccount.objects.filter(
                student=invitation.student
            ).exists():
                error = "Este aluno já possui acesso."

            elif User.objects.filter(email=email).exists():
                error = "Já existe uma conta com este e-mail."

            else:
                user = User.objects.create_user(
                    email=email,
                    password=form.cleaned_data["password"],
                    name=invitation.student.name,
                )

                StudentAccount.objects.create(
                    organization=invitation.organization,
                    student=invitation.student,
                    user=user,
                )

                invitation.used_at = timezone.now()
                invitation.save(update_fields=["used_at"])

                login(request, user)
                return redirect("student_portal:home")

    else:
        form = StudentActivationForm()

    return render(
        request,
        "student_portal/activate.html",
        {"form": form, "error": error},
    )


def student_login(request):
    error = ""

    if request.method == "POST":
        form = StudentLoginForm(request.POST)

        if form.is_valid():
            user = authenticate(
                request,
                email=form.cleaned_data["email"].strip().lower(),
                password=form.cleaned_data["password"],
            )

            account = (
                StudentAccount.objects
                .filter(user=user, is_active=True)
                .first()
                if user
                else None
            )

            if not account:
                error = "E-mail ou senha inválidos."
            else:
                login(request, user)
                account.last_access_at = timezone.now()
                account.save(update_fields=["last_access_at"])
                return redirect("student_portal:home")

    else:
        form = StudentLoginForm()

    return render(
        request,
        "student_portal/login.html",
        {"form": form, "error": error},
    )


@student_account_required
@require_POST
def student_logout(request):
    logout(request)
    return redirect("student_portal:login")


@student_account_required
def home(request):
    student = request.student
    organization = request.student_organization
    today = timezone.localdate()

    schedules = (
        WorkoutSchedule.objects
        .filter(
            organization=organization,
            routine__plan__student=student,
            routine__plan__status=WorkoutPlan.Status.ACTIVE,
            weekday=today.weekday(),
            is_active=True,
        )
        .select_related("routine", "routine__plan")
        .order_by("time")
    )

    routines = (
        WorkoutRoutine.objects
        .filter(
            organization=organization,
            plan__student=student,
            plan__status=WorkoutPlan.Status.ACTIVE,
        )
        .select_related("plan")
        .order_by("plan__created_at", "order")
    )

    if request.method == "POST" and request.POST.get("routine_id"):
        routine = get_object_or_404(
            WorkoutRoutine,
            pk=request.POST["routine_id"],
            organization=organization,
            plan__student=student,
        )
        request.session["student_app_routine_id"] = str(routine.pk)
        return redirect("student_portal:workout")

    week_start = today - timedelta(days=today.weekday())

    completed_week = WorkoutSession.objects.filter(
        organization=organization,
        student=student,
        status=WorkoutSession.Status.COMPLETED,
        completed_at__date__gte=week_start,
    ).count()

    unread_notifications = StudentNotification.objects.filter(
        organization=organization,
        student=student,
        read_at__isnull=True,
    ).count()

    return render(
        request,
        "student_portal/home.html",
        {
            "student": student,
            "schedules": schedules,
            "routines": routines,
            "completed_week": completed_week,
            "unread_notifications": unread_notifications,
            "today": today,
        },
    )


@student_account_required
def workout(request):
    student = request.student
    organization = request.student_organization

    routine_id = request.session.get("student_app_routine_id")

    if not routine_id:
        return redirect("student_portal:home")

    routine = get_object_or_404(
        WorkoutRoutine.objects.select_related("plan"),
        pk=routine_id,
        organization=organization,
        plan__student=student,
    )

    items = list(
        routine.items
        .filter(organization=organization)
        .select_related("exercise")
        .order_by("order")
    )

    session = (
        WorkoutSession.objects
        .filter(
            organization=organization,
            student=student,
            routine=routine,
            status=WorkoutSession.Status.IN_PROGRESS,
        )
        .order_by("-started_at")
        .first()
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "start":
            if not session:
                WorkoutSession.objects.create(
                    organization=organization,
                    student=student,
                    routine=routine,
                )
            return redirect("student_portal:workout")

        if action == "complete_set" and session:
            item = get_object_or_404(
                WorkoutExercise,
                pk=request.POST.get("item_id"),
                organization=organization,
                routine=routine,
            )

            try:
                set_number = int(request.POST.get("set_number", "0"))
            except ValueError:
                set_number = 0

            if not 1 <= set_number <= item.sets:
                raise PermissionDenied("Série inválida.")

            WorkoutSetLog.objects.update_or_create(
                organization=organization,
                session=session,
                workout_exercise=item,
                set_number=set_number,
                defaults={
                    "reps_done": request.POST.get("reps_done", "").strip(),
                    "load_kg": safe_decimal(request.POST.get("load_kg")),
                    "rpe_actual": safe_int(
                        request.POST.get("rpe_actual"),
                        1,
                        10,
                    ),
                    "rir_actual": safe_int(
                        request.POST.get("rir_actual"),
                        0,
                        10,
                    ),
                },
            )

            return redirect("student_portal:workout")

        if action == "finish" and session:
            session.status = WorkoutSession.Status.COMPLETED
            session.completed_at = timezone.now()
            session.save(update_fields=["status", "completed_at"])

            StudentNotification.objects.create(
                organization=organization,
                student=student,
                title="Treino concluído 💪",
                body=f"{routine.name} foi registrado com sucesso.",
            )

            return redirect("student_portal:home")

    completed = {}

    if session:
        for log in session.set_logs.all():
            completed[
                (str(log.workout_exercise_id), log.set_number)
            ] = log

    workout_data = []

    for item in items:
        workout_data.append(
            {
                "item": item,
                "sets": [
                    {
                        "number": number,
                        "log": completed.get(
                            (str(item.pk), number)
                        ),
                    }
                    for number in range(1, item.sets + 1)
                ],
                "progression": progression_for_item(
                    item,
                    student,
                    organization,
                ),
            }
        )

    return render(
        request,
        "student_portal/workout.html",
        {
            "routine": routine,
            "session": session,
            "workout_data": workout_data,
        },
    )


@student_account_required
def history(request):
    sessions = (
        WorkoutSession.objects
        .filter(
            organization=request.student_organization,
            student=request.student,
            status=WorkoutSession.Status.COMPLETED,
        )
        .select_related("routine", "routine__plan")
        .order_by("-completed_at")
    )

    return render(
        request,
        "student_portal/history.html",
        {"sessions": sessions},
    )


@student_account_required
def progress(request):
    student = request.student
    organization = request.student_organization

    if request.method == "POST" and request.POST.get("exercise_id"):
        request.session["student_progress_exercise_id"] = (
            request.POST["exercise_id"]
        )
        return redirect("student_portal:progress")

    exercise_ids = (
        WorkoutSetLog.objects
        .filter(
            organization=organization,
            session__student=student,
            session__status=WorkoutSession.Status.COMPLETED,
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

    selected = Exercise.objects.filter(
        pk=request.session.get("student_progress_exercise_id"),
        pk__in=exercise_ids,
    ).first()

    points = []
    max_load = Decimal("0")

    if selected:
        rows = list(
            WorkoutSetLog.objects
            .filter(
                organization=organization,
                session__student=student,
                session__status=WorkoutSession.Status.COMPLETED,
                workout_exercise__exercise=selected,
                load_kg__isnull=False,
            )
            .values("completed_at__date")
            .annotate(max_load=Max("load_kg"))
            .order_by("completed_at__date")
        )

        if rows:
            max_load = max(row["max_load"] for row in rows)

        points = [
            {
                "date": row["completed_at__date"],
                "load": row["max_load"],
                "percentage": (
                    int((row["max_load"] / max_load) * 100)
                    if max_load
                    else 0
                ),
            }
            for row in rows
        ]

    return render(
        request,
        "student_portal/progress.html",
        {
            "exercises": exercises,
            "selected": selected,
            "points": points,
            "max_load": max_load,
        },
    )


@student_account_required
def notifications(request):
    items = StudentNotification.objects.filter(
        organization=request.student_organization,
        student=request.student,
    )

    if request.method == "POST":
        items.filter(
            read_at__isnull=True
        ).update(read_at=timezone.now())

        return redirect("student_portal:notifications")

    return render(
        request,
        "student_portal/notifications.html",
        {"notifications": items},
    )


@student_account_required
def profile(request):
    return render(
        request,
        "student_portal/profile.html",
        {"student": request.student},
    )


def manifest(request):
    return JsonResponse(
        {
            "name": "Personal - Aluno",
            "short_name": "Personal",
            "start_url": "/app/",
            "scope": "/app/",
            "display": "standalone",
            "background_color": "#0c0c09",
            "theme_color": "#ed5d26",
            "icons": [
                {
                    "src": "/app/icon.svg",
                    "sizes": "any",
                    "type": "image/svg+xml",
                }
            ],
        },
        content_type="application/manifest+json",
    )


def service_worker(request):
    return HttpResponse(
        "self.addEventListener('install',()=>self.skipWaiting());"
        "self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));"
        "self.addEventListener('fetch',()=>{});",
        content_type="application/javascript",
    )


def icon(request):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
        '<rect width="512" height="512" rx="120" fill="#0c0c09"/>'
        '<circle cx="256" cy="256" r="180" fill="#ed5d26"/>'
        '<text x="256" y="335" text-anchor="middle" font-family="Arial" '
        'font-size="230" font-weight="900" fill="white">P</text></svg>'
    )
    return HttpResponse(svg, content_type="image/svg+xml")
