import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.core.views import dashboard, health, secure_login


admin_path = (
    os.getenv("DJANGO_ADMIN_PATH", "admin")
    .strip("/")
    + "/"
)


urlpatterns = [
    path("equipe/", include("apps.organizations.urls")),
    path(
        "acessos-alunos/",
        include("apps.student_portal.trainer_urls"),
    ),
    path(
        "api/student/",
        include("apps.student_portal.api_urls"),
    ),
    path(
        "app/",
        include("apps.student_portal.urls"),
    ),
    path(
        "treinos/",
        include("apps.workouts.urls"),
    ),
    path(
        "exercicios/",
        include("apps.exercises.urls"),
    ),
    path(admin_path, admin.site.urls),
    path(
        "alunos/",
        include("apps.students.urls"),
    ),
    path("health/", health, name="health"),
    path("login/", secure_login, name="login"),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path("", dashboard, name="dashboard"),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
