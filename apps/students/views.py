from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import StudentForm
from .models import Student
from apps.organizations.permissions import org_member_required


def get_organization(request):
    if not request.organization:
        raise PermissionDenied("Usuário sem organização ativa.")
    return request.organization


@login_required
@org_member_required
def student_list(request):
    organization = get_organization(request)

    students = Student.objects.filter(
        organization=organization
    ).order_by("name")

    return render(
        request,
        "students/list.html",
        {"students": students},
    )


@login_required
@org_member_required
def student_create(request):
    organization = get_organization(request)

    if request.method == "POST":
        form = StudentForm(request.POST)

        if form.is_valid():
            student = form.save(commit=False)
            student.organization = organization
            student.save()

            return redirect("students:list")
    else:
        form = StudentForm()

    return render(
        request,
        "students/form.html",
        {"form": form},
    )


@login_required
@org_member_required
def student_edit(request):
    organization = get_organization(request)

    # Seleção do aluno vinda pela listagem.
    # O ID nunca aparece na URL.
    if request.method == "POST" and request.POST.get("select_student_id"):
        student = get_object_or_404(
            Student,
            pk=request.POST["select_student_id"],
            organization=organization,
        )

        request.session["editing_student_id"] = str(student.pk)

        return redirect("students:edit")

    student_id = request.session.get("editing_student_id")

    if not student_id:
        return redirect("students:list")

    student = get_object_or_404(
        Student,
        pk=student_id,
        organization=organization,
    )

    if request.method == "POST":
        form = StudentForm(request.POST, instance=student)

        if form.is_valid():
            form.save()

            request.session.pop("editing_student_id", None)

            return redirect("students:list")
    else:
        form = StudentForm(instance=student)

    return render(
        request,
        "students/form.html",
        {
            "form": form,
            "student": student,
        },
    )
