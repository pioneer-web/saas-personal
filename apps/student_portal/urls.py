from django.urls import path

from . import views

app_name = "student_portal"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.student_login, name="login"),
    path("ativar/", views.activate, name="activate"),
    path("sair/", views.student_logout, name="logout"),
    path("treino/", views.workout, name="workout"),
    path("historico/", views.history, name="history"),
    path("evolucao/", views.progress, name="progress"),
    path("notificacoes/", views.notifications, name="notifications"),
    path("perfil/", views.profile, name="profile"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="sw"),
    path("icon.svg", views.icon, name="icon"),
]
