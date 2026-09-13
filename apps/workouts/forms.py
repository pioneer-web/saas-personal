from django import forms
from django.db.models import Q

from apps.exercises.models import Exercise
from apps.students.models import Student

from .models import WorkoutExercise, WorkoutPlan, WorkoutRoutine, WorkoutSchedule


class ExerciseChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        parts = [obj.display_name]
        if obj.display_primary_muscle:
            parts.append(obj.display_primary_muscle)
        if obj.display_equipment:
            parts.append(obj.display_equipment)
        return " — ".join(parts)


class WorkoutPlanForm(forms.ModelForm):
    class Meta:
        model = WorkoutPlan
        fields = ["student", "name", "objective", "status", "start_date", "end_date", "notes"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = (
            Student.objects.filter(organization=organization).order_by("name")
            if organization else Student.objects.none()
        )


class WorkoutRoutineForm(forms.ModelForm):
    class Meta:
        model = WorkoutRoutine
        fields = ["name", "instructions"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Ex.: Treino A - Peito e Tríceps"}),
            "instructions": forms.Textarea(attrs={"rows": 2}),
        }


class WorkoutExerciseForm(forms.ModelForm):
    exercise = ExerciseChoiceField(queryset=Exercise.objects.none(), label="Exercício")

    class Meta:
        model = WorkoutExercise
        fields = [
            "exercise", "method", "group_code", "sets", "reps", "load_kg",
            "target_seconds", "rest_seconds", "cadence", "rpe_target", "rir_target",
            "progression_enabled", "progression_increment_kg", "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
            "reps": forms.TextInput(attrs={"placeholder": "Ex.: 10-12"}),
            "cadence": forms.TextInput(attrs={"placeholder": "Ex.: 3-1-2"}),
            "group_code": forms.TextInput(attrs={"placeholder": "Ex.: A1"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["exercise"].queryset = Exercise.objects.filter(
                Q(
                    organization__isnull=True,
                    publication_status=Exercise.PublicationStatus.APPROVED,
                )
                | Q(organization=organization)
            ).order_by("name_ptbr", "name")


class WorkoutScheduleForm(forms.ModelForm):
    class Meta:
        model = WorkoutSchedule
        fields = ["routine", "weekday", "time"]
        widgets = {"time": forms.TimeInput(attrs={"type": "time"})}

    def __init__(self, *args, organization=None, plan=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["routine"].queryset = (
            WorkoutRoutine.objects.filter(organization=organization, plan=plan).order_by("order")
            if organization and plan else WorkoutRoutine.objects.none()
        )


class TemplateApplyForm(forms.Form):
    students = forms.ModelMultipleChoiceField(
        label="Alunos",
        queryset=Student.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    plan_name = forms.CharField(label="Nome do plano", max_length=160, required=False)
    start_date = forms.DateField(
        label="Data de início",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, organization=None, template=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["students"].queryset = (
            Student.objects.filter(organization=organization).order_by("name")
            if organization else Student.objects.none()
        )
        if template and not self.is_bound:
            self.fields["plan_name"].initial = template.name
