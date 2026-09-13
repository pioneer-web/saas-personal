import json
import re
import unicodedata
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand

from apps.exercises.models import Exercise


PTBR_URL = (
    "https://raw.githubusercontent.com/"
    "gugeldev/exercicios-bd-ptbr/main/"
    "exercises/exercises-ptbr-full-translation.json"
)


def normalize(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def instructions_to_text(items):
    return "\n".join(
        f"{index}. {text}"
        for index, text in enumerate(items or [], start=1)
    )


class Command(BaseCommand):
    help = "Localiza a biblioteca de exercícios para português do Brasil."

    def handle(self, *args, **options):
        self.stdout.write("Baixando biblioteca PT-BR...")

        request = Request(
            PTBR_URL,
            headers={"User-Agent": "SaaSPersonal/1.0"},
        )

        with urlopen(request, timeout=60) as response:
            ptbr_data = json.load(response)

        ptbr_by_id = {
            normalize(item.get("id")): item
            for item in ptbr_data
            if item.get("id")
        }

        matched_keys = set()
        localized = 0

        # Primeiro: localizar exercícios RepDB que tenham correspondência.
        repdb_exercises = Exercise.objects.filter(
            organization__isnull=True
        ).exclude(source_id__startswith="ptbr:")

        for exercise in repdb_exercises:
            key = normalize(exercise.source_id)

            item = ptbr_by_id.get(key)

            if not item:
                continue

            matched_keys.add(key)

            exercise.name_ptbr = item.get("name", "")
            exercise.primary_muscle_ptbr = ", ".join(
                item.get("primaryMuscles") or []
            )[:120]

            exercise.secondary_muscles_ptbr = ", ".join(
                item.get("secondaryMuscles") or []
            )[:250]

            exercise.equipment_ptbr = item.get("equipment") or ""
            exercise.category_ptbr = item.get("category") or ""
            exercise.difficulty_ptbr = item.get("level") or ""

            exercise.instructions_ptbr = instructions_to_text(
                item.get("instructions")
            )

            exercise.save(
                update_fields=[
                    "name_ptbr",
                    "primary_muscle_ptbr",
                    "secondary_muscles_ptbr",
                    "equipment_ptbr",
                    "category_ptbr",
                    "difficulty_ptbr",
                    "instructions_ptbr",
                    "updated_at",
                ]
            )

            localized += 1

        # Depois: adicionar os exercícios PT-BR que não existem no RepDB.
        added = 0

        for item in ptbr_data:
            key = normalize(item.get("id"))

            if not key or key in matched_keys:
                continue

            source_id = f"ptbr:{item['id']}"

            primary = ", ".join(
                item.get("primaryMuscles") or []
            )[:120]

            secondary = ", ".join(
                item.get("secondaryMuscles") or []
            )[:250]

            instructions = instructions_to_text(
                item.get("instructions")
            )

            _, created = Exercise.objects.update_or_create(
                source_id=source_id,
                defaults={
                    "organization": None,
                    "name": item.get("name") or item["id"],
                    "name_ptbr": item.get("name") or "",
                    "primary_muscle": primary,
                    "primary_muscle_ptbr": primary,
                    "secondary_muscles": secondary,
                    "secondary_muscles_ptbr": secondary,
                    "equipment": item.get("equipment") or "",
                    "equipment_ptbr": item.get("equipment") or "",
                    "category": item.get("category") or "",
                    "category_ptbr": item.get("category") or "",
                    "difficulty": item.get("level") or "",
                    "difficulty_ptbr": item.get("level") or "",
                    "instructions": instructions,
                    "instructions_ptbr": instructions,
                },
            )

            if created:
                added += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"PT-BR concluído: {localized} exercícios RepDB "
                f"localizados + {added} exercícios PT-BR adicionados."
            )
        )
