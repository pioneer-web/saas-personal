from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from apps.core.views import dashboard, health

urlpatterns = [
    path("treinos/", include("apps.workouts.urls")),
    path("exercicios/", include("apps.exercises.urls")),
    path("admin/", admin.site.urls),
    path("alunos/", include("apps.students.urls")),
    path("health/", health, name="health"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", dashboard, name="dashboard"),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
