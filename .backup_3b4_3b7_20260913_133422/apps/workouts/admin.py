from django.contrib import admin

from .models import (
    WorkoutExercise,
    WorkoutPlan,
    WorkoutRoutine,
)


admin.site.register(WorkoutPlan)
admin.site.register(WorkoutRoutine)
admin.site.register(WorkoutExercise)
