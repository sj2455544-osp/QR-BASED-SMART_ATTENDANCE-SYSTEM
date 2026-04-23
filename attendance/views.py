import uuid
import qrcode # type: ignore
import base64
import math
import json
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.core.mail import send_mail
from django.contrib import messages
from django.http import JsonResponse
from accounts.models import Teacher, Student, ClassSession, AttendanceRecord
import csv
from django.http import HttpResponse
from django.db.models import Count

# --- Basic Views ---
def home_view(request):
    return render(request, 'home.html')

def about_view(request):
    return render(request, 'about.html')

def contact_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        full_name = f"{first_name} {last_name}"
        subject = f"New Contact Request from {full_name}"
        email_body = f"Name: {full_name}\nEmail: {email}\n\nMessage:\n{message}"
        
        try:
            send_mail(subject, email_body, email, ['sj2455544@gmail.com'], fail_silently=False)
            messages.success(request, "Your message has been sent successfully!")
            return redirect('contact')
        except Exception as e:
            messages.error(request, "An error occurred while sending your message.")
    return render(request, 'contact.html')

# ==========================================
# 1. TEACHER VIEW: GENERATE QR / EXAM SESSION
# ==========================================
@login_required
def generate_qr_view(request):
    try:
        teacher = request.user.teacher
    except Teacher.DoesNotExist:
        messages.error(request, "Only authorized teachers can access this portal.")
        return redirect('admin_dashboard')

    if request.method == 'POST':
        # YAHAN UPDATE KIYA HAI: Agar value khali aayi, toh automatically 'ALL' le lega
        course = request.POST.get('course') or 'ALL COURSES'
        batch = request.POST.get('batch') or 'ALL BATCHES'
        
        subject = request.POST.get('subject')
        session_type = request.POST.get('session_type', 'CLASS') 
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')

        if not all([subject, lat, lng]):
            messages.error(request, "Subject and GPS location are required!")
            return render(request, 'generate_qr.html')

        now = timezone.now()
        today = now.date()

        session = ClassSession.objects.filter(
            teacher=teacher, course=course, batch=batch, subject=subject, date=today
        ).first()

        if session:
            if session.is_locked:
                delta = now - session.last_generated_at
                if delta.total_seconds() < 30 * 60:
                    remaining_min = 30 - int(delta.total_seconds() / 60)
                    messages.error(request, f"Locked! Wait {remaining_min} mins.")
                    return render(request, 'generate_qr.html')
                else:
                    session.is_locked = False
                    session.generation_count = 0 

            session.generation_count += 1
            session.qr_token = uuid.uuid4()
            session.last_generated_at = now
            session.session_type = session_type
            if session.generation_count >= 3:
                session.is_locked = True
            session.save()
        else:
            session = ClassSession.objects.create(
                teacher=teacher, course=course, batch=batch, 
                subject=subject, session_type=session_type,
                latitude=lat, longitude=lng, last_generated_at=now
            )

        students = []
        qr_base64 = None

        if session_type == 'EXAM':
            # FIX: student_id use kiya kyunki roll_number field nahi mila
            students = Student.objects.filter(course=course, batch=batch).order_by('student_id')
            messages.success(request, "Exam mode activated. Mark attendance manually.")
        else:
            scan_url = f"http://{request.get_host()}/attendance/scan/{session.qr_token}/"
            qr = qrcode.make(scan_url)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            messages.success(request, f"Session Active (Attempt {session.generation_count}/3)")

        return render(request, 'generate_qr.html', {
            'qr_image': qr_base64, 
            'session': session,
            'students': students
        })
    
    return render(request, 'generate_qr.html')

# ==========================================
# 2. DYNAMIC AJAX & FORM MANUAL MARKING
# ==========================================
@login_required
def mark_manual_attendance(request, session_id=None):
    if request.method == 'POST':
        
        # -----------------------------------------------------------
        # CONDITION 1: AJAX JSON Handling (For Live Exam Mode)
        # -----------------------------------------------------------
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                sid = session_id or data.get('session_id') 
                student_id = data.get('student_id')
                
                student = get_object_or_404(Student, id=student_id)
                session = get_object_or_404(ClassSession, id=sid)
                
                AttendanceRecord.objects.create(
                    student=student,
                    session=session,
                    is_manual=True,
                    device_id="EXAM_HALL_MANUAL",
                    device_ip=request.META.get('REMOTE_ADDR'),
                    scanned_latitude=session.latitude,
                    scanned_longitude=session.longitude
                )
                return JsonResponse({'status': 'success'})
            except IntegrityError:
                return JsonResponse({'status': 'error', 'message': 'Already marked present.'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})

        # -----------------------------------------------------------
        # CONDITION 2: Traditional Form Handling (For Session Details Modal)
        # -----------------------------------------------------------
        else:
            sid = session_id or request.POST.get('session_id')
            
            # HTML Modal mein select tag ka name ya toh 'student_db_id' hoga ya 'student_id'
            student_id = request.POST.get('student_db_id') or request.POST.get('student_id')
            
            if not student_id:
                messages.error(request, "Please select a student from the dropdown.")
                return redirect('session_details', id=sid)

            session = get_object_or_404(ClassSession, id=sid, teacher=request.user.teacher)
            student = get_object_or_404(Student, id=student_id)
            
            try:
                AttendanceRecord.objects.create(
                    student=student,
                    session=session,
                    is_manual=True,
                    device_id="MODAL_MANUAL",
                    device_ip=request.META.get('REMOTE_ADDR'),
                    scanned_latitude=session.latitude,
                    scanned_longitude=session.longitude
                )
                messages.success(request, f"Presence confirmed manually for {student.name}")
            except IntegrityError:
                messages.warning(request, f"{student.name} is already marked present!")
            
            # Redirect wapas usi Session Details page par karega
            return redirect('session_details', id=sid)

    return JsonResponse({'status': 'error', 'message': 'Invalid Request'})

# ==========================================
# 3. STUDENT SCAN VIEW
# ==========================================
@login_required
def scan_qr_view(request, token):
    import uuid # Validation ke liye zaroori hai

    try:
        student = request.user.student
    except Student.DoesNotExist:
        return render(request, 'scan_qr.html', {'error': 'Only students can mark attendance.'})

    # --- YAHAN UPDATE KIYA HAI (UUID VALIDATION) ---
    try:
        # Check karo ki token ek sahi UUID format mein hai ya nahi
        uuid.UUID(str(token))
    except ValueError:
        # Agar "dummy_token" jaisa kuch aayega toh ye block chalega
        return render(request, 'scan_qr.html', {'error': 'Invalid QR Format! Please scan a valid QR code from the classroom.'})
    # -----------------------------------------------

    try:
        session = ClassSession.objects.get(qr_token=token, is_active=True)
    except (ClassSession.DoesNotExist, ValueError):
        return render(request, 'scan_qr.html', {'error': 'Invalid or Expired QR Session!'})

    if session.session_type == 'EXAM':
        return render(request, 'scan_qr.html', {'error': 'Phones not allowed in Exams. Attendance by Teacher only.'})

    if request.method == 'POST':
        student_lat = request.POST.get('latitude')
        student_lng = request.POST.get('longitude')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        device_id = base64.b64encode(user_agent.encode()).decode()[:100]

        if not student_lat or not student_lng:
            return render(request, 'scan_qr.html', {'error': 'GPS location is required!'})

        # --- SMART EVENT/CLASS CHECK ---
        if session.course and session.course != 'ALL COURSES':
            if student.course != session.course:
                return render(request, 'scan_qr.html', {'error': f'Access Denied! Session is only for {session.course} students.'})

        if session.batch and session.batch != 'ALL BATCHES':
            if student.batch != session.batch:
                return render(request, 'scan_qr.html', {'error': f'Access Denied! Session is only for {session.batch}.'})

        R = 6371000
        phi1, phi2 = math.radians(float(session.latitude)), math.radians(float(student_lat))
        dphi = math.radians(float(student_lat) - float(session.latitude))
        dlamb = math.radians(float(student_lng) - float(session.longitude))
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlamb/2)**2
        distance = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

        if distance > 50:
            return render(request, 'scan_qr.html', {'error': f'Too far ({int(distance)}m).'})

        if AttendanceRecord.objects.filter(session=session, device_id=device_id).exclude(student=student).exists():
            return render(request, 'scan_qr.html', {'error': 'Device already used for another student.'})

        try:
            AttendanceRecord.objects.create(
                student=student, session=session, 
                scanned_latitude=student_lat, scanned_longitude=student_lng,
                device_id=device_id, device_ip=request.META.get('REMOTE_ADDR')
            )
            return render(request, 'scan_qr.html', {'success': f'Attendance marked for {session.subject}!'})
        except IntegrityError:
            return render(request, 'scan_qr.html', {'error': 'Already marked!'})

    return render(request, 'scan_qr.html', {'token': token, 'session': session, 'is_valid_token': True})

@login_required
def export_subject_detailed_report(request):
    subject = request.GET.get('subject')
    course = request.GET.get('course')
    batch = request.GET.get('batch')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # 1. Us range mein is Subject ki saari Classes (Dates) nikal lo
    sessions = ClassSession.objects.filter(
        subject=subject, course=course, batch=batch, 
        date__range=[start_date, end_date]
    ).order_by('date')

    # Dates ki list banao columns ke liye
    session_dates = [sess.date.strftime("%d-%m") for sess in sessions]

    # CSV Setup
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{subject}_{batch}_Report.csv"'
    writer = csv.writer(response)

    # Header Row: Name | ID | 01-03 | 05-03 | ... | Total %
    header = ['Student Name', 'University ID'] + session_dates + ['Total %']
    writer.writerow(header)

    # 2. Students fetch karo
    students = Student.objects.filter(course=course, batch=batch).order_by('name')

    for s in students:
        row = [s.name, s.student_id]
        present_in_sessions = 0

        for sess in sessions:
            # Check karo bacha is specific session mein present tha ya nahi
            is_present = AttendanceRecord.objects.filter(student=s, session=sess).exists()
            if is_present:
                row.append('P')
                present_in_sessions += 1
            else:
                row.append('A')

        # Percentage calculation for this specific subject
        total_classes = len(sessions)
        percent = int((present_in_sessions / total_classes) * 100) if total_classes > 0 else 0
        row.append(f"{percent}%")
        
        writer.writerow(row)

    return response