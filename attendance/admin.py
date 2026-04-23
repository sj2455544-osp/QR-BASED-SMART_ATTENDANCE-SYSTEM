from django.contrib import admin
from .models import QRSession, AttendanceLog

admin.site.register(QRSession)
admin.site.register(AttendanceLog)