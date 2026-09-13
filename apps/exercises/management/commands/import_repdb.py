import json
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand

from apps.exercises.models import Exercise


DATA_URL = "https://exercise-dataset.com/exercises.json"
BASE_URL = "https://exercise-dataset.com/"


class Command(BaseCommand):
    help = "Importa a biblioteca gratuita RepDB."

    def handle(self, *args, **options):
        self.stdout.write("Baixando biblioteca RepDB...")

        request = Request(
            DATA_URL,
            headers={"User-Agent": "SaaSPersonal/1.0"},
        )

        with urlopen(request, timeout=60) as response:
            data = json.load(response)

        exercises = data.get("exercises", [])

        created_count = 0
        updated_count = 0

        for item in exercises:
            flat = (
                item.get("images", {})
                .get("flat", {})
            )

            def image_url(key):
                path = flat.get(key)
                return urljoin(BASE_URL, path) if path else ""

            primary = ", ".join(
                item.get("primary_muscles") or []
            )[:120]

            secondary = ", ".join(
                item.get("secondary_muscles") or []
            )[:250]

            instructions = "\n".join(
                f"{index}. {text}"
                for index, text in enumerate(
                    item.get("instructions_en") or [],
                    start=1,
                )
            )

            exercise, created = Exercise.objects.update_or_create(
                source_id=item["id"],
                defaults={
                    "organization": None,
                    "name": item.get("name_en") or item["id"],
                    "description": item.get("description_en") or "",
                    "primary_muscle": primary,
                    "secondary_muscles": secondary,
                    "equipment": item.get("equipment") or "",
                    "body_part": item.get("body_part") or "",
                    "category": item.get("category") or "",
                    "difficulty": item.get("difficulty") or "",
                    "met": item.get("met"),
                    "is_unilateral": bool(
                        item.get("is_unilateral", False)
                    ),
                    "is_bodyweight": bool(
                        item.get("is_bodyweight", False)
                    ),
                    "instructions": instructions,
                    "image_start_url": image_url("start"),
                    "image_peak_url": image_url("peak"),
                    "image_main_url": image_url("main"),
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Importação concluída: "
                f"{created_count} novos / "
                f"{updated_count} atualizados."
            )
        )
