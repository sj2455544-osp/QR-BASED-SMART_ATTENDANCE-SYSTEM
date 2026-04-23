from django.db import models
from django.contrib.auth.models import User
import uuid 
from django.utils import timezone

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True, null=True)
    subject = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True, null=True)
    course = models.CharField(max_length=20, blank=True, null=True)
    batch = models.CharField(max_length=20, blank=True, null=True)
    student_id = models.CharField(max_length=20, unique=True) 

    def __str__(self):
        return f"{self.name} ({self.student_id}) - {self.course} - {self.batch}"


# ==========================================
# ATTENDANCE TRACKING MODELS (ULTRA SECURE)
# ==========================================

class ClassSession(models.Model):
    # Requirement 4 & 5: Added Session Types (Class, Exam, Event)
    SESSION_TYPES = (
        ('CLASS', 'Regular Class'),
        ('EXAM', 'Examination'),
        ('EVENT', 'College Event'),
    )

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    course = models.CharField(max_length=50)   
    batch = models.CharField(max_length=20)    
    subject = models.CharField(max_length=100) 
    
    session_type = models.CharField(max_length=10, choices=SESSION_TYPES, default='CLASS')
    date = models.DateField(auto_now_add=True)
    start_time = models.TimeField(auto_now_add=True)
    
    qr_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_active = models.BooleanField(default=True) 
    
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    generation_count = models.IntegerField(default=1) 
    last_generated_at = models.DateTimeField(auto_now_add=True)
    is_locked = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.session_type}] {self.subject} - {self.date}"


class AttendanceRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    scanned_latitude = models.FloatField(null=True, blank=True)
    scanned_longitude = models.FloatField(null=True, blank=True)
    device_ip = models.GenericIPAddressField(null=True, blank=True)

    # Requirement 3: Anti-Scam (Device Fingerprint)
    # Isme hum student ke phone ki unique ID store karenge
    device_id = models.CharField(max_length=255, null=True, blank=True)

    # Requirement 1: Manual Attendance Flag
    is_manual = models.BooleanField(default=False) 
    marked_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='manual_markings')

    class Meta:
        unique_together = ('student', 'session')

    def __str__(self):
        type_str = "Manual" if self.is_manual else "QR Scan"
        return f"{self.student.name} - {self.session.subject} ({type_str})"