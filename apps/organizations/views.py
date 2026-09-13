from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Membership
from .permissions import owner_required


@login_required
@owner_required
def team(request):
    organization = request.organization

    memberships = (
        Membership.objects
        .filter(organization=organization)
        .select_related("user")
        .order_by("-is_active", "role", "user__name", "user__email")
    )

    if request.method == "POST":
        membership = get_object_or_404(
            Membership,
            pk=request.POST.get("membership_id"),
            organization=organization,
        )

        if membership.user_id == request.user.id:
            messages.error(
                request,
                "Você não pode alterar sua própria associação aqui.",
            )
            return redirect("organizations:team")

        action = request.POST.get("action", "")

        if action == "change_role":
            role = request.POST.get("role")
            valid_roles = {
                Membership.Role.OWNER,
                Membership.Role.TRAINER,
                Membership.Role.STAFF,
            }

            if role not in valid_roles:
                messages.error(request, "Papel inválido.")
                return redirect("organizations:team")

            if (
                membership.role == Membership.Role.OWNER
                and role != Membership.Role.OWNER
                and Membership.objects.filter(
                    organization=organization,
                    role=Membership.Role.OWNER,
                    is_active=True,
                ).count() <= 1
            ):
                messages.error(
                    request,
                    "A organização precisa manter um proprietário ativo.",
                )
                return redirect("organizations:team")

            membership.role = role
            membership.save(update_fields=["role"])
            messages.success(request, "Permissão atualizada.")

        elif action == "toggle_active":
            if (
                membership.role == Membership.Role.OWNER
                and membership.is_active
                and Membership.objects.filter(
                    organization=organization,
                    role=Membership.Role.OWNER,
                    is_active=True,
                ).count() <= 1
            ):
                messages.error(
                    request,
                    "Não é possível desativar o último proprietário.",
                )
                return redirect("organizations:team")

            membership.is_active = not membership.is_active
            membership.save(update_fields=["is_active"])
            messages.success(request, "Status atualizado.")

        return redirect("organizations:team")

    return render(
        request,
        "organizations/team.html",
        {
            "memberships": memberships,
            "roles": Membership.Role.choices,
        },
    )
