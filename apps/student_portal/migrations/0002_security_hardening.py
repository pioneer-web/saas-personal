from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("student_portal", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentinvitation",
            name="failed_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="studentinvitation",
            name="locked_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="studentapitoken",
            name="revoked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="studentinvitation",
            index=models.Index(
                fields=["expires_at", "used_at"],
                name="student_por_expires_5a4a95_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="studentinvitation",
            index=models.Index(
                fields=["student", "created_at"],
                name="student_por_student_74f6ce_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="studentapitoken",
            index=models.Index(
                fields=["expires_at", "revoked_at"],
                name="student_por_expires_c8e3ca_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="studentapitoken",
            index=models.Index(
                fields=["account", "created_at"],
                name="student_por_account_9c190c_idx",
            ),
        ),
    ]
