from django.contrib import admin

from .models import (
    StudentAccount,
    StudentApiToken,
    StudentInvitation,
    StudentNotification,
)

admin.site.register(StudentAccount)
admin.site.register(StudentInvitation)
admin.site.register(StudentApiToken)
admin.site.register(StudentNotification)
