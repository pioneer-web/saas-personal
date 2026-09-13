import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("organizations", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="Exercise",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=160, verbose_name="Nome")),
                ("primary_muscle", models.CharField(max_length=120, verbose_name="Músculo principal")),
                ("secondary_muscles", models.CharField(blank=True, max_length=250, verbose_name="Músculos secundários")),
                ("equipment", models.CharField(blank=True, max_length=120, verbose_name="Equipamento")),
                ("instructions", models.TextField(blank=True, verbose_name="Instruções")),
                ("media_url", models.URLField(blank=True, verbose_name="Vídeo/Animação")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="exercises", to="organizations.organization")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddIndex(model_name="exercise", index=models.Index(fields=["name"], name="exercises_name_idx")),
        migrations.AddIndex(model_name="exercise", index=models.Index(fields=["primary_muscle"], name="exercises_muscle_idx")),
    ]
