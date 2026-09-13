from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.shortcuts import redirect, render

from apps.security_center.models import SecurityEvent
from apps.security_center.utils import (
    check_rate_limit,
    clear_rate_limit,
    get_client_ip,
    normalize_identifier,
    record_security_event,
)


def health(request):
    return JsonResponse({"status": "ok"})


def secure_login(request):
    error = ""

    if request.user.is_authenticated:
        if (
            hasattr(request.user, "student_account")
            and not request.user.memberships.filter(
                is_active=True,
                organization__is_active=True,
            ).exists()
        ):
            return redirect("student_portal:home")
        return redirect("dashboard")

    if request.method == "POST":
        email = normalize_identifier(
            request.POST.get("username", "")
        )
        ip = get_client_ip(request) or "unknown"

        checks = [
            (
                "trainer-login-ip",
                ip,
                30,
                600,
                1800,
            ),
            (
                "trainer-login-identity",
                f"{ip}|{email}",
                10,
                600,
                1800,
            ),
            (
                "trainer-login-email",
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
                retry_after = max(retry_after, retry)

        if retry_after:
            record_security_event(
                request,
                "trainer_login_rate_limited",
                severity=SecurityEvent.Severity.WARNING,
                identifier=email,
            )
            response = render(
                request,
                "registration/login.html",
                {
                    "form": AuthenticationForm(
                        request=request
                    ),
                    "security_error":
                    "Muitas tentativas. Tente novamente mais tarde.",
                },
                status=429,
            )
            response["Retry-After"] = str(retry_after)
            return response

    form = AuthenticationForm(
        request=request,
        data=request.POST or None,
    )

    if request.method == "POST":
        email = normalize_identifier(
            request.POST.get("username", "")
        )
        ip = get_client_ip(request) or "unknown"

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            clear_rate_limit(
                "trainer-login-identity",
                f"{ip}|{email}",
            )

            record_security_event(
                request,
                "login_success",
                user=user,
                identifier=email,
            )

            if (
                hasattr(user, "student_account")
                and not user.memberships.filter(
                    is_active=True,
                    organization__is_active=True,
                ).exists()
            ):
                return redirect("student_portal:home")

            return redirect("dashboard")

        record_security_event(
            request,
            "login_failed",
            severity=SecurityEvent.Severity.WARNING,
            identifier=email,
        )
        error = "E-mail ou senha inválidos."

    return render(
        request,
        "registration/login.html",
        {
            "form": form,
            "security_error": error,
        },
    )


@login_required
def dashboard(request):
    if (
        hasattr(request.user, "student_account")
        and not request.user.memberships.filter(
            is_active=True,
            organization__is_active=True,
        ).exists()
    ):
        return redirect("student_portal:home")

    return render(
        request,
        "dashboard.html",
        {
            "organization":
            getattr(request, "organization", None)
        },
    )
