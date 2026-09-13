from django.urls import path

from . import views

app_name = "workouts"

urlpatterns = [
    path("", views.plan_list, name="list"),
    path("novo/", views.plan_create, name="create"),
    path("editar/", views.plan_edit, name="edit"),
    path("adicionar-treino/", views.routine_add, name="routine_add"),
    path("montar/", views.routine_builder, name="builder"),
    path("modo-aluno/", views.student_workout_preview, name="student_workout"),
    path("historico/", views.workout_history, name="history"),
    path("evolucao/", views.exercise_progress, name="progress"),
    path("modelos/", views.template_list, name="templates"),
    path("modelos/aplicar/", views.template_apply, name="template_apply"),
    path("salvar-modelo/", views.save_plan_as_template, name="save_template"),
    path("agenda/", views.schedule_manage, name="schedule"),
    path("agenda-semanal/", views.weekly_agenda, name="weekly_agenda"),
]
