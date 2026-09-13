from django.urls import path
from . import views

app_name = "students"

urlpatterns = [
    path("", views.student_list, name="list"),
    path("novo/", views.student_create, name="create"),
    path("editar/", views.student_edit, name="edit"),
]
