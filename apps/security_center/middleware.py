from django.http import HttpResponse
from django.urls import Resolver404, resolve

from .models import SecurityEvent
from .utils import (
    check_rate_limit,
    get_client_ip,
    record_security_event,
)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-src https://www.youtube.com https://youtube.com "
            "https://player.bilibili.com https://www.bilibili.com;"
        )

        response["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), interest-cohort=()"
        )
        response["X-Permitted-Cross-Domain-Policies"] = "none"

        if (
            request.path.startswith("/app/")
            or request.path.startswith("/api/student/")
            or request.path.startswith("/acessos-alunos/")
            or request.path.startswith("/admin/")
            or request.path == "/login/"
        ):
            response["Cache-Control"] = "no-store, private"
            response["Pragma"] = "no-cache"

        return response


class SensitiveRateLimitMiddleware:
    """Protege o login do Django Admin contra força bruta.

    Os demais logins/ativação possuem controles mais fortes nas próprias views,
    incluindo limitação por IP + identificador.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST":
            try:
                match = resolve(request.path_info)
            except Resolver404:
                match = None

            if (
                match
                and match.app_name == "admin"
                and match.url_name == "login"
            ):
                ip = get_client_ip(request) or "unknown"
                allowed, retry_after = check_rate_limit(
                    "admin-login-ip",
                    ip,
                    limit=10,
                    window_seconds=600,
                    block_seconds=1800,
                )

                if not allowed:
                    record_security_event(
                        request,
                        "admin_login_rate_limited",
                        severity=SecurityEvent.Severity.WARNING,
                    )
                    response = HttpResponse(
                        "Muitas tentativas. Tente novamente mais tarde.",
                        status=429,
                    )
                    response["Retry-After"] = str(retry_after)
                    return response

        return self.get_response(request)
