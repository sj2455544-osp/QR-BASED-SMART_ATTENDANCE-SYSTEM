from django.urls import path
from . import views

urlpatterns = [
    # Public Pages
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    
    
    # Secure QR Pages
    path('generate/', views.generate_qr_view, name='generate_qr'),
    path('scan/<str:token>/', views.scan_qr_view, name='scan_qr'),
    
    path('mark-manual-attendance/<int:session_id>/', views.mark_manual_attendance, name='mark_manual_attendance'),
    path('mark-manual/', views.mark_manual_attendance, name='mark_manual_attendance'),
    path('export-subject-report/', views.export_subject_detailed_report, name='export_subject_detailed_report'),
]