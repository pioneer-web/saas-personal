from django.contrib import admin

from .models import (
    WorkoutExercise,
    WorkoutPlan,
    WorkoutRoutine,
    WorkoutSchedule,
    WorkoutSession,
    WorkoutSetLog,
    WorkoutTemplate,
    WorkoutTemplateExercise,
    WorkoutTemplateRoutine,
)

admin.site.register(WorkoutPlan)
admin.site.register(WorkoutRoutine)
admin.site.register(WorkoutExercise)
admin.site.register(WorkoutSession)
admin.site.register(WorkoutSetLog)
admin.site.register(WorkoutTemplate)
admin.site.register(WorkoutTemplateRoutine)
admin.site.register(WorkoutTemplateExercise)
admin.site.register(WorkoutSchedule)
