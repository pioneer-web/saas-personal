from functools import wraps

from django.core.exceptions import PermissionDenied

from .models import Membership


def _authorized(request, roles):
    user = getattr(request, "user", None)

    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    membership = getattr(request, "membership", None)

    return bool(
        membership
        and membership.is_active
        and membership.organization.is_active
        and membership.role in roles
    )


def roles_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not _authorized(request, roles):
                raise PermissionDenied(
                    "Você não possui permissão para esta ação."
                )
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


org_member_required = roles_required(
    Membership.Role.OWNER,
    Membership.Role.TRAINER,
    Membership.Role.STAFF,
)

trainer_or_owner_required = roles_required(
    Membership.Role.OWNER,
    Membership.Role.TRAINER,
)

owner_required = roles_required(
    Membership.Role.OWNER,
)
