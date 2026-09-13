import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "exercises",
            "0002_remove_exercise_exercises_name_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="exercise",
            name="base_exercise",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="personalizations",
                to="exercises.exercise",
            ),
        ),
        migrations.AddField(
            model_name="exercise",
            name="custom_image",
            field=models.FileField(
                blank=True,
                upload_to="exercises/images/%Y/%m/",
                verbose_name="Imagem própria",
            ),
        ),
        migrations.AddField(
            model_name="exercise",
            name="custom_video",
            field=models.FileField(
                blank=True,
                upload_to="exercises/videos/%Y/%m/",
                verbose_name="Vídeo próprio",
            ),
        ),
    ]
