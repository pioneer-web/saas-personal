from django.contrib import admin

from .models import SecurityEvent, SecurityThrottle


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "severity",
        "ip_address",
        "user",
        "created_at",
    )
    list_filter = ("severity", "event_type", "created_at")
    search_fields = ("event_type", "ip_address", "path")
    readonly_fields = (
        "event_type",
        "severity",
        "user",
        "identifier_hash",
        "ip_address",
        "path",
        "user_agent",
        "metadata",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SecurityThrottle)
class SecurityThrottleAdmin(admin.ModelAdmin):
    list_display = (
        "scope",
        "count",
        "blocked_until",
        "updated_at",
    )
    list_filter = ("scope",)
    readonly_fields = (
        "key_hash",
        "scope",
        "window_started_at",
        "count",
        "blocked_until",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
