from django.urls import path

from . import api


urlpatterns = [
    path("login/", api.login_api),
    path("logout/", api.logout_api),
    path("home/", api.home_api),
    path("workout/", api.workout_api),
    path("history/", api.history_api),
    path("evolution/", api.evolution_api),
]
