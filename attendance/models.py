from django.db import models
from accounts.models import Teacher, Student

class QRSession(models.Model):
    # The secure random string generated for the QR code
    token = models.CharField(max_length=255, unique=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    created_time = models.DateTimeField(auto_now_add=True)
    expiry_time = models.DateTimeField()
    
    # High-precision decimal fields for accurate GPS tracking
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)

    def __str__(self):
        return f"Session by {self.teacher.name} on {self.created_time.strftime('%Y-%m-%d')}"

class AttendanceLog(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    session = models.ForeignKey(QRSession, on_delete=models.CASCADE)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Crucial Security Step: This strictly prevents duplicate attendance entries 
        # for the same student in the same 2-minute session window.
        unique_together = ('student', 'session')

    def __str__(self):
        return f"{self.student.name} marked present at {self.timestamp.strftime('%H:%M')}"