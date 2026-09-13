import hashlib
import ipaddress
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import SecurityEvent, SecurityThrottle


def normalize_identifier(value):
    return str(value or "").strip().lower()


def hash_identifier(value):
    value = normalize_identifier(value)
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def get_client_ip(request):
    candidate = request.META.get("REMOTE_ADDR", "")

    if getattr(settings, "SECURITY_TRUST_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            candidate = forwarded.split(",")[0].strip()

    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _throttle_hash(scope, identifier):
    raw = f"{scope}|{normalize_identifier(identifier)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def check_rate_limit(
    scope,
    identifier,
    *,
    limit,
    window_seconds,
    block_seconds,
):
    now = timezone.now()
    digest = _throttle_hash(scope, identifier)
    window = timedelta(seconds=window_seconds)

    with transaction.atomic():
        try:
            row = (
                SecurityThrottle.objects
                .select_for_update()
                .get(key_hash=digest)
            )
        except SecurityThrottle.DoesNotExist:
            try:
                row = SecurityThrottle.objects.create(
                    key_hash=digest,
                    scope=scope,
                    window_started_at=now,
                    count=1,
                )
                return True, 0
            except IntegrityError:
                row = (
                    SecurityThrottle.objects
                    .select_for_update()
                    .get(key_hash=digest)
                )

        if row.blocked_until and row.blocked_until > now:
            retry_after = max(
                1,
                int((row.blocked_until - now).total_seconds()),
            )
            return False, retry_after

        if row.window_started_at <= now - window:
            row.window_started_at = now
            row.count = 1
            row.blocked_until = None
            row.save(
                update_fields=[
                    "window_started_at",
                    "count",
                    "blocked_until",
                    "updated_at",
                ]
            )
            return True, 0

        row.count += 1

        if row.count > limit:
            row.blocked_until = now + timedelta(seconds=block_seconds)
            row.save(
                update_fields=[
                    "count",
                    "blocked_until",
                    "updated_at",
                ]
            )
            return False, block_seconds

        row.save(update_fields=["count", "updated_at"])
        return True, 0


def clear_rate_limit(scope, identifier):
    SecurityThrottle.objects.filter(
        key_hash=_throttle_hash(scope, identifier)
    ).delete()


def record_security_event(
    request,
    event_type,
    *,
    severity=SecurityEvent.Severity.INFO,
    identifier="",
    user=None,
    metadata=None,
):
    try:
        SecurityEvent.objects.create(
            event_type=event_type,
            severity=severity,
            user=user if getattr(user, "pk", None) else None,
            identifier_hash=hash_identifier(identifier),
            ip_address=get_client_ip(request),
            path=(request.path or "")[:255],
            user_agent=(
                request.META.get("HTTP_USER_AGENT", "") or ""
            )[:255],
            metadata=metadata or {},
        )
    except Exception:
        # O log de segurança nunca deve derrubar a aplicação.
        return
