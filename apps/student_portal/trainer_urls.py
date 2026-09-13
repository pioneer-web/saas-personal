from django.urls import path

from . import views

app_name = "student_access"

urlpatterns = [
    path("", views.trainer_access_list, name="list"),
    path("gerar/", views.trainer_generate_access, name="generate"),
]
