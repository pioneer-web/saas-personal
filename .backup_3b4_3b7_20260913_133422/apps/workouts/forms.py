from django import forms
from django.db.models import Q

from apps.exercises.models import Exercise
from apps.students.models import Student

from .models import (
    WorkoutExercise,
    WorkoutPlan,
    WorkoutRoutine,
)


class WorkoutPlanForm(forms.ModelForm):

    class Meta:
        model = WorkoutPlan
        fields = [
            "student",
            "name",
            "objective",
            "status",
            "start_date",
            "end_date",
            "notes",
        ]

        widgets = {
            "start_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={"rows": 3}
            ),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["student"].queryset = (
            Student.objects.filter(
                organization=organization
            ).order_by("name")
            if organization
            else Student.objects.none()
        )


class WorkoutRoutineForm(forms.ModelForm):

    class Meta:
        model = WorkoutRoutine
        fields = [
            "name",
            "instructions",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder":
                    "Ex.: Treino A - Peito e Tríceps"
                }
            ),
            "instructions": forms.Textarea(
                attrs={"rows": 2}
            ),
        }


class WorkoutExerciseForm(forms.ModelForm):

    class Meta:
        model = WorkoutExercise

        fields = [
            "exercise",
            "sets",
            "reps",
            "load_kg",
            "rest_seconds",
            "cadence",
            "notes",
        ]

        widgets = {
            "notes": forms.Textarea(
                attrs={"rows": 2}
            ),
            "reps": forms.TextInput(
                attrs={"placeholder": "Ex.: 10-12"}
            ),
            "cadence": forms.TextInput(
                attrs={"placeholder": "Ex.: 3-1-2"}
            ),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)

        if organization:
            self.fields["exercise"].queryset = (
                Exercise.objects.filter(
                    Q(organization__isnull=True)
                    | Q(organization=organization)
                ).order_by(
                    "name_ptbr",
                    "name",
                )
            )
        else:
            self.fields["exercise"].queryset = (
                Exercise.objects.none()
            )
