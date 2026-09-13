from django.urls import path

from . import views

app_name = "exercises"

urlpatterns = [
    path("", views.exercise_list, name="list"),
    path("novo/", views.exercise_create, name="create"),
    path("editar/", views.exercise_edit, name="edit"),
    path(
        "personalizar/",
        views.exercise_personalize,
        name="personalize",
    ),
]
