# accounts/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('reset-password/', views.simple_password_reset, name='password_reset'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('student/profile/', views.student_profile, name='student_profile'),
    path('faculty/profile/', views.admin_profile, name='admin_profile'),
    path('student-history/', views.student_history, name='student_history'),
    path('manage-students/', views.manage_students, name='manage_students'),
    path('edit-student/<int:id>/', views.edit_student, name='edit_student'),
    path('delete-student/<int:id>/', views.delete_student, name='delete_student'),
    path('class-reports/', views.class_reports, name='class_reports'),
    path('session-details/<int:id>/', views.session_details, name='session_details'),

    path('export-reports/', views.export_reports_csv, name='export_reports_csv'),
    path('export-session/<int:id>/', views.export_session_csv, name='export_session_csv'),
    
    
]