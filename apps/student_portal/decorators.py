from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden

from .models import StudentAccount


def student_account_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                login_url="student_portal:login",
            )

        account = (
            StudentAccount.objects
            .select_related("student", "organization", "user")
            .filter(
                user=request.user,
                user__is_active=True,
                is_active=True,
                organization__is_active=True,
            )
            .first()
        )

        if not account:
            return HttpResponseForbidden(
                "Esta conta não possui acesso ao aplicativo do aluno."
            )

        request.student_account = account
        request.student = account.student
        request.student_organization = account.organization

        return view_func(request, *args, **kwargs)

    return wrapped
