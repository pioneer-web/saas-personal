import json
import secrets
from datetime import timedelta
from functools import wraps

from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from apps.workouts.models import (
    WorkoutExercise,
    WorkoutPlan,
    WorkoutRoutine,
    WorkoutSchedule,
    WorkoutSession,
    WorkoutSetLog,
)

from .models import StudentAccount, StudentApiToken


def read_json(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return {}


def token_account(request):
    auth = request.headers.get("Authorization", "")

    if not auth.startswith("Bearer "):
        return None

    token_hash = StudentApiToken.hash_token(
        auth[7:].strip()
    )

    token = (
        StudentApiToken.objects
        .select_related(
            "account",
            "account__student",
            "account__organization",
        )
        .filter(
            token_hash=token_hash,
            expires_at__gt=timezone.now(),
            account__is_active=True,
        )
        .first()
    )

    if not token:
        return None

    token.last_used_at = timezone.now()
    token.save(update_fields=["last_used_at"])

    return token.account


def api_student_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        account = token_account(request)

        if not account:
            return JsonResponse(
                {"detail": "Token inválido ou expirado."},
                status=401,
            )

        request.student = account.student
        request.student_organization = account.organization

        return view(request, *args, **kwargs)

    return wrapped


@csrf_exempt
def login_api(request):
    if request.method != "POST":
        return JsonResponse(
            {"detail": "Método não permitido."},
            status=405,
        )

    data = read_json(request)

    user = authenticate(
        request,
        email=str(data.get("email", "")).strip().lower(),
        password=str(data.get("password", "")),
    )

    account = (
        StudentAccount.objects
        .select_related("student", "organization")
        .filter(user=user, is_active=True)
        .first()
        if user
        else None
    )

    if not account:
        return JsonResponse(
            {"detail": "Credenciais inválidas."},
            status=401,
        )

    plain_token = secrets.token_urlsafe(40)

    StudentApiToken.objects.create(
        account=account,
        token_hash=StudentApiToken.hash_token(plain_token),
        expires_at=timezone.now() + timedelta(days=30),
    )

    return JsonResponse(
        {
            "token": plain_token,
            "student": {
                "name": account.student.name,
                "email": account.student.email,
            },
        }
    )


@csrf_exempt
@api_student_required
def home_api(request):
    if request.method != "GET":
        return JsonResponse(
            {"detail": "Método não permitido."},
            status=405,
        )

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
    )

    routines = (
        WorkoutRoutine.objects
        .filter(
            organization=organization,
            plan__student=student,
            plan__status=WorkoutPlan.Status.ACTIVE,
        )
        .select_related("plan")
        .order_by("order")
    )

    return JsonResponse(
        {
            "student": {
                "name": student.name,
                "email": student.email,
            },
            "today_workouts": [
                {
                    "routine_id": str(item.routine_id),
                    "name": item.routine.name,
                    "plan": item.routine.plan.name,
                }
                for item in schedules
            ],
            "routines": [
                {
                    "routine_id": str(item.pk),
                    "name": item.name,
                    "plan": item.plan.name,
                }
                for item in routines
            ],
        }
    )


@csrf_exempt
@api_student_required
def workout_api(request):
    if request.method != "POST":
        return JsonResponse(
            {"detail": "Método não permitido."},
            status=405,
        )

    data = read_json(request)
    action = data.get("action")
    student = request.student
    organization = request.student_organization

    if action in {"detail", "start"}:
        routine = (
            WorkoutRoutine.objects
            .select_related("plan")
            .filter(
                pk=data.get("routine_id"),
                organization=organization,
                plan__student=student,
            )
            .first()
        )

        if not routine:
            return JsonResponse(
                {"detail": "Treino não encontrado."},
                status=404,
            )

        session = None

        if action == "start":
            session = (
                WorkoutSession.objects
                .filter(
                    organization=organization,
                    student=student,
                    routine=routine,
                    status=WorkoutSession.Status.IN_PROGRESS,
                )
                .first()
            )

            if not session:
                session = WorkoutSession.objects.create(
                    organization=organization,
                    student=student,
                    routine=routine,
                )

        items = (
            routine.items
            .filter(organization=organization)
            .select_related("exercise")
            .order_by("order")
        )

        return JsonResponse(
            {
                "routine": {
                    "id": str(routine.pk),
                    "name": routine.name,
                    "plan": routine.plan.name,
                },
                "session_id": (
                    str(session.pk)
                    if session
                    else None
                ),
                "items": [
                    {
                        "item_id": str(item.pk),
                        "name": item.exercise.display_name,
                        "sets": item.sets,
                        "reps": item.reps,
                        "load_kg": (
                            str(item.load_kg)
                            if item.load_kg is not None
                            else None
                        ),
                        "rest_seconds": item.rest_seconds,
                        "method": item.get_method_display(),
                        "video_url": item.exercise.media_url,
                        "embed_url": item.exercise.embed_video_url,
                        "image_url": item.exercise.display_image_url,
                    }
                    for item in items
                ],
            }
        )

    if action == "complete_set":
        session = (
            WorkoutSession.objects
            .filter(
                pk=data.get("session_id"),
                organization=organization,
                student=student,
                status=WorkoutSession.Status.IN_PROGRESS,
            )
            .first()
        )

        if not session:
            return JsonResponse(
                {"detail": "Sessão não encontrada."},
                status=404,
            )

        item = (
            WorkoutExercise.objects
            .filter(
                pk=data.get("item_id"),
                organization=organization,
                routine=session.routine,
            )
            .first()
        )

        if not item:
            return JsonResponse(
                {"detail": "Exercício não encontrado."},
                status=404,
            )

        try:
            set_number = int(data.get("set_number", 0))
        except (TypeError, ValueError):
            set_number = 0

        if not 1 <= set_number <= item.sets:
            return JsonResponse(
                {"detail": "Série inválida."},
                status=400,
            )

        WorkoutSetLog.objects.update_or_create(
            organization=organization,
            session=session,
            workout_exercise=item,
            set_number=set_number,
            defaults={
                "reps_done": str(
                    data.get("reps_done", "")
                ).strip(),
                "load_kg": data.get("load_kg") or None,
                "rpe_actual": data.get("rpe_actual") or None,
                "rir_actual": (
                    data.get("rir_actual")
                    if data.get("rir_actual") != ""
                    else None
                ),
            },
        )

        return JsonResponse({"ok": True})

    if action == "finish":
        session = (
            WorkoutSession.objects
            .filter(
                pk=data.get("session_id"),
                organization=organization,
                student=student,
                status=WorkoutSession.Status.IN_PROGRESS,
            )
            .first()
        )

        if not session:
            return JsonResponse(
                {"detail": "Sessão não encontrada."},
                status=404,
            )

        session.status = WorkoutSession.Status.COMPLETED
        session.completed_at = timezone.now()
        session.save(
            update_fields=["status", "completed_at"]
        )

        return JsonResponse({"ok": True})

    return JsonResponse(
        {"detail": "Ação inválida."},
        status=400,
    )


@csrf_exempt
@api_student_required
def history_api(request):
    sessions = (
        WorkoutSession.objects
        .filter(
            organization=request.student_organization,
            student=request.student,
            status=WorkoutSession.Status.COMPLETED,
        )
        .select_related("routine", "routine__plan")
        .order_by("-completed_at")[:100]
    )

    return JsonResponse(
        {
            "history": [
                {
                    "routine": item.routine.name,
                    "plan": item.routine.plan.name,
                    "completed_at": (
                        item.completed_at.isoformat()
                        if item.completed_at
                        else None
                    ),
                }
                for item in sessions
            ]
        }
    )
