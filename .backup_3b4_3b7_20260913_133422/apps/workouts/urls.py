from django.urls import path

from . import views

app_name = "workouts"

urlpatterns = [
    path(
        "historico/",
        views.workout_history,
        name="history",
    ),
    path(
        "evolucao/",
        views.exercise_progress,
        name="progress",
    ),
    path(
        "modo-aluno/",
        views.student_workout_preview,
        name="student_workout",
    ),
    path("", views.plan_list, name="list"),
    path("novo/", views.plan_create, name="create"),
    path("editar/", views.plan_edit, name="edit"),
    path(
        "adicionar-treino/",
        views.routine_add,
        name="routine_add",
    ),
    path(
        "montar/",
        views.routine_builder,
        name="builder",
    ),
]
