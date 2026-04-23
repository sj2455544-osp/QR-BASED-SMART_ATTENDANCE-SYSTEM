from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Student, Teacher
from .models import Student, Teacher, ClassSession, AttendanceRecord
import re
import csv
from django.http import HttpResponse
from django.utils.timezone import localtime
from django.db import IntegrityError


def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        student_id = request.POST.get('student_id')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        course = request.POST.get('course') 
        batch = request.POST.get('batch')
        role = request.POST.get('role')
        admin_code = request.POST.get('admin_code')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not email.endswith('@cimage.in'):
            messages.error(request, "Registration allowed only with official @cimage.in email.")
            return redirect('signup')

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('signup')

        password_pattern = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$')
        if not password_pattern.match(password):
            messages.error(request, "Password must be at least 8 characters with 1 capital letter, 1 number, and 1 symbol.")
            return redirect('signup')

        phone_pattern = re.compile(r'^[6-9]\d{9}$')
        if not phone_pattern.match(phone):
            messages.error(request, "Please enter a valid 10-digit Indian phone number.")
            return redirect('signup')

        is_super_admin = False
        if role == 'admin':
            if admin_code == 'SuperAdmin@9546':
                is_super_admin = True
            elif admin_code != 'Admin@123':
                messages.error(request, "Invalid Admin Verification Code!")
                return redirect('signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return redirect('signup')
            
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect('signup')

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.first_name = username 
            
            if is_super_admin:
                user.is_staff = True
                user.is_superuser = True
                
            user.save()
            
            if role == 'student':
                Student.objects.create(user=user, name=username, student_id=student_id, phone=phone, course=course, batch=batch) 
            elif role == 'admin':
                Teacher.objects.create(user=user, name=username, phone=phone) 
                
            messages.success(request, "Account created! Please log in with your credentials.")
            return redirect('login') 
            
        except Exception as e:
            messages.error(request, f"Error: {e}")
            return redirect('signup')

    return render(request, 'signup.html')


def login_view(request):
    if request.method == 'POST':
        email_id = request.POST.get('email')
        p_pass = request.POST.get('password')

        try:
            user_obj = User.objects.get(email=email_id)
            user = authenticate(username=user_obj.username, password=p_pass)

            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name}!")
                
                if hasattr(user, 'student'):
                    return redirect('student_dashboard')
                elif hasattr(user, 'teacher'):
                    return redirect('admin_dashboard')
                else:
                    return redirect('home')
            else:
                messages.error(request, "Incorrect password. Please try again.")
        except User.DoesNotExist:
            messages.error(request, "No account found with this Email ID.")
            
        return redirect('login')

    return render(request, 'login.html')


def simple_password_reset(request):
    if request.method == 'POST':
        email_id = request.POST.get('email')
        new_pass = request.POST.get('password')
        confirm_pass = request.POST.get('confirm_password')

        if new_pass != confirm_pass:
            messages.error(request, "Passwords do not match!")
            return render(request, 'password_reset_simple.html', {'email': email_id})

        try:
            user = User.objects.get(email=email_id)
            user.password = make_password(new_pass)
            user.save()
            messages.success(request, "Password updated successfully! You can now log in.")
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, "This Email ID is not registered.")
    
    return render(request, 'password_reset_simple.html')


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')


# ==========================================
# DASHBOARD VIEWS
# ==========================================

@login_required(login_url='login')
def student_dashboard(request):
    if not hasattr(request.user, 'student'):
        return redirect('home')
        
    student = request.user.student

    # Database Calculations
    total_classes = ClassSession.objects.filter(course=student.course, batch=student.batch).count()
    present_count = AttendanceRecord.objects.filter(student=student).count()
    
    absent_count = total_classes - present_count
    if absent_count < 0:
        absent_count = 0

    if total_classes > 0:
        attendance_percentage = int((present_count / total_classes) * 100)
    else:
        attendance_percentage = 0

    # REQUIREMENT 2: 75% Alert Logic
    low_attendance_alert = attendance_percentage < 75

    recent_attendance = AttendanceRecord.objects.filter(student=student).order_by('-id')[:5]

    context = {
        'total_classes': total_classes,
        'present_count': present_count,
        'absent_count': absent_count,
        'attendance_percentage': attendance_percentage,
        'low_attendance_alert': low_attendance_alert, # New field for alert
        'recent_attendance': recent_attendance,
    }

    return render(request, 'student_dashboard.html', context)


@login_required(login_url='login')
def admin_dashboard(request):
    if not hasattr(request.user, 'teacher'):
        return redirect('home')
        
    teacher = request.user.teacher

    # 1. Total Classes
    sessions = ClassSession.objects.filter(teacher=teacher)
    total_classes = sessions.count()

    # 2. Recent Classes (Last 5)
    recent_sessions = sessions.order_by('-date')[:5]

    # 3. SMART AVERAGE ATTENDANCE CALCULATION
    total_percentage = 0
    valid_classes = 0

    for session in sessions:
        # Kitne bache present hain
        present_count = session.attendancerecord_set.count()
        # Us course+batch mein kitne bache enrolled hain
        enrolled_count = Student.objects.filter(course=session.course, batch=session.batch).count()
        
        if enrolled_count > 0:
            class_percent = (present_count / enrolled_count) * 100
            total_percentage += min(class_percent, 100) # 100 se upar na jaye
            valid_classes += 1
        elif present_count > 0:
            # Agar by chance student enrolled na dikhe par present mark ho
            total_percentage += 100
            valid_classes += 1

    # Final Average nikalna
    if valid_classes > 0:
        avg_attendance = int(total_percentage / valid_classes)
    else:
        avg_attendance = 0

    context = {
        'total_classes': total_classes,
        'avg_attendance': avg_attendance,
        'recent_sessions': recent_sessions,
        'active_qr_count': 0 # Optional, isko baad me live sessions ke liye use kar sakte hain
    }

    return render(request, 'admin_dashboard.html', context)


# ==========================================
# PROFILE VIEWS
# ==========================================

@login_required(login_url='login')
def student_profile(request):
    if not hasattr(request.user, 'student'):
        return redirect('home')
    return render(request, 'student_profile.html')


@login_required(login_url='login')
def admin_profile(request):
    if not hasattr(request.user, 'teacher'):
        return redirect('home')
    return render(request, 'admin_profile.html')


# accounts/views.py ke sabse end mein add karo:
@login_required(login_url='login')
def student_history(request):
    if not hasattr(request.user, 'student'):
        return redirect('home')
        
    student = request.user.student
    
    # Saari attendance laani hai, latest pehle dikhegi
    all_attendance = AttendanceRecord.objects.filter(student=student).order_by('-id')
    
    # Optional: Hum stats bhi bhej sakte hain agar history page pe top par dikhana ho
    total_classes = ClassSession.objects.filter(course=student.course, batch=student.batch).count()
    present_count = all_attendance.count()
    absent_count = max(total_classes - present_count, 0)
    attendance_percentage = int((present_count / total_classes) * 100) if total_classes > 0 else 0

    context = {
        'all_attendance': all_attendance,
        'total_classes': total_classes,
        'present_count': present_count,
        'absent_count': absent_count,
        'attendance_percentage': attendance_percentage,
    }
    
    return render(request, 'student_history.html', context)

@login_required(login_url='login')
def manage_students(request):
    if not hasattr(request.user, 'teacher'):
        return redirect('home')
    students = Student.objects.all().order_by('name')
    student_list = []
    # REQUIREMENT 2: Har student ka percentage nikalna
    for s in students:
        total = ClassSession.objects.filter(course=s.course, batch=s.batch).count()
        present = AttendanceRecord.objects.filter(student=s).count()
        percent = int((present/total)*100) if total > 0 else 0
        student_list.append({'data': s, 'percent': percent})

    context = {'student_list': student_list, 'total_students': students.count()}
    return render(request, 'manage_students.html', context)



@login_required(login_url='login')
def delete_student(request, id):
    if not hasattr(request.user, 'teacher'):
        return redirect('home')
        
    student = get_object_or_404(Student, id=id)
    user_to_delete = student.user
    user_to_delete.delete() # Ye user account aur student profile dono ko permanently delete kar dega
    
    messages.success(request, f"Student {student.name} removed successfully!")
    return redirect('manage_students')

@login_required(login_url='login')
def edit_student(request, id):
    if not hasattr(request.user, 'teacher'):
        return redirect('home')
        
    student = get_object_or_404(Student, id=id)

    if request.method == 'POST':
        student.name = request.POST.get('name')
        student.student_id = request.POST.get('student_id')
        student.course = request.POST.get('course')
        student.batch = request.POST.get('batch')
        student.phone = request.POST.get('phone')
        student.save()
        
        
        student.user.first_name = student.name
        student.user.save()
        
        messages.success(request, "Student details updated successfully!")
        return redirect('manage_students')

    return render(request, 'edit_student.html', {'student': student})

@login_required(login_url='login')
def class_reports(request):
    if not hasattr(request.user, 'teacher'):
        return redirect('home')
    
    # Get all sessions for this specific teacher, ordered by newest first
    class_sessions = ClassSession.objects.filter(teacher=request.user.teacher).order_by('-date', '-start_time')
    
    return render(request, 'class_reports.html', {'class_sessions': class_sessions})

@login_required(login_url='login')
def session_details(request, id):
    if not hasattr(request.user, 'teacher'):
        return redirect('home')
        
    session = get_object_or_404(ClassSession, id=id, teacher=request.user.teacher)
    attendance_records = AttendanceRecord.objects.filter(session=session).select_related('student')
    
    # REQUIREMENT 1: Manual attendance ke liye bachon ki list (SMART FILTERING)
    eligible_students = Student.objects.all()
    
    # Agar course "ALL COURSES" nahi hai, tabhi filter lagao
    if session.course and session.course != 'ALL COURSES':
        eligible_students = eligible_students.filter(course=session.course)
        
    # Agar batch "ALL BATCHES" nahi hai, tabhi filter lagao
    if session.batch and session.batch != 'ALL BATCHES':
        eligible_students = eligible_students.filter(batch=session.batch)
        
    # Name se sort kar do
    eligible_students = eligible_students.order_by('name')
    
    return render(request, 'session_details.html', {
        'session': session, 
        'attendance_records': attendance_records,
        'eligible_students': eligible_students
    })

@login_required(login_url='login')
def mark_manual_attendance(request, session_id):
    if not hasattr(request.user, 'teacher'):
        return redirect('home')
    session = get_object_or_404(ClassSession, id=session_id, teacher=request.user.teacher)
    if request.method == 'POST':
        student_db_id = request.POST.get('student_db_id')
        student = get_object_or_404(Student, id=student_db_id)
        try:
            AttendanceRecord.objects.create(
                student=student, 
                session=session, 
                is_manual=True, 
                marked_by=request.user.teacher
            )
            messages.success(request, f"Manual attendance marked for {student.name}")
        except IntegrityError:
            messages.warning(request, f"{student.name} is already present.")
    return redirect('session_details', id=session_id)

@login_required(login_url='login')
def export_reports_csv(request):
    if not hasattr(request.user, 'teacher'):
        return redirect('home')
        
    # CSV ke liye response setup
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Class_Reports.csv"'
    
    writer = csv.writer(response)
    # CSV File ki Top Heading Row
    writer.writerow(['Date', 'Time (IST)', 'Course', 'Batch', 'Subject', 'Total Students Present'])
    
    # Database se data nikalna
    sessions = ClassSession.objects.filter(teacher=request.user.teacher).order_by('-date', '-start_time')
    
    for sess in sessions:
        date_str = sess.date.strftime("%b %d, %Y") if sess.date else "N/A"
        time_str = sess.start_time.strftime("%I:%M %p") if sess.start_time else "N/A"
        present_count = sess.attendancerecord_set.count()
        
        # Har class ka data row-by-row likhna
        writer.writerow([date_str, time_str, sess.course, sess.batch, sess.subject, present_count])
        
    return response

@login_required(login_url='login')
def export_session_csv(request, id):
    if not hasattr(request.user, 'teacher'):
        return redirect('home')
        
    # Class aur uske bachhon ka data nikalna
    session = get_object_or_404(ClassSession, id=id, teacher=request.user.teacher)
    records = AttendanceRecord.objects.filter(session=session).select_related('student')
    
    # CSV file ka naam (e.g., Attendance_BCA_2026-03-24.csv)
    response = HttpResponse(content_type='text/csv')
    filename = f"Attendance_{session.course}_{session.date}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    # UPDATED: Added 'Mode' column to track Manual vs QR Scan
    writer.writerow(['Roll No / S.No', 'Student Name', 'University ID', 'Mode', 'Scan Time (IST)'])
    
    # Har student ka data loop karke likhna
    for index, record in enumerate(records, start=1):
        # Logic to check if attendance was manual or QR
        mode = "Manual" if record.is_manual else "QR Scan"
        scan_time = localtime(record.timestamp).strftime("%I:%M:%S %p")
        
        # UPDATED: Row now includes 'mode'
        writer.writerow([index, record.student.name, record.student.student_id, mode, scan_time])
        
    return response