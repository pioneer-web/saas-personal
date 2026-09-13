import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SecurityThrottle",
            fields=[
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
                    "key_hash",
                    models.CharField(max_length=64, unique=True),
                ),
                ("scope", models.CharField(max_length=80)),
                ("window_started_at", models.DateTimeField()),
                ("count", models.PositiveIntegerField(default=0)),
                (
                    "blocked_until",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="SecurityEvent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("event_type", models.CharField(max_length=80)),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("info", "Informação"),
                            ("warning", "Alerta"),
                            ("critical", "Crítico"),
                        ],
                        default="info",
                        max_length=20,
                    ),
                ),
                (
                    "identifier_hash",
                    models.CharField(blank=True, max_length=64),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True,
                        null=True,
                    ),
                ),
                ("path", models.CharField(blank=True, max_length=255)),
                (
                    "user_agent",
                    models.CharField(blank=True, max_length=255),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="security_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="securitythrottle",
            index=models.Index(
                fields=["scope", "updated_at"],
                name="security_th_scope_72c9f6_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="securitythrottle",
            index=models.Index(
                fields=["blocked_until"],
                name="security_th_blocked_4d9320_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="securityevent",
            index=models.Index(
                fields=["event_type", "created_at"],
                name="security_ev_event_t_8ab210_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="securityevent",
            index=models.Index(
                fields=["severity", "created_at"],
                name="security_ev_severit_6e35f4_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="securityevent",
            index=models.Index(
                fields=["ip_address", "created_at"],
                name="security_ev_ip_addr_1a4fb4_idx",
            ),
        ),
    ]
