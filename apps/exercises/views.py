from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ExerciseForm, GlobalExerciseForm
from .models import Exercise
from apps.organizations.permissions import trainer_or_owner_required


def get_organization(request):
    if not request.organization:
        raise PermissionDenied("Usuário sem organização ativa.")

    return request.organization


@login_required
@trainer_or_owner_required
def exercise_list(request):
    organization = get_organization(request)

    exercises = Exercise.objects.filter(
        Q(
            organization__isnull=True,
            publication_status=Exercise.PublicationStatus.APPROVED,
        )
        | Q(organization=organization)
    )

    search = ""

    if request.method == "POST":
        action = request.POST.get("action")
        exercise_id = request.POST.get("exercise_id")

        if action == "search":
            search = request.POST.get(
                "search", ""
            ).strip()

            if search:
                exercises = exercises.filter(
                    Q(name_ptbr__icontains=search)
                    | Q(name__icontains=search)
                    | Q(
                        primary_muscle_ptbr__icontains=search
                    )
                    | Q(
                        primary_muscle__icontains=search
                    )
                    | Q(
                        equipment_ptbr__icontains=search
                    )
                    | Q(
                        equipment__icontains=search
                    )
                )

        elif action == "edit":
            exercise = get_object_or_404(
                Exercise,
                pk=exercise_id,
            )

            if exercise.is_global:
                if not request.user.is_superuser:
                    raise PermissionDenied()
            elif (
                exercise.organization_id
                != organization.id
            ):
                raise PermissionDenied()

            request.session[
                "editing_exercise_id"
            ] = str(exercise.pk)

            return redirect("exercises:edit")

        elif action == "personalize":
            exercise = get_object_or_404(
                Exercise,
                pk=exercise_id,
                organization__isnull=True,
            )

            request.session[
                "personalizing_exercise_id"
            ] = str(exercise.pk)

            return redirect(
                "exercises:personalize"
            )

        elif action == "request_publish":
            exercise = get_object_or_404(
                Exercise,
                pk=exercise_id,
                organization=organization,
            )

            exercise.request_publication()

            return redirect("exercises:list")

    return render(
        request,
        "exercises/list.html",
        {
            "exercises": exercises,
            "search": search,
        },
    )


@login_required
@trainer_or_owner_required
def exercise_create(request):
    organization = get_organization(request)

    if request.method == "POST":
        form = ExerciseForm(request.POST)

        if form.is_valid():
            exercise = form.save(commit=False)

            exercise.organization = organization
            exercise.source_id = None
            exercise.publication_status = (
                Exercise.PublicationStatus.PRIVATE
            )

            exercise.save()

            return redirect("exercises:list")
    else:
        form = ExerciseForm()

    return render(
        request,
        "exercises/form.html",
        {
            "form": form,
            "title": "Novo exercício",
        },
    )


@login_required
@trainer_or_owner_required
def exercise_edit(request):
    organization = get_organization(request)

    exercise_id = request.session.get(
        "editing_exercise_id"
    )

    if not exercise_id:
        return redirect("exercises:list")

    exercise = get_object_or_404(
        Exercise,
        pk=exercise_id,
    )

    if exercise.is_global:
        if not request.user.is_superuser:
            raise PermissionDenied()

        form_class = GlobalExerciseForm

    else:
        if (
            exercise.organization_id
            != organization.id
        ):
            raise PermissionDenied()

        form_class = ExerciseForm

    if request.method == "POST":
        form = form_class(
            request.POST,
            instance=exercise,
        )

        if form.is_valid():
            obj = form.save(commit=False)

            # Se o personal altera o exercício,
            # qualquer aprovação anterior deixa de
            # representar essa nova versão.
            if not obj.is_global:
                obj.publication_status = (
                    Exercise.PublicationStatus.PRIVATE
                )

                obj.publication_requested_at = None
                obj.publication_reviewed_at = None
                obj.publication_reviewed_by = None
                obj.publication_rejection_reason = ""

            obj.save()

            request.session.pop(
                "editing_exercise_id",
                None,
            )

            return redirect("exercises:list")

    else:
        form = form_class(instance=exercise)

    return render(
        request,
        "exercises/form.html",
        {
            "form": form,
            "exercise": exercise,
            "title": "Editar exercício",
        },
    )


@login_required
@trainer_or_owner_required
def exercise_personalize(request):
    organization = get_organization(request)

    exercise_id = request.session.get(
        "personalizing_exercise_id"
    )

    if not exercise_id:
        return redirect("exercises:list")

    base = get_object_or_404(
        Exercise,
        pk=exercise_id,
        organization__isnull=True,
        publication_status=Exercise.PublicationStatus.APPROVED,
    )

    initial = {
        "name": base.display_name,
        "description": base.description,
        "primary_muscle":
            base.display_primary_muscle,
        "secondary_muscles":
            base.secondary_muscles_ptbr
            or base.secondary_muscles,
        "equipment": base.display_equipment,
        "body_part": base.body_part,
        "category":
            base.category_ptbr
            or base.category,
        "difficulty":
            base.display_difficulty,
        "instructions":
            base.display_instructions,
        "media_url": base.media_url,
    }

    if request.method == "POST":
        form = ExerciseForm(request.POST)

        if form.is_valid():
            exercise = form.save(commit=False)

            exercise.organization = organization
            exercise.base_exercise = base
            exercise.source_id = None
            exercise.publication_status = (
                Exercise.PublicationStatus.PRIVATE
            )

            exercise.save()

            request.session.pop(
                "personalizing_exercise_id",
                None,
            )

            return redirect("exercises:list")

    else:
        form = ExerciseForm(initial=initial)

    return render(
        request,
        "exercises/form.html",
        {
            "form": form,
            "base_exercise": base,
            "title": "Personalizar exercício",
        },
    )
