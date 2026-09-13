from django import forms

from .models import Exercise


class ExerciseForm(forms.ModelForm):

    class Meta:
        model = Exercise

        fields = [
            "name",
            "description",
            "primary_muscle",
            "secondary_muscles",
            "equipment",
            "body_part",
            "category",
            "difficulty",
            "instructions",
            "media_url",
        ]

        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 3}
            ),
            "instructions": forms.Textarea(
                attrs={"rows": 5}
            ),
            "media_url": forms.URLInput(
                attrs={
                    "placeholder":
                    "https://youtube.com/... ou https://bilibili.com/..."
                }
            ),
        }


class GlobalExerciseForm(forms.ModelForm):

    class Meta:
        model = Exercise

        fields = [
            "name_ptbr",
            "primary_muscle_ptbr",
            "secondary_muscles_ptbr",
            "equipment_ptbr",
            "category_ptbr",
            "difficulty_ptbr",
            "instructions_ptbr",
            "media_url",
        ]

        labels = {
            "name_ptbr": "Nome",
            "primary_muscle_ptbr": "Músculo principal",
            "secondary_muscles_ptbr": "Músculos secundários",
            "equipment_ptbr": "Equipamento",
            "category_ptbr": "Categoria",
            "difficulty_ptbr": "Dificuldade",
            "instructions_ptbr": "Instruções",
        }
