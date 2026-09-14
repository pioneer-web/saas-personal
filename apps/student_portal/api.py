import json
import re
import secrets
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from apps.security_center.models import SecurityEvent
from apps.security_center.utils import (
    check_rate_limit,
    clear_rate_limit,
    get_client_ip,
    normalize_identifier,
    record_security_event,
)
from apps.workouts.models import (
    WorkoutExercise,
    WorkoutPlan,
    WorkoutRoutine,
    WorkoutSchedule,
    WorkoutSession,
    WorkoutSetLog,
)

from .models import (
    StudentAccount,
    StudentApiToken,
    StudentNotification,
)



def notify_student(organization, student, title, body, dedupe_hours=1):
    cutoff = timezone.now() - timedelta(hours=dedupe_hours)
    exists = StudentNotification.objects.filter(
        organization=organization,
        student=student,
        title=title,
        body=body,
        created_at__gte=cutoff,
    ).exists()
    if not exists:
        StudentNotification.objects.create(
            organization=organization,
            student=student,
            title=title,
            body=body,
        )


def json_error(message, status):
    return JsonResponse(
        {"detail": message},
        status=status,
    )


def read_json(request):
    content_type = (
        request.META
        .get("CONTENT_TYPE", "")
        .split(";")[0]
        .strip()
        .lower()
    )

    if content_type != "application/json":
        return None

    try:
        data = json.loads(
            request.body.decode("utf-8") or "{}"
        )
    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        return None

    return data if isinstance(data, dict) else None


def parse_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def parse_decimal(value, minimum, maximum):
    if value in (None, ""):
        return None, True

    try:
        value = Decimal(
            str(value).replace(",", ".")
        )
    except (InvalidOperation, ValueError):
        return None, False

    if value < minimum or value > maximum:
        return None, False

    return value, True


def parse_int(value, minimum, maximum):
    if value in (None, ""):
        return None, True

    try:
        value = int(value)
    except (TypeError, ValueError):
        return None, False

    if value < minimum or value > maximum:
        return None, False

    return value, True


def token_account(request):
    auth = request.headers.get(
        "Authorization",
        "",
    )

    if not auth.startswith("Bearer "):
        return None, None

    plain_token = auth[7:].strip()

    if not plain_token:
        return None, None

    token_hash = StudentApiToken.hash_token(
        plain_token
    )

    token = (
        StudentApiToken.objects
        .select_related(
            "account",
            "account__student",
            "account__organization",
            "account__user",
        )
        .filter(
            token_hash=token_hash,
            expires_at__gt=timezone.now(),
            revoked_at__isnull=True,
            account__is_active=True,
            account__organization__is_active=True,
            account__user__is_active=True,
        )
        .first()
    )

    if not token:
        return None, None

    token.last_used_at = timezone.now()
    token.save(
        update_fields=["last_used_at"]
    )

    return token.account, token


def api_student_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        account, token = token_account(request)

        if not account:
            return json_error(
                "Token inválido ou expirado.",
                401,
            )

        request.student_account = account
        request.student_token = token
        request.student = account.student
        request.student_organization = (
            account.organization
        )

        return view_func(
            request,
            *args,
            **kwargs,
        )

    return wrapped


@csrf_exempt
def login_api(request):
    if request.method != "POST":
        return json_error(
            "Método não permitido.",
            405,
        )

    data = read_json(request)

    if data is None:
        return json_error(
            "JSON inválido.",
            400,
        )

    email = normalize_identifier(
        data.get("email", "")
    )
    password = str(
        data.get("password", "")
    )

    ip = get_client_ip(request) or "unknown"

    checks = [
        (
            "api-student-login-ip",
            ip,
            30,
            600,
            1800,
        ),
        (
            "api-student-login-identity",
            f"{ip}|{email}",
            10,
            600,
            1800,
        ),
        (
            "api-student-login-email",
            email,
            20,
            1800,
            1800,
        ),
    ]

    retry_after = 0

    for scope, key, limit, window, block in checks:
        allowed, retry = check_rate_limit(
            scope,
            key,
            limit=limit,
            window_seconds=window,
            block_seconds=block,
        )
        if not allowed:
            retry_after = max(
                retry_after,
                retry,
            )

    if retry_after:
        record_security_event(
            request,
            "api_student_login_rate_limited",
            severity=SecurityEvent.Severity.WARNING,
            identifier=email,
        )
        response = json_error(
            "Muitas tentativas. Tente novamente mais tarde.",
            429,
        )
        response["Retry-After"] = str(
            retry_after
        )
        return response

    user = authenticate(
        request,
        email=email,
        password=password,
    )

    account = (
        StudentAccount.objects
        .select_related(
            "student",
            "organization",
            "user",
        )
        .filter(
            user=user,
            user__is_active=True,
            is_active=True,
            organization__is_active=True,
        )
        .first()
        if user
        else None
    )

    if not account:
        record_security_event(
            request,
            "api_student_login_failed",
            severity=SecurityEvent.Severity.WARNING,
            identifier=email,
        )
        return json_error(
            "Credenciais inválidas.",
            401,
        )

    clear_rate_limit(
        "api-student-login-identity",
        f"{ip}|{email}",
    )

    now = timezone.now()

    account.api_tokens.filter(
        expires_at__lte=now,
    ).delete()

    active_tokens = list(
        account.api_tokens.filter(
            revoked_at__isnull=True,
            expires_at__gt=now,
        ).order_by("-created_at")
    )

    for old_token in active_tokens[4:]:
        old_token.revoked_at = now
        old_token.save(
            update_fields=["revoked_at"]
        )

    plain_token = secrets.token_urlsafe(48)

    StudentApiToken.objects.create(
        account=account,
        token_hash=StudentApiToken.hash_token(
            plain_token
        ),
        expires_at=now + timedelta(days=30),
    )

    record_security_event(
        request,
        "api_student_login_success",
        user=user,
        identifier=email,
    )

    return JsonResponse(
        {
            "token": plain_token,
            "expires_in_days": 30,
            "student": {
                "name": account.student.name,
                "email": account.student.email,
            },
        }
    )


@csrf_exempt
@api_student_required
def logout_api(request):
    if request.method != "POST":
        return json_error(
            "Método não permitido.",
            405,
        )

    request.student_token.revoked_at = (
        timezone.now()
    )
    request.student_token.save(
        update_fields=["revoked_at"]
    )

    return JsonResponse({"ok": True})


@csrf_exempt
@api_student_required
def home_api(request):
    if request.method != "GET":
        return json_error(
            "Método não permitido.",
            405,
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
        .select_related(
            "routine",
            "routine__plan",
        )
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

    today_schedules = list(schedules)
    if today_schedules:
        routine_names = ", ".join(
            item.routine.name
            for item in today_schedules[:3]
        )
        notify_student(
            organization,
            student,
            "Treino de hoje",
            f"Hoje você tem: {routine_names}.",
            dedupe_hours=20,
        )

    return JsonResponse(
        {
            "student": {
                "name": student.name,
                "email": student.email,
            },
            "unread_notifications": StudentNotification.objects.filter(
                organization=organization,
                student=student,
                read_at__isnull=True,
            ).count(),
            "today": str(today),
            "today_workouts": [
                {
                    "routine_id":
                    str(item.routine_id),
                    "name":
                    item.routine.name,
                    "plan":
                    item.routine.plan.name,
                }
                for item in schedules
            ],
            "routines": [
                {
                    "routine_id":
                    str(item.pk),
                    "name":
                    item.name,
                    "plan":
                    item.plan.name,
                }
                for item in routines
            ],
        }
    )


@csrf_exempt
@api_student_required
def workout_api(request):
    if request.method != "POST":
        return json_error(
            "Método não permitido.",
            405,
        )

    data = read_json(request)

    if data is None:
        return json_error(
            "JSON inválido.",
            400,
        )

    action = data.get("action")
    student = request.student
    organization = request.student_organization

    if action in {"detail", "start"}:
        routine_id = parse_uuid(
            data.get("routine_id")
        )

        if not routine_id:
            return json_error(
                "Treino inválido.",
                400,
            )

        routine = (
            WorkoutRoutine.objects
            .select_related("plan")
            .filter(
                pk=routine_id,
                organization=organization,
                plan__student=student,
                plan__status=WorkoutPlan.Status.ACTIVE,
            )
            .first()
        )

        if not routine:
            return json_error(
                "Treino não encontrado.",
                404,
            )

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

        if action == "start" and not session:
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
                        "name":
                        item.exercise.display_name,
                        "sets": item.sets,
                        "reps": item.reps,
                        "load_kg": (
                            str(item.load_kg)
                            if item.load_kg is not None
                            else None
                        ),
                        "rest_seconds":
                        item.rest_seconds,
                        "method":
                        item.get_method_display(),
                        "video_url":
                        item.exercise.media_url,
                        "embed_url":
                        item.exercise.embed_video_url,
                        "image_url":
                        item.exercise.display_image_url,
                        "completed_sets": (
                            [
                                {
                                    "set_number": log.set_number,
                                    "reps_done": log.reps_done,
                                    "load_kg": (
                                        str(log.load_kg)
                                        if log.load_kg is not None
                                        else None
                                    ),
                                }
                                for log in (
                                    WorkoutSetLog.objects
                                    .filter(
                                        organization=organization,
                                        session=session,
                                        workout_exercise=item,
                                    )
                                    .order_by("set_number")
                                )
                            ]
                            if session
                            else []
                        ),
                    }
                    for item in items
                ],
            }
        )

    if action == "complete_set":
        session_id = parse_uuid(
            data.get("session_id")
        )
        item_id = parse_uuid(
            data.get("item_id")
        )

        if not session_id or not item_id:
            return json_error(
                "Identificador inválido.",
                400,
            )

        session = (
            WorkoutSession.objects
            .filter(
                pk=session_id,
                organization=organization,
                student=student,
                status=WorkoutSession.Status.IN_PROGRESS,
            )
            .first()
        )

        if not session:
            return json_error(
                "Sessão não encontrada.",
                404,
            )

        item = (
            WorkoutExercise.objects
            .filter(
                pk=item_id,
                organization=organization,
                routine=session.routine,
            )
            .first()
        )

        if not item:
            return json_error(
                "Exercício não encontrado.",
                404,
            )

        try:
            set_number = int(
                data.get("set_number", 0)
            )
        except (TypeError, ValueError):
            set_number = 0

        if not 1 <= set_number <= item.sets:
            return json_error(
                "Série inválida.",
                400,
            )

        load, load_ok = parse_decimal(
            data.get("load_kg"),
            Decimal("0"),
            Decimal("2000"),
        )
        rpe, rpe_ok = parse_int(
            data.get("rpe_actual"),
            1,
            10,
        )
        rir, rir_ok = parse_int(
            data.get("rir_actual"),
            0,
            10,
        )

        if not (
            load_ok
            and rpe_ok
            and rir_ok
        ):
            return json_error(
                "Dados da série inválidos.",
                400,
            )

        reps_done = str(
            data.get("reps_done", "")
        ).strip()[:40]

        WorkoutSetLog.objects.update_or_create(
            organization=organization,
            session=session,
            workout_exercise=item,
            set_number=set_number,
            defaults={
                "reps_done": reps_done,
                "load_kg": load,
                "rpe_actual": rpe,
                "rir_actual": rir,
            },
        )

        return JsonResponse({"ok": True})

    if action == "finish":
        session_id = parse_uuid(
            data.get("session_id")
        )

        if not session_id:
            return json_error(
                "Sessão inválida.",
                400,
            )

        session = (
            WorkoutSession.objects
            .filter(
                pk=session_id,
                organization=organization,
                student=student,
                status=WorkoutSession.Status.IN_PROGRESS,
            )
            .first()
        )

        if not session:
            return json_error(
                "Sessão não encontrada.",
                404,
            )

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

        notify_student(
            organization,
            student,
            "Treino concluído 💪",
            f"{session.routine.name} foi registrado com sucesso.",
            dedupe_hours=1,
        )

        return JsonResponse({"ok": True})

    return json_error(
        "Ação inválida.",
        400,
    )


@csrf_exempt
@api_student_required
def evolution_api(request):
    if request.method != "GET":
        return json_error(
            "Método não permitido.",
            405,
        )

    student = request.student
    organization = request.student_organization
    today = timezone.localdate()
    start_7 = today - timedelta(days=6)
    start_30 = today - timedelta(days=29)
    previous_30_start = today - timedelta(days=59)
    previous_30_end = today - timedelta(days=30)

    sessions = list(
        WorkoutSession.objects
        .filter(
            organization=organization,
            student=student,
            status=WorkoutSession.Status.COMPLETED,
            completed_at__date__gte=previous_30_start,
        )
        .order_by("completed_at")
    )

    workouts_7d = sum(
        1
        for item in sessions
        if item.completed_at
        and item.completed_at.date() >= start_7
    )
    workouts_30d = sum(
        1
        for item in sessions
        if item.completed_at
        and item.completed_at.date() >= start_30
    )
    workouts_previous_30d = sum(
        1
        for item in sessions
        if item.completed_at
        and previous_30_start
        <= item.completed_at.date()
        <= previous_30_end
    )

    logs = list(
        WorkoutSetLog.objects
        .filter(
            organization=organization,
            session__student=student,
            session__status=WorkoutSession.Status.COMPLETED,
            session__completed_at__date__gte=previous_30_start,
        )
        .select_related(
            "session",
            "workout_exercise__exercise",
        )
        .order_by("completed_at")
    )

    volume_30d = Decimal("0")
    volume_previous_30d = Decimal("0")
    exercise_data = {}

    for log in logs:
        completed_date = (
            log.session.completed_at.date()
            if log.session.completed_at
            else log.completed_at.date()
        )

        reps_match = re.search(
            r"\d+",
            log.reps_done or "",
        )
        reps_value = (
            int(reps_match.group())
            if reps_match
            else 0
        )

        if log.load_kg is not None and reps_value > 0:
            set_volume = log.load_kg * reps_value

            if completed_date >= start_30:
                volume_30d += set_volume
            elif completed_date <= previous_30_end:
                volume_previous_30d += set_volume

        exercise = log.workout_exercise.exercise
        exercise_id = str(exercise.pk)

        if exercise_id not in exercise_data:
            exercise_data[exercise_id] = {
                "id": exercise_id,
                "name": exercise.display_name,
                "max_load": Decimal("0"),
                "last_load": None,
                "dates": {},
            }

        if log.load_kg is not None:
            item = exercise_data[exercise_id]
            item["last_load"] = log.load_kg
            item["max_load"] = max(
                item["max_load"],
                log.load_kg,
            )

            date_key = str(completed_date)
            previous = item["dates"].get(
                date_key,
                Decimal("0"),
            )
            item["dates"][date_key] = max(
                previous,
                log.load_kg,
            )

    def change_percent(current, previous):
        if previous:
            return round(
                ((float(current) - float(previous))
                 / float(previous)) * 100,
                1,
            )
        return 100.0 if current else 0.0

    week_start = today - timedelta(days=today.weekday())
    weekly_workouts = []

    for offset in range(7, -1, -1):
        start = week_start - timedelta(days=offset * 7)
        end = start + timedelta(days=6)
        count = sum(
            1
            for item in sessions
            if item.completed_at
            and start <= item.completed_at.date() <= end
        )
        weekly_workouts.append(
            {
                "label": start.strftime("%d/%m"),
                "count": count,
            }
        )

    exercise_progress = []

    for item in exercise_data.values():
        if item["max_load"] <= 0:
            continue

        points = [
            {
                "date": date,
                "load": float(load),
            }
            for date, load in sorted(
                item["dates"].items()
            )[-12:]
        ]

        exercise_progress.append(
            {
                "id": item["id"],
                "name": item["name"],
                "max_load": float(item["max_load"]),
                "last_load": (
                    float(item["last_load"])
                    if item["last_load"] is not None
                    else None
                ),
                "points": points,
            }
        )

    exercise_progress.sort(
        key=lambda item: item["max_load"],
        reverse=True,
    )

    return JsonResponse(
        {
            "summary": {
                "workouts_7d": workouts_7d,
                "workouts_30d": workouts_30d,
                "workouts_previous_30d":
                workouts_previous_30d,
                "workouts_change_pct": change_percent(
                    workouts_30d,
                    workouts_previous_30d,
                ),
                "volume_30d": round(
                    float(volume_30d),
                    1,
                ),
                "volume_previous_30d": round(
                    float(volume_previous_30d),
                    1,
                ),
                "volume_change_pct": change_percent(
                    volume_30d,
                    volume_previous_30d,
                ),
                "personal_records": len(
                    exercise_progress
                ),
            },
            "weekly_workouts": weekly_workouts,
            "exercise_progress": exercise_progress,
        }
    )

@csrf_exempt
@api_student_required
def history_api(request):
    if request.method != "GET":
        return json_error(
            "Método não permitido.",
            405,
        )

    sessions = (
        WorkoutSession.objects
        .filter(
            organization=request.student_organization,
            student=request.student,
            status=WorkoutSession.Status.COMPLETED,
        )
        .select_related(
            "routine",
            "routine__plan",
        )
        .order_by("-completed_at")[:100]
    )

    return JsonResponse(
        {
            "history": [
                {
                    "routine":
                    item.routine.name,
                    "plan":
                    item.routine.plan.name,
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

@csrf_exempt
@api_student_required
def notifications_api(request):
    student = request.student
    organization = request.student_organization

    items = StudentNotification.objects.filter(
        organization=organization,
        student=student,
    )

    if request.method == "GET":
        notifications = list(items.order_by("-created_at")[:100])

        return JsonResponse(
            {
                "unread_count": items.filter(
                    read_at__isnull=True,
                ).count(),
                "notifications": [
                    {
                        "id": str(item.pk),
                        "title": item.title,
                        "body": item.body,
                        "is_read": item.read_at is not None,
                        "read_at": (
                            item.read_at.isoformat()
                            if item.read_at
                            else None
                        ),
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in notifications
                ],
            }
        )

    if request.method != "POST":
        return json_error(
            "Método não permitido.",
            405,
        )

    data = read_json(request)
    if data is None:
        return json_error(
            "JSON inválido.",
            400,
        )

    action = data.get("action")

    if action == "mark_all_read":
        items.filter(
            read_at__isnull=True,
        ).update(read_at=timezone.now())

        return JsonResponse({"ok": True})

    if action == "mark_read":
        notification_id = parse_uuid(
            data.get("notification_id")
        )
        if not notification_id:
            return json_error(
                "Notificação inválida.",
                400,
            )

        notification = items.filter(
            pk=notification_id,
        ).first()

        if not notification:
            return json_error(
                "Notificação não encontrada.",
                404,
            )

        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(
                update_fields=["read_at"]
            )

        return JsonResponse({"ok": True})

    return json_error(
        "Ação inválida.",
        400,
    )


@csrf_exempt
@api_student_required
def profile_api(request):
    if request.method != "GET":
        return json_error(
            "Método não permitido.",
            405,
        )

    student = request.student

    return JsonResponse(
        {
            "student": {
                "name": student.name,
                "email": student.email,
                "phone": student.phone,
                "status": student.get_status_display(),
            },
            "organization": {
                "name": request.student_organization.name,
            },
        }
    )
