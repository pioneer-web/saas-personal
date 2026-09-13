from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden

from .models import StudentAccount


def student_account_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                login_url="student_portal:login",
            )

        account = (
            StudentAccount.objects
            .select_related("student", "organization")
            .filter(user=request.user, is_active=True)
            .first()
        )

        if not account:
            return HttpResponseForbidden(
                "Conta sem acesso ao aplicativo do aluno."
            )

        request.student_account = account
        request.student = account.student
        request.student_organization = account.organization

        return view(request, *args, **kwargs)

    return wrapped
