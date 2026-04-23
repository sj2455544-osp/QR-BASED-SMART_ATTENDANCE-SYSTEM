from django.contrib import admin
from .models import Teacher, Student, ClassSession, AttendanceRecord

admin.site.register(Teacher)
admin.site.register(Student)
admin.site.register(ClassSession)
admin.site.register(AttendanceRecord)