 
 
from django.core.mail import EmailMultiAlternatives  
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib import messages # For displaying feedback messages
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.conf import settings

from django.db.models import Prefetch, Count, Q
from django.http import JsonResponse
import base64
import json
import numpy as np
import cv2
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.auth import authenticate, login, logout
import logging


from .models import User, Student, Lecturer, Course, Enrollment, ClassSession, Attendance, FaceEncoding
from .chat_intents import LOW_CONFIDENCE_REPLY, resolve_chat_intent

from .forms import (
    CustomUserCreationForm, StudentForm, LecturerForm, CourseForm,
    EnrollmentForm, ClassSessionForm, AttendanceForm
)
 
from .forms import AnnouncementForm  
 
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test

logger = logging.getLogger(__name__)
from django.db.models import Prefetch, Count, Q
from django.http import JsonResponse
import base64
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from datetime import timedelta
from datetime import datetime, time
from django.utils import timezone
from .models import User, Student, Lecturer, Course, Enrollment, ClassSession, Attendance, FaceEncoding
from .forms import (
    CustomUserCreationForm, StudentForm, LecturerForm, CourseForm,
    EnrollmentForm, ClassSessionForm, AttendanceForm
)

import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
import re

# --- Helper functions for user type checks ---
def is_student(user):
    return user.is_authenticated and hasattr(user, 'student_profile') and user.user_type == 'Student'

def is_lecturer(user):
    return user.is_authenticated and hasattr(user, 'lecturer_profile') and user.user_type == 'Lecturer'

def is_admin(user):
    return user.is_authenticated


def _session_has_passed(session, now_local):
    day_name_to_int = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
        'Friday': 4, 'Saturday': 5, 'Sunday': 6,
    }
    session_day_int = day_name_to_int.get(session.day_of_week)
    if session_day_int is None:
        return False

    today_int = now_local.weekday()
    if today_int > session_day_int:
        return True
    if today_int < session_day_int:
        return False
    return now_local.time() > session.end_time


def _backfill_missed_attendance(student_profile):
    now_local = timezone.localtime(timezone.now())
    enrolled_course_ids = Enrollment.objects.filter(student=student_profile).values_list('course_id', flat=True)
    sessions_qs = ClassSession.objects.filter(course__in=enrolled_course_ids).only('id', 'day_of_week', 'end_time')
    existing_session_ids = set(student_profile.attendance_records.values_list('session_id', flat=True))

    missed_records = []
    for session in sessions_qs:
        if session.id in existing_session_ids:
            continue
        if _session_has_passed(session, now_local):
            missed_records.append(
                Attendance(
                    student=student_profile,
                    session=session,
                    status='Absent',
                    date_time=now_local,
                )
            )

    if missed_records:
        Attendance.objects.bulk_create(missed_records)


# --- Basic Authentication Views ---
 


 
def custom_login_view(request):
    """
    Redirects to the appropriate dashboard based on user_type.
    The role selection from the form has been removed for a cleaner UI.
    """
    if request.method == 'POST':
        user_number = request.POST.get('user_number')
        password = request.POST.get('password')

        user = authenticate(request, username=user_number, password=password)

        if user is not None:
            # If this is the default admin account logging in for the first time, show a one-time security warning.
            show_default_admin_notice = (
                user.user_type == 'Admin'
                and user.username == 'admin'
                and user.check_password('Admin123!')
                and user.last_login is None
            )

            login(request, user)  # Log the user in

            if show_default_admin_notice:
                admin_users_url = reverse('admin_user_list')
                messages.warning(
                    request,
                    mark_safe(
                        f"Default admin credentials are <strong>admin/Admin123!</strong>. "
                        f"<a href='{admin_users_url}'>Change the password</a> immediately in production."
                    ),
                )

            # Redirect based on user_type fetched directly from the authenticated user
            if user.user_type == 'Student':
                messages.success(request, f"Welcome, {user.first_name}! You're logged in as a Student.")
                return redirect('student_dashboard')
            elif user.user_type == 'Lecturer':
                messages.success(request, f"Welcome, {user.first_name}! You're logged in as a Lecturer.")
                return redirect('lecturer_dashboard')
            elif user.user_type == 'Admin':
                return redirect('admin_dashboard')
            else:
                return redirect('home')  # Fallback for other user types

        else:
            # Authentication failed
            messages.error(request, "You could not be authenticated, please check your username/password then try again")
            return render(request, 'login.html')
    else:
        # For GET requests, just render the empty login form
        return render(request, 'login.html')

def custom_logout_view(request):
    """
    Logs out the user and redirects to the login page with a success message.
    """
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect('login')
 

# --- Home View ---
def home(request):
    """
    Renders the home page.
    """
     
    return render(request, 'home.html')


# --- Dashboard Views ---

@login_required
 
@user_passes_test(is_student, login_url='/webapp/login/')
def student_dashboard(request):
    """
    Displays the dashboard for a logged-in student.
    Fetches student-specific details, enrollments, attendance, and upcoming sessions.
    """
    student_profile = request.user.student_profile
    user_data = request.user

    # --- AI onboarding: force face enrollment on first login ---
    # If the student has not enrolled a face encoding yet, redirect them to the setup page.
    if not FaceEncoding.objects.filter(student=student_profile).exists():
        return redirect('student_face_setup')

    _backfill_missed_attendance(student_profile)

    enrolled_courses_qs = Enrollment.objects.filter(student=student_profile).select_related('course')

    subjects_data = []
    for enrollment in enrolled_courses_qs:
        course = enrollment.course
        lecturer_names = set()
        for mod in course.modules.all():
            for lec in mod.lecturers.all():
                lecturer_names.add(lec.user.get_full_name())
        lecturer_name = ", ".join(sorted(lecturer_names)) if lecturer_names else 'N/A'

        subjects_data.append({
            'id': course.course_code,
            'course_code': course.course_code,
            'course_name': course.course_name,
            'lecturer_name': lecturer_name,
        })

    attendance_records_qs = Attendance.objects.filter(
        student=student_profile
    ).select_related(
        'session__course', 'session__module'
    ).order_by('-date_time')

    attendance_records_data = []
    for record in attendance_records_qs:
        module_name = record.session.module.module_name if record.session.module else record.session.course.course_name
        module_code = record.session.module.module_code if record.session.module else record.session.course.course_code
        attendance_records_data.append({
            'module_name': module_name,
            'module_code': module_code,
            'course_name': record.session.course.course_name,
            'course_code': record.session.course.course_code,
            'date_time': record.date_time.isoformat(),
            'date_only': record.date_time.date().isoformat(),
            'status': record.status,
            'image_data_url': record.image_data.url if record.image_data else None,
            'session_id': record.session.id,
            'session_day': record.session.get_day_of_week_display(),
            'session_start_time': record.session.start_time.strftime('%H:%M'),
        })

    enrolled_course_ids = [enrollment.course.course_code for enrollment in enrolled_courses_qs]

    # Only include sessions the student is eligible for:
    # - If a session has a specific module, only include it when the student
    #   is enrolled in that module for the course.
    # - If a session has no module, include it when the student is enrolled in the course.
    student_module_ids = Enrollment.objects.filter(student=student_profile).values_list('modules', flat=True)

    class_schedule_qs = ClassSession.objects.filter(
        Q(module__isnull=True, course__course_code__in=enrolled_course_ids) |
        Q(module__in=student_module_ids)
    ).select_related(
        'course', 'lecturer__user'
    ).order_by('day_of_week', 'start_time')

    class_schedule_data = []
    for session in class_schedule_qs:
        class_schedule_data.append({
            'id': session.id,
            'course_name': session.course.course_name,
            'course_code': session.course.course_code,
            'day_of_week': session.get_day_of_week_display(),
            'start_time': session.start_time.strftime('%H:%M'),
            'end_time': session.end_time.strftime('%H:%M'),
            'room': session.room,
            'lecturer_name': session.lecturer.user.get_full_name() if session.lecturer else 'N/A',
        })

    enrollments = student_profile.enrollments.select_related('course')
    lecturer_info = []
    for enrollment in enrollments:
        course = enrollment.course
        for module in course.modules.all():
            for lecturer in module.lecturers.all():
                lecturer_info.append({
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'lecturer_name': f"{lecturer.user.first_name} {lecturer.user.last_name}",
                    'lecturer_email': lecturer.user.email,
                })

    context = {
        'student': {
            'firstName': user_data.first_name,
            'lastName': user_data.last_name,
            'email': user_data.email,
            'studentNumber': student_profile.user.username,
            'program': student_profile.program,
            'pk': user_data.pk,
        },
        'subjects': subjects_data,
        'attendance_records': attendance_records_data,
        'class_schedule': class_schedule_data,
        'lecturer_info': lecturer_info,
    }

     
    return render(request, 'students/student_dashboard.html', context)


@login_required
@user_passes_test(is_student, login_url='/webapp/login/')
def student_face_setup(request):
    """First-time face enrollment page.

    Students must enroll a face encoding before they can access the dashboard.
    """
    student_profile = request.user.student_profile

    # If already enrolled, skip setup.
    if FaceEncoding.objects.filter(student=student_profile).exists():
        return redirect('student_dashboard')

    return render(request, 'students/face_setup.html', {
        'student': student_profile,
    })

@login_required
@user_passes_test(is_lecturer, login_url='/webapp/login/')
def lecturer_dashboard(request):
    """
    Displays the dashboard for a logged-in lecturer.
    Fetches lecturer-specific details, courses taught, and class sessions.
    """
    lecturer_profile = request.user.lecturer_profile
    user_data = request.user

    lecturer_context_data = {
        'firstName': user_data.first_name,
        'lastName': user_data.last_name,
        'email': user_data.email,
        'staffNumber': user_data.username,
        'department': lecturer_profile.department,
        'pk': user_data.pk,
    }
 
    lecturer_sessions_qs = ClassSession.objects.filter(
        lecturer=lecturer_profile
    ).select_related('course').order_by('day_of_week', 'start_time')

    # --- Upcoming Session Calculation ---
    upcoming_session = None
    now = timezone.localtime(timezone.now())  # Get the current local datetime
    today_date = now.date()                    # Extract today's date
    current_day_of_week_int = today_date.weekday()  
    current_time = now.time()                 # Get the current time

    # Mapping your model's day_of_week strings to Python's weekday() integers
    day_name_to_int = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
        'Friday': 4, 'Saturday': 5, 'Sunday': 6
    }
    
    potential_upcoming_sessions = []

    for session in lecturer_sessions_qs:
        session_day_int = day_name_to_int.get(session.day_of_week)
        
        if session_day_int is not None:
            days_diff = session_day_int - current_day_of_week_int
            
            # Calculate days_ahead to the next occurrence of this session's day
            if days_diff < 0:
                # If the session's day has already passed this week (e.g., it's Thursday, session was Monday),
                # schedule for next week.
                days_ahead = days_diff + 7
            elif days_diff == 0:
                # If it's today, check if the session time has already passed.
                if session.start_time <= current_time:
                    # If time has passed or it's the current session, schedule for next week.
                    days_ahead = 7
                else:
                    # Session is today and still in the future.
                    days_ahead = 0
            else:
                # Session is on a future day this week.
                days_ahead = days_diff
            
            # Calculate the actual concrete date for this upcoming session.
            concrete_session_date = today_date + timedelta(days=days_ahead)

            potential_upcoming_sessions.append({
                'id': session.pk,
                'course': {
                    'subjectName': session.course.course_name,
                    'subjectCode': session.course.course_code,
                },
                'date': concrete_session_date,
                'time': session.start_time,
                'location': session.room,
                'day_of_week': session.day_of_week, # Include for full display if needed
            })
    
    # Sort all potential sessions by concrete date and then by time to find the very next one.
    if potential_upcoming_sessions:
        potential_upcoming_sessions.sort(key=lambda x: (x['date'], x['time']))
        upcoming_session = potential_upcoming_sessions[0] # This is the earliest upcoming session.

    # --- End Upcoming Session Calculation ---

    # --- Fetch unique courses taught by the lecturer  
    # Courses are considered "taught" if they contain modules assigned to this lecturer.
    courses_taught_qs = Course.objects.filter(modules__in=lecturer_profile.modules.all()).distinct().order_by('course_code')
    lecturer_modules_qs = lecturer_profile.modules.all().order_by('module_code')

    courses_for_dashboard_cards = []  
    for course in courses_taught_qs:
        courses_for_dashboard_cards.append({
            'subjectCode': course.course_code,
            'subjectName': course.course_name
        })
 
    enrolled_students_qs = Student.objects.filter(
        enrollments__course__in=courses_taught_qs
    ).distinct().select_related('user').prefetch_related(
        Prefetch(
            'enrollments',
            queryset=Enrollment.objects.filter(course__in=courses_taught_qs).select_related('course'),
            to_attr='lecturer_related_enrollments'
        )
    ).order_by('user__last_name', 'user__first_name')

    enrolled_students_data = []
    lecturer_module_codes = {module.module_code for module in lecturer_profile.modules.all()}
    for student in enrolled_students_qs:
        student_modules_list = []
        seen_module_codes = set()
        for enrollment in student.lecturer_related_enrollments:
            modules = list(enrollment.modules.all()) or list(enrollment.course.modules.all())
            for module in modules:
                if module.module_code not in lecturer_module_codes:
                    continue
                if module.module_code in seen_module_codes:
                    continue
                seen_module_codes.add(module.module_code)
                student_modules_list.append({
                    'moduleName': module.module_name,
                    'moduleCode': module.module_code,
                })
        enrolled_students_data.append({
            'firstName': student.user.first_name,
            'lastName': student.user.last_name,
            'studentNumber': student.user.username,
            'email': student.user.email,
            'program': student.program,
            'enrolled_modules': student_modules_list,
            'enrolled_courses': student_modules_list,
        })

    attendance_records_qs = Attendance.objects.filter(
        session__in=lecturer_sessions_qs # sessions are filtered by lecturer in the first query
    ).select_related('student__user', 'session__course', 'session__module').order_by('-date_time')

    attendance_records_data = []
    for record in attendance_records_qs:
        module_code = record.session.module.module_code if record.session.module else record.session.course.course_code
        formatted_datetime = record.date_time.strftime('%Y-%m-%d %H:%M:%S')
        attendance_records_data.append({
            'id': record.student.user.id,
            'student_firstName': record.student.user.first_name,
            'student_lastName': record.student.user.last_name,
            'student_studentNumber': record.student.user.username,
            'subjectName': record.session.course.course_name,
            'subjectCode': module_code,
            'dateAndTime': formatted_datetime,
            'date_only': record.date_time.date().isoformat(),
            'status': record.status,
            'image_data_url': record.image_data.url if record.image_data else None,
        })

    context = {
        'lecturer': lecturer_context_data,
        'courses': courses_for_dashboard_cards, # This is the list of unique courses for the cards!
        'lecturer_modules': lecturer_modules_qs,
        'enrolled_students': enrolled_students_data,
        'attendance_records': attendance_records_data,
        'upcoming_session': upcoming_session, # This is the single upcoming session
    }
    return render(request, 'lecturers/lecture_dashboard.html', context)


@login_required
@user_passes_test(is_lecturer, login_url='/webapp/login/')
def view_course_sessions(request, course_code):
    """
    Displays all class sessions for a specific course taught by the logged-in lecturer.
    Each session's next concrete upcoming date is calculated for display.
    """
    lecturer_profile = request.user.lecturer_profile
    
    # Securely get the Course object. It must exist AND be taught by the current lecturer (via module assignments).
    course = get_object_or_404(
        Course.objects.filter(
            course_code=course_code,
            modules__in=lecturer_profile.modules.all()
        ).distinct()
    )

    # Fetch all class sessions for this specific course and lecturer.
    # Order them by day of the week and then by start time for a logical display.
    course_sessions_qs = ClassSession.objects.filter(
        course=course,
        lecturer=lecturer_profile
    ).order_by('day_of_week', 'start_time')

    sessions_for_display = []
    now = timezone.localtime(timezone.now()) # Get the current local datetime
    today = now.date()                       # Extract today's date
    current_day_of_week_int = today.weekday() # Get today's weekday as an integer (0=Monday, 6=Sunday)
    current_time = now.time()                # Get the current time

    # Map the string day names from your model to Python's integer weekdays
    day_name_to_int = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
        'Friday': 4, 'Saturday': 5, 'Sunday': 6
    }
    
    for session in course_sessions_qs:
        session_day_int = day_name_to_int.get(session.day_of_week)
        
        if session_day_int is not None: # Ensure the day name is valid
            days_diff = session_day_int - current_day_of_week_int
            
            # Calculate how many days ahead the next occurrence of this session is
            if days_diff < 0:
                # If the session's day has already passed this week, it's next week
                days_ahead = days_diff + 7
            elif days_diff == 0:
                # If it's today, check if the session time has already passed
                if session.start_time <= current_time:
                    # If time has passed or it's the exact current session, schedule for next week
                    days_ahead = 7
                else:
                    # Session is today and still in the future
                    days_ahead = 0
            else:
                # Session is on a future day this week
                days_ahead = days_diff
            
            # Calculate the actual concrete date for this upcoming session instance
            upcoming_session_date = today + timedelta(days=days_ahead)

            sessions_for_display.append({
                'id': session.pk,
                'day_of_week': session.day_of_week,
                'date': upcoming_session_date,  
                'start_time': session.start_time,
                'end_time': session.end_time,
                'location': session.room,
                'course_name': course.course_name,  
                'course_code': course.course_code,  
            })
            
    # Finally, sort the prepared sessions by their calculated upcoming date, then by start time.
    sessions_for_display.sort(key=lambda x: (x['date'], x['start_time']))

    context = {
        'course': course,  # The course object for this session
        'course_sessions_list': sessions_for_display, # The list of sessions for this course
    }
    return render(request, 'lecturers/course_sessions_detail.html', context)




@login_required
@user_passes_test(is_lecturer, login_url='/webapp/login/')
def send_announcement(request):
    
    if not hasattr(request.user, 'lecturer_profile'):
        messages.error(request, "Access denied. You must be a lecturer to send announcements.")
        return redirect('lecturer_dashboard')  

    lecturer_profile = request.user.lecturer_profile
    
    # Get all courses taught by the current lecturer (via module assignments)
    lecturer_courses = Course.objects.filter(modules__in=lecturer_profile.modules.all()).distinct().order_by('course_name')
    
    
    course_choices = [('', 'All My Modules')] + \
                     [(course.course_code, f"{course.course_name} ({course.course_code})") 
                      for course in lecturer_courses]

    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        
        form.fields['course_code'].choices = course_choices 
        
        if form.is_valid():
            selected_course_code = form.cleaned_data['course_code']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            recipient_emails = set()  
            
            if selected_course_code:
                # Send to students of a specific course
                try:
                    course = lecturer_courses.get(course_code=selected_course_code)
                    
                
                    students_to_email = Student.objects.filter(enrollments__course=course).distinct() 
                    
                    for student in students_to_email:
                        if student.user and student.user.email:  
                            recipient_emails.add(student.user.email)
                except Course.DoesNotExist:
                    messages.error(request, "Selected course not found or you don't teach it.")
                    return render(request, 'lecturers/send_announcement.html', {'form': form})
            else:
                # Send to all students across all courses taught by the lecturer
                 
                students_to_email = Student.objects.filter(enrollments__course__in=lecturer_courses).distinct() # <--- FIXED THIS LINE
                
                for student in students_to_email:
                    if student.user and student.user.email:
                        recipient_emails.add(student.user.email)

            if not recipient_emails:
                messages.warning(request, "No students found to send the announcement to for the selected course(s). Please ensure students are enrolled.")
            else:
                
                html_content = render_to_string('emails/announcement_email.html', {
                    'subject': subject,
                    'message': message,
                    'lecturer_name': request.user.get_full_name() or request.user.username,
                    'course_info': selected_course_code if selected_course_code else 'All your courses'
                })
                text_content = strip_tags(html_content)  

                try:
                    sender_email = request.user.email or settings.DEFAULT_FROM_EMAIL
                    sender_name = request.user.get_full_name() or request.user.username

                    msg = EmailMultiAlternatives(
                        subject,
                        text_content,
                        f"{sender_name} <{sender_email}>",  
                        list(recipient_emails)  
                    )
                    msg.attach_alternative(html_content, "text/html")
                    msg.send()
                    messages.success(request, f"Announcement sent successfully to {len(recipient_emails)} student(s).")
                    return redirect('lecturer_dashboard')  
                except Exception as e:
                    logger.exception("Failed to send announcement email")
                    messages.error(request, "Failed to send announcement. Please verify email configuration and try again.")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = AnnouncementForm()
        
        form.fields['course_code'].choices = course_choices 

    context = {
        'form': form,
    }
    return render(request, 'lecturers/send_announcement.html', context)


WEEKDAY_INDEX = {
    'monday': 0,
    'tuesday': 1,
    'wednesday': 2,
    'thursday': 3,
    'friday': 4,
    'saturday': 5,
    'sunday': 6,
}

MONTH_INDEX = {
    'jan': 1,
    'feb': 2,
    'mar': 3,
    'apr': 4,
    'may': 5,
    'jun': 6,
    'jul': 7,
    'aug': 8,
    'sep': 9,
    'oct': 10,
    'nov': 11,
    'dec': 12,
}


def _format_course_list(courses):
    return ', '.join(courses) if courses else 'none'


def _extract_course_from_message(message, enrolled_courses):
    lower_message = message.lower()
    for course in enrolled_courses:
        course_code = course.course_code.lower()
        course_name = course.course_name.lower()
        if course_code in lower_message or course_name in lower_message:
            return course

    if len(enrolled_courses) == 1:
        return enrolled_courses[0]

    code_like_match = re.search(r'\b([a-z]{2,}\d{2,}[a-z\d]*)\b', lower_message)
    if code_like_match:
        requested_code = code_like_match.group(1)
        for course in enrolled_courses:
            if course.course_code.lower() == requested_code:
                return course

    return None


def _extract_module_from_message(message, modules):
    lower_message = message.lower()
    message_tokens = set(re.findall(r'[a-z0-9]+', lower_message))
    for module in modules:
        module_code = module.module_code.lower()
        module_name = module.module_name.lower()
        if module_code in lower_message or module_name in lower_message:
            return module

        module_tokens = set(re.findall(r'[a-z0-9]+', module_name))
        if module_tokens and module_tokens & message_tokens:
            return module

    if len(modules) == 1:
        return modules[0]

    code_like_match = re.search(r'\b([a-z]{2,}\d{2,}[a-z\d]*)\b', lower_message)
    if code_like_match:
        requested_code = code_like_match.group(1)
        for module in modules:
            if module.module_code.lower() == requested_code:
                return module

    return None


def _student_module_attendance_rows(student_profile):
    enrollments = (
        Enrollment.objects.filter(student=student_profile)
        .select_related('course')
        .prefetch_related('modules')
    )

    rows = {}
    for enrollment in enrollments:
        modules = list(enrollment.modules.all()) or list(enrollment.course.modules.all())
        if not modules:
            modules = [None]

        for module in modules:
            if module is None:
                row_key = enrollment.course.course_code
                module_code = enrollment.course.course_code
                module_name = enrollment.course.course_name
                sessions_qs = ClassSession.objects.filter(course=enrollment.course, module__isnull=True)
            else:
                row_key = module.module_code
                module_code = module.module_code
                module_name = module.module_name
                sessions_qs = ClassSession.objects.filter(course=enrollment.course).filter(
                    Q(module=module) | Q(module__isnull=True)
                )

            total_sessions = sessions_qs.count()
            if total_sessions == 0:
                continue

            attended_sessions = Attendance.objects.filter(
                student=student_profile,
                session__in=sessions_qs,
                status__in=['Present', 'Late'],
            ).count()
            absent_sessions = Attendance.objects.filter(
                student=student_profile,
                session__in=sessions_qs,
                status='Absent',
            ).count()

            row = rows.setdefault(row_key, {
                'module_code': module_code,
                'module_name': module_name,
                'attendance_rate': 0,
                'attended_sessions': 0,
                'absent_sessions': 0,
                'total_sessions': 0,
                'course_codes': set(),
                'course_names': set(),
            })

            row['attended_sessions'] += attended_sessions
            row['absent_sessions'] += absent_sessions
            row['total_sessions'] += total_sessions
            row['course_codes'].add(enrollment.course.course_code)
            row['course_names'].add(enrollment.course.course_name)

    finalized_rows = []
    for row in rows.values():
        total_sessions = row['total_sessions']
        attendance_rate = (row['attended_sessions'] / total_sessions) * 100 if total_sessions else 0
        finalized_rows.append({
            'module_code': row['module_code'],
            'module_name': row['module_name'],
            'attendance_rate': attendance_rate,
            'attended_sessions': row['attended_sessions'],
            'absent_sessions': row['absent_sessions'],
            'total_sessions': total_sessions,
            'course_codes': sorted(row['course_codes']),
            'course_names': sorted(row['course_names']),
        })

    return sorted(finalized_rows, key=lambda row: (row['module_code'], row['module_name']))


def _lecturer_module_attendance_rows(lecturer_profile):
    rows = []
    for module in lecturer_profile.modules.all().order_by('module_code'):
        sessions_qs = ClassSession.objects.filter(lecturer=lecturer_profile).filter(
            Q(module=module) | Q(module__isnull=True, course__modules=module)
        )
        total_sessions = sessions_qs.count()
        if total_sessions == 0:
            continue

        attended_sessions = Attendance.objects.filter(
            session__in=sessions_qs,
            status__in=['Present', 'Late'],
        ).count()
        absent_sessions = Attendance.objects.filter(
            session__in=sessions_qs,
            status='Absent',
        ).count()
        attendance_rate = (attended_sessions / total_sessions) * 100 if total_sessions else 0
        rows.append({
            'module_code': module.module_code,
            'module_name': module.module_name,
            'attendance_rate': attendance_rate,
            'attended_sessions': attended_sessions,
            'absent_sessions': absent_sessions,
            'total_sessions': total_sessions,
        })

    return sorted(rows, key=lambda row: (row['module_code'], row['module_name']))


def _lecturer_todays_attendance_summary(lecturer_profile):
    today = timezone.localdate()
    records_qs = Attendance.objects.filter(
        session__lecturer=lecturer_profile,
        date_time__date=today,
    ).select_related('student__user', 'session__course', 'session__module')

    records = list(records_qs)
    unique_student_ids = {record.student.user_id for record in records}
    sessions_count = len({record.session_id for record in records})
    present_count = sum(1 for record in records if record.status == 'Present')
    late_count = sum(1 for record in records if record.status == 'Late')
    absent_count = sum(1 for record in records if record.status == 'Absent')

    return {
        'date': today,
        'records': records,
        'students_count': len(unique_student_ids),
        'sessions_count': sessions_count,
        'present_count': present_count,
        'late_count': late_count,
        'absent_count': absent_count,
    }


def _lecturer_students_at_risk(lecturer_profile, limit=10):
    taught_courses = Course.objects.filter(modules__in=lecturer_profile.modules.all()).distinct()
    taught_course_ids = list(taught_courses.values_list('course_code', flat=True))

    risk_rows = []
    students = Student.objects.filter(enrollments__course__course_code__in=taught_course_ids).distinct()
    for student in students:
        module_rows = _student_exam_module_rows(student, course_ids=taught_course_ids)
        if not module_rows:
            continue

        below_threshold_rows = [row for row in module_rows if not row['qualifies']]
        if not below_threshold_rows:
            continue

        lowest_row = min(module_rows, key=lambda row: row['attendance_rate'])
        risk_rows.append({
            'student_name': student.user.get_full_name().strip() or student.user.username,
            'student_number': student.user.username,
            'lowest_module': lowest_row['module_name'],
            'lowest_rate': lowest_row['attendance_rate'],
            'below_threshold_count': len(below_threshold_rows),
        })

    risk_rows.sort(key=lambda row: (row['lowest_rate'], row['below_threshold_count'], row['student_name']))
    return risk_rows[:limit]


def _lecturer_best_attendance_class(lecturer_profile):
    sessions_qs = ClassSession.objects.filter(lecturer=lecturer_profile).select_related('course', 'module')
    best_session = None
    best_rate = -1.0

    for session in sessions_qs:
        records_qs = Attendance.objects.filter(session=session)
        total_records = records_qs.count()
        if total_records == 0:
            continue

        attended_records = records_qs.filter(status__in=['Present', 'Late']).count()
        attendance_rate = (attended_records / total_records) * 100 if total_records else 0
        if attendance_rate > best_rate:
            best_rate = attendance_rate
            best_session = session

    if best_session is None:
        return None

    return {
        'course_code': best_session.course.course_code,
        'course_name': best_session.course.course_name,
        'module_code': best_session.module.module_code if best_session.module else best_session.course.course_code,
        'module_name': best_session.module.module_name if best_session.module else best_session.course.course_name,
        'day_of_week': best_session.day_of_week,
        'start_time': best_session.start_time.strftime('%H:%M'),
        'end_time': best_session.end_time.strftime('%H:%M'),
        'room': best_session.room,
        'attendance_rate': best_rate,
    }


def _parse_attendance_date(message):
    lower_message = message.lower()
    current_year = timezone.localdate().year
    patterns = (
        r'\b(?:on\s+)?(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month>[a-z]+)(?:\s+(?P<year>\d{4}))?\b',
        r'\b(?:on\s+)?(?P<month>[a-z]+)\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?(?:\s+(?P<year>\d{4}))?\b',
    )

    for pattern in patterns:
        match = re.search(pattern, lower_message)
        if not match:
            continue

        month_name = (match.group('month') or '')[:3]
        month = MONTH_INDEX.get(month_name)
        if not month:
            continue

        day = int(match.group('day'))
        year = int(match.group('year') or current_year)

        try:
            return datetime(year, month, day).date()
        except ValueError:
            return None

    return None


def _lecturer_most_absent_students(lecturer_profile, limit=10):
    absent_rows = (
        Attendance.objects.filter(session__lecturer=lecturer_profile, status='Absent')
        .values('student__user__first_name', 'student__user__last_name', 'student__user__username')
        .annotate(absent_count=Count('id'))
        .order_by('-absent_count', 'student__user__first_name', 'student__user__last_name')[:limit]
    )

    if not absent_rows:
        return 'I could not find any absent records for your students yet.'

    lines = []
    for row in absent_rows:
        first_name = (row.get('student__user__first_name') or '').strip()
        last_name = (row.get('student__user__last_name') or '').strip()
        username = (row.get('student__user__username') or '').strip()
        full_name = f'{first_name} {last_name}'.strip() or username or 'Unknown student'
        lines.append(f'{full_name} - absent {row["absent_count"]} times')

    return 'Students with the most absent records:\n' + '\n'.join(lines)


def _student_presence_on_date(student_profile, target_date):
    attendance_qs = Attendance.objects.filter(student=student_profile, date_time__date=target_date)
    statuses = list(attendance_qs.values_list('status', flat=True))

    if 'Present' in statuses:
        return 'Yes'
    if 'Late' in statuses:
        return 'Yes, but you were marked as Late'
    return 'No'


def _get_next_session(sessions):
    now = timezone.localtime()
    today_index = now.weekday()
    current_time = now.time()

    def sort_key(session):
        session_day_index = WEEKDAY_INDEX.get(session.day_of_week.lower(), 7)
        day_delta = (session_day_index - today_index) % 7
        if day_delta == 0 and session.start_time <= current_time:
            day_delta = 7
        return (day_delta, session.start_time)

    upcoming_sessions = sorted(sessions, key=sort_key)
    return upcoming_sessions[0] if upcoming_sessions else None


EXAM_ATTENDANCE_THRESHOLD = 80.0


def _student_exam_module_rows(student_profile, course_ids=None):
    enrollments = Enrollment.objects.filter(student=student_profile).select_related('course').prefetch_related('modules')
    if course_ids is not None:
        enrollments = enrollments.filter(course_id__in=course_ids)

    module_rows = []
    for enrollment in enrollments:
        modules = list(enrollment.modules.all())
        if not modules:
            modules = list(enrollment.course.modules.all())

        if modules:
            for module in modules:
                sessions_qs = ClassSession.objects.filter(course=enrollment.course).filter(
                    Q(module=module) | Q(module__isnull=True)
                )
                total_sessions = sessions_qs.count()
                if total_sessions == 0:
                    continue

                attended_sessions = Attendance.objects.filter(
                    student=student_profile,
                    session__in=sessions_qs,
                    status__in=['Present', 'Late'],
                ).count()

                attendance_rate = (attended_sessions / total_sessions) * 100 if total_sessions else 0
                module_rows.append({
                    'course_code': enrollment.course.course_code,
                    'course_name': enrollment.course.course_name,
                    'module_code': module.module_code,
                    'module_name': module.module_name,
                    'attended_sessions': attended_sessions,
                    'total_sessions': total_sessions,
                    'attendance_rate': attendance_rate,
                    'qualifies': attendance_rate >= EXAM_ATTENDANCE_THRESHOLD,
                })
        else:
            sessions_qs = ClassSession.objects.filter(course=enrollment.course, module__isnull=True)
            total_sessions = sessions_qs.count()
            if total_sessions == 0:
                continue

            attended_sessions = Attendance.objects.filter(
                student=student_profile,
                session__in=sessions_qs,
                status__in=['Present', 'Late'],
            ).count()

            attendance_rate = (attended_sessions / total_sessions) * 100 if total_sessions else 0
            module_rows.append({
                'course_code': enrollment.course.course_code,
                'course_name': enrollment.course.course_name,
                'module_code': enrollment.course.course_code,
                'module_name': enrollment.course.course_name,
                'attended_sessions': attended_sessions,
                'total_sessions': total_sessions,
                'attendance_rate': attendance_rate,
                'qualifies': attendance_rate >= EXAM_ATTENDANCE_THRESHOLD,
            })

    return module_rows


def _student_attendance_summary(student_profile):
    attendance_qs = Attendance.objects.filter(student=student_profile)
    total_sessions = attendance_qs.count()
    present_count = attendance_qs.filter(status='Present').count()
    late_count = attendance_qs.filter(status='Late').count()
    absent_count = attendance_qs.filter(status='Absent').count()
    attended_count = present_count + late_count
    attendance_rate = (attended_count / total_sessions) * 100 if total_sessions else 0

    return {
        'total_sessions': total_sessions,
        'present_count': present_count,
        'late_count': late_count,
        'absent_count': absent_count,
        'attended_count': attended_count,
        'attendance_rate': attendance_rate,
    }


def _student_absent_records(student_profile):
    return (
        Attendance.objects.filter(student=student_profile, status='Absent')
        .select_related('session__course', 'session__module')
        .order_by('date_time')
    )


def _lecturer_qualified_student_count(lecturer_profile):
    taught_courses = Course.objects.filter(modules__in=lecturer_profile.modules.all()).distinct()
    taught_course_ids = list(taught_courses.values_list('course_code', flat=True))

    qualified_students = []
    students = Student.objects.filter(enrollments__course__course_code__in=taught_course_ids).distinct()
    for student in students:
        module_rows = _student_exam_module_rows(student, course_ids=taught_course_ids)
        if any(row['qualifies'] for row in module_rows):
            qualified_students.append(student)

    return {
        'qualified_student_count': len(qualified_students),
        'qualified_students': qualified_students,
        'taught_courses': taught_courses,
    }


def ai_chat(request):
    """Simple AI helper endpoint for UI chat widget.

    This is a lightweight assistant and not intended to replace a full AI service.
    """
    # Accept JSON payload
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
        message = (payload.get('message') or '').strip()
    except Exception:
        return JsonResponse({'error': 'Invalid request payload.'}, status=400)

    if not message:
        return JsonResponse({'reply': 'Please type a question or message so I can assist you.'})

    user = request.user if request.user.is_authenticated else None
    is_student_user = bool(user and hasattr(user, 'student_profile'))
    is_lecturer_user = bool(user and hasattr(user, 'lecturer_profile'))
    intent_role = 'lecturer' if is_lecturer_user else 'student' if is_student_user else 'anonymous'
    intent_match = resolve_chat_intent(message, intent_role)
    intent_name = intent_match.intent
    intent_confidence = round(intent_match.confidence, 3)

    if not request.user.is_authenticated:
        lower = message.lower()
        if 'login' in lower or 'sign in' in lower:
            return JsonResponse({'reply': 'Use your student number and password to log in. If you forgot your password, use the login page reset option.', 'intent': None, 'confidence': intent_confidence})
        return JsonResponse({'reply': 'Please log in so I can answer personal questions about attendance and exam eligibility.', 'intent': None, 'confidence': intent_confidence})

    if intent_name is None:
        return JsonResponse({'reply': LOW_CONFIDENCE_REPLY, 'intent': None, 'confidence': intent_confidence})

    if is_lecturer_user:
        lecturer_profile = request.user.lecturer_profile
        if intent_name == 'students_most_absent':
            reply = _lecturer_most_absent_students(lecturer_profile)
        elif intent_name == 'students_qualify_exam':
            result = _lecturer_qualified_student_count(lecturer_profile)
            qualified_students = result['qualified_students']
            course_count = result['taught_courses'].count()
            if not qualified_students:
                reply = (
                    f'No students currently qualify for exam across the {course_count} module(s) you teach. '
                    f'A student must reach at least {EXAM_ATTENDANCE_THRESHOLD:.0f}% attendance.'
                )
            else:
                student_names = [f'{student.user.first_name} {student.user.last_name}'.strip() or student.user.username for student in qualified_students]
                reply = (
                    f'{len(qualified_students)} student(s) currently qualify for exam across your taught modules: '
                    f'{_format_course_list(student_names)}. '
                    f'The qualification rule is at least {EXAM_ATTENDANCE_THRESHOLD:.0f}% attendance.'
                )
        elif intent_name == 'exam_qualification_count':
            result = _lecturer_qualified_student_count(lecturer_profile)
            count = result['qualified_student_count']
            course_count = result['taught_courses'].count()
            if count == 0:
                reply = (
                    f'No students currently qualify for exam across the {course_count} module(s) you teach. '
                    f'A student must reach at least {EXAM_ATTENDANCE_THRESHOLD:.0f}% attendance.'
                )
            else:
                reply = (
                    f'{count} student(s) currently qualify for exam across your taught modules. '
                    f'The qualification rule is at least {EXAM_ATTENDANCE_THRESHOLD:.0f}% attendance.'
                )
        elif intent_name == 'module_lowest_attendance':
            module_rows = _lecturer_module_attendance_rows(lecturer_profile)
            if not module_rows:
                reply = 'I could not find enough attendance records to rank your modules yet.'
            else:
                lowest_row = min(module_rows, key=lambda row: row['attendance_rate'])
                reply = (
                    f"The module with the lowest attendance is {lowest_row['module_name']} ({lowest_row['module_code']}) at "
                    f"{lowest_row['attendance_rate']:.1f}%."
                )
        elif intent_name == 'module_highest_attendance':
            module_rows = _lecturer_module_attendance_rows(lecturer_profile)
            if not module_rows:
                reply = 'I could not find enough attendance records to rank your modules yet.'
            else:
                highest_row = max(module_rows, key=lambda row: row['attendance_rate'])
                reply = (
                    f"The module with the highest attendance is {highest_row['module_name']} ({highest_row['module_code']}) at "
                    f"{highest_row['attendance_rate']:.1f}%."
                )
        elif intent_name == 'todays_attendance_summary':
            summary = _lecturer_todays_attendance_summary(lecturer_profile)
            if summary['sessions_count'] == 0:
                reply = 'No attendance has been recorded today yet.'
            else:
                reply = (
                    f"Today you have attendance recorded for {summary['students_count']} student(s) across {summary['sessions_count']} session(s): "
                    f"{summary['present_count']} Present, {summary['late_count']} Late, and {summary['absent_count']} Absent."
                )
        elif intent_name == 'students_at_risk_exam':
            risk_rows = _lecturer_students_at_risk(lecturer_profile)
            if not risk_rows:
                reply = 'No students are currently at risk of not qualifying based on the attendance records I have.'
            else:
                lines = [
                    f"{row['student_name']} ({row['student_number']}): lowest module {row['lowest_module']} at {row['lowest_rate']:.1f}%"
                    for row in risk_rows
                ]
                reply = 'Students at risk of not qualifying:\n' + '\n'.join(lines)
        elif intent_name == 'absent_today_count':
            summary = _lecturer_todays_attendance_summary(lecturer_profile)
            if summary['absent_count'] == 0:
                reply = 'No students were marked absent today.'
            else:
                reply = f"{summary['absent_count']} student(s) were marked absent today across {summary['sessions_count']} session(s)."
        elif intent_name == 'attendance_statistics_for_module':
            module = _extract_module_from_message(message, list(lecturer_profile.modules.all()))
            if not module:
                reply = 'Please mention the module name or code so I can show its attendance statistics.'
            else:
                module_rows = _lecturer_module_attendance_rows(lecturer_profile)
                matched_row = next((row for row in module_rows if row['module_code'].lower() == module.module_code.lower()), None)
                if not matched_row:
                    reply = f'I could not find enough attendance records for {module.module_name} yet.'
                else:
                    reply = (
                        f"Attendance statistics for {matched_row['module_name']} ({matched_row['module_code']}): "
                        f"{matched_row['attended_sessions']} attended, {matched_row['absent_sessions']} absent, "
                        f"{matched_row['total_sessions']} total session record(s), {matched_row['attendance_rate']:.1f}% attendance."
                    )
        elif intent_name == 'best_attendance_class':
            best_class = _lecturer_best_attendance_class(lecturer_profile)
            if not best_class:
                reply = 'I could not find enough attendance records to compare classes yet.'
            else:
                reply = (
                    f"The best attended class is {best_class['course_code']} - {best_class['course_name']} "
                    f"({best_class['module_name']}) on {best_class['day_of_week']} from {best_class['start_time']} to {best_class['end_time']} "
                    f"in {best_class['room']} with {best_class['attendance_rate']:.1f}% attendance."
                )
        elif intent_name == 'taught_modules':
            taught_courses = Course.objects.filter(modules__in=lecturer_profile.modules.all()).distinct().order_by('course_code')
            if taught_courses:
                module_names = [f'{course.course_code} - {course.course_name}' for course in taught_courses]
                reply = f'You teach {_format_course_list(module_names)}.'
            else:
                reply = 'You are not assigned to any modules yet.'
        elif intent_name == 'greeting':
            reply = f"Hello {request.user.first_name}! Ask me about your taught modules, exam eligibility, and student qualification counts."
        else:
            reply = 'I can answer questions about your taught modules, exam eligibility, and student qualification counts.'
        return JsonResponse({'reply': reply, 'intent': intent_name, 'confidence': intent_confidence})

    if not is_student_user:
        return JsonResponse({'reply': 'Please log in as a student or lecturer so I can answer attendance and exam-eligibility questions.', 'intent': None, 'confidence': intent_confidence})

    student_profile = request.user.student_profile
    enrolled_courses_qs = Enrollment.objects.filter(student=student_profile).select_related('course').order_by('course__course_code')
    enrolled_courses = [enrollment.course for enrollment in enrolled_courses_qs]
    enrolled_course_codes = [course.course_code for course in enrolled_courses]
    lower = message.lower()
    attendance_date = _parse_attendance_date(message)
    module_rows = _student_module_attendance_rows(student_profile)

    if intent_name == 'next_session':
        schedule_qs = ClassSession.objects.filter(course__in=enrolled_courses).select_related('course', 'lecturer__user')
        next_session = _get_next_session(list(schedule_qs))
        if next_session:
            lecturer_name = next_session.lecturer.user.get_full_name() if next_session.lecturer else 'N/A'
            reply = (
                f"Your next session is {next_session.course.course_code} - {next_session.course.course_name}. "
                f"It is on {next_session.day_of_week} from {next_session.start_time.strftime('%H:%M')} to {next_session.end_time.strftime('%H:%M')} "
                f"in {next_session.room} with {lecturer_name}."
            )
        else:
            reply = 'I could not find any upcoming sessions for your enrolled courses.'
    elif intent_name == 'absent_count':
        _backfill_missed_attendance(student_profile)
        summary = _student_attendance_summary(student_profile)
        absent_records = list(_student_absent_records(student_profile))
        if not absent_records:
            reply = 'You do not have any absent records yet.'
        else:
            lines = []
            for record in absent_records:
                module_name = record.session.module.module_name if record.session.module else record.session.course.course_name
                module_code = record.session.module.module_code if record.session.module else record.session.course.course_code
                lines.append(
                    f"{record.date_time.strftime('%A %d %b %Y')} - {module_name} ({module_code}) in {record.session.room}"
                )
            reply = (
                f'You have {summary["absent_count"]} absent record(s). '
                f'You were absent on:\n' + '\n'.join(lines)
            )
    elif intent_name == 'present_count':
        _backfill_missed_attendance(student_profile)
        summary = _student_attendance_summary(student_profile)
        reply = f'You have {summary["present_count"]} present record(s).'
    elif intent_name == 'late_count':
        _backfill_missed_attendance(student_profile)
        summary = _student_attendance_summary(student_profile)
        reply = f'You have {summary["late_count"]} late record(s).'
    elif intent_name == 'attendance_percentage':
        _backfill_missed_attendance(student_profile)
        summary = _student_attendance_summary(student_profile)
        if summary['total_sessions'] == 0:
            reply = 'You do not have any attendance records yet.'
        else:
            reply = (
                f'Your attendance rate is {summary["attendance_rate"]:.1f}% across {summary["total_sessions"]} recorded sessions. '
                f'You need at least {EXAM_ATTENDANCE_THRESHOLD:.0f}% attendance to qualify for exams.'
            )
    elif intent_name == 'attendance_summary':
        _backfill_missed_attendance(student_profile)
        summary = _student_attendance_summary(student_profile)
        if summary['total_sessions'] == 0:
            reply = 'You do not have any attendance records yet.'
        else:
            percentage = summary['attendance_rate']
            reply = (
                f"You have {summary['present_count']} Present, {summary['late_count']} Late, and {summary['absent_count']} Absent records. "
                f"That is {percentage:.1f}% attendance across {summary['total_sessions']} recorded sessions. "
                f"You need at least {EXAM_ATTENDANCE_THRESHOLD:.0f}% attendance to qualify for exams."
            )
    elif intent_name == 'attendance_by_module':
        if not module_rows:
            reply = 'You do not have enough attendance records yet to break down attendance by module.'
        else:
            lines = []
            for row in module_rows:
                course_note = f" - {', '.join(row['course_codes'])}" if row['course_codes'] else ''
                lines.append(
                    f"{row['module_name']} ({row['module_code']}): {row['attended_sessions']}/{row['total_sessions']} attended "
                    f"({row['attendance_rate']:.1f}%){course_note}"
                )
            reply = 'Your attendance by module:\n' + '\n'.join(lines)
    elif intent_name in {'module_lowest_attendance', 'module_highest_attendance'}:
        if not module_rows:
            reply = 'You do not have enough attendance records yet to compare your modules.'
        else:
            selected_row = min(module_rows, key=lambda row: row['attendance_rate']) if intent_name == 'module_lowest_attendance' else max(module_rows, key=lambda row: row['attendance_rate'])
            relation = 'lowest' if intent_name == 'module_lowest_attendance' else 'highest'
            course_note = f" across {', '.join(selected_row['course_codes'])}" if selected_row['course_codes'] else ''
            if intent_name == 'module_lowest_attendance':
                reply = (
                    f"The module you need to improve attendance in is {selected_row['module_name']} ({selected_row['module_code']}) "
                    f"at {selected_row['attendance_rate']:.1f}%{course_note}."
                )
            else:
                reply = (
                    f"Your highest attendance is in {selected_row['module_name']} ({selected_row['module_code']}) "
                    f"at {selected_row['attendance_rate']:.1f}%{course_note}."
                )
    elif intent_name == 'attendance_this_month':
        today = timezone.localdate()
        attended_this_month = Attendance.objects.filter(
            student=student_profile,
            date_time__year=today.year,
            date_time__month=today.month,
            status__in=['Present', 'Late'],
        ).count()
        if attended_this_month == 0:
            reply = 'You have not attended any classes this month yet.'
        else:
            reply = f'You have attended {attended_this_month} class record(s) this month.'
    elif intent_name == 'missed_classes_this_week':
        start_of_week = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        end_of_week = start_of_week + timedelta(days=6)
        missed_records = Attendance.objects.filter(
            student=student_profile,
            date_time__date__gte=start_of_week,
            date_time__date__lte=end_of_week,
            status='Absent',
        ).select_related('session__course', 'session__module').order_by('date_time')

        if not missed_records:
            reply = 'You did not miss any classes this week.'
        else:
            lines = []
            for record in missed_records:
                module_name = record.session.module.module_name if record.session.module else record.session.course.course_name
                module_code = record.session.module.module_code if record.session.module else record.session.course.course_code
                lines.append(
                    f"{record.date_time.strftime('%A %d %b')} - {module_name} ({module_code}) in {record.session.room}"
                )
            reply = 'You missed these classes this week:\n' + '\n'.join(lines)
    elif intent_name == 'exam_qualification_count':
        _backfill_missed_attendance(student_profile)
        module_rows = _student_exam_module_rows(student_profile)
        qualifying_rows = [row for row in module_rows if row['qualifies']]
        if not module_rows:
            reply = 'I could not find enough attendance records to calculate exam eligibility yet.'
        elif not qualifying_rows:
            lowest_row = min(module_rows, key=lambda row: row['attendance_rate'])
            reply = (
                f'No, you do not currently qualify for exams. '
                f'Your lowest attendance is {lowest_row["module_name"]} ({lowest_row["module_code"]}) at {lowest_row["attendance_rate"]:.1f}%. '
                f'A student must reach at least {EXAM_ATTENDANCE_THRESHOLD:.0f}% attendance in a module to qualify.'
            )
        else:
            module_list = ', '.join(f"{row['module_code']} ({row['attendance_rate']:.1f}%)" for row in qualifying_rows)
            reply = (
                f'Yes, you qualify for exams in {len(qualifying_rows)} module(s): {module_list}. '
                f'The qualification rule is at least {EXAM_ATTENDANCE_THRESHOLD:.0f}% attendance.'
            )
    elif intent_name == 'enrolled_courses':
        if enrolled_course_codes:
            reply = f"You are enrolled in {_format_course_list(enrolled_course_codes)}."
        else:
            reply = 'You are not enrolled in any courses yet.'
    elif intent_name == 'lecturer_for_course':
        matched_course = _extract_course_from_message(message, enrolled_courses)
        if matched_course:
            lecturer_names = set()
            lecturer_emails = set()
            for module in matched_course.modules.all():
                for lecturer in module.lecturers.all():
                    lecturer_names.add(lecturer.user.get_full_name())
                    if lecturer.user.email:
                        lecturer_emails.add(lecturer.user.email)

            if lecturer_names:
                reply = f"The lecturer for {matched_course.course_code} - {matched_course.course_name} is {', '.join(sorted(lecturer_names))}."
                if lecturer_emails:
                    reply += f" Email: {', '.join(sorted(lecturer_emails))}."
            else:
                reply = f"I could not find a lecturer assigned to {matched_course.course_code} - {matched_course.course_name}."
        else:
            reply = 'Please mention the course code or course name so I can find the lecturer for you.'
    elif intent_name == 'attendance_on_specific_date':
        if attendance_date:
            status = _student_presence_on_date(student_profile, attendance_date)
            display_date = attendance_date.strftime('%d %B %Y').lstrip('0')
            if 'late' in lower:
                reply = f'You were marked as late on {display_date}.' if status == 'Yes, but you were marked as Late' else f'You were not marked as late on {display_date}.'
            elif 'absent' in lower:
                reply = f'You were absent on {display_date}.' if status == 'No' else f'You were not absent on {display_date}.'
            else:
                if status == 'Yes':
                    reply = f'Yes, you were present on {display_date}.'
                elif status == 'Yes, but you were marked as Late':
                    reply = f'You attended on {display_date}, but you were marked as late.'
                else:
                    reply = f'You were absent on {display_date}.'
        else:
            reply = 'Please mention a specific date like 9 May so I can check your attendance.'
    elif intent_name == 'greeting':
        reply = f"Hello {request.user.first_name}! Ask me about your next session, attendance counts, exam eligibility, enrolled courses, or lecturer."
    else:
        reply = 'I can answer student-specific questions about your next session, attendance counts, exam eligibility, enrolled courses, and lecturers.'

    return JsonResponse({'reply': reply, 'intent': intent_name, 'confidence': intent_confidence})


# --- Registration Views ---

def register_student(request):
    """
    Handles student registration.
    """
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        student_form = StudentForm(request.POST)
        if user_form.is_valid() and student_form.is_valid():
            user = user_form.save(commit=False)
            user.user_type = 'Student'
            user.save()
            student = student_form.save(commit=False)
            student.user = user
            student.save()
            messages.success(request, "Student account created successfully! You can now log in.")
            return redirect('login')
    else:
        user_form = CustomUserCreationForm()
        student_form = StudentForm()

    context = {
        'user_form': user_form,
        'student_form': student_form
    }
    
    return render(request, 'register_student.html', context)


# --- Course Management Views (New) ---

@login_required
# Corrected login_url for the decorator
@user_passes_test(is_admin, login_url='/webapp/login/')
def course_list(request):
    """
    Displays a list of all courses.
    """
    courses = Course.objects.select_related('lecturer__user').all().order_by('course_code')
    context = {
        'courses': courses
    }
    
    return render(request, 'course_list.html', context)


@login_required
# Corrected login_url for the decorator
@user_passes_test(is_admin, login_url='/webapp/login/')
def add_course(request):
    """
    Handles adding a new course.
    """
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Course added successfully!")
            return redirect('course_list')  
    else:
        form = CourseForm()
    context = {
        'form': form
    }
    
    return render(request, 'add_course.html', context)

@login_required

@user_passes_test(is_admin, login_url='/webapp/login/')
def enroll_student(request, student_id):
    """
    Handles enrolling a student into courses.
    This is a simplified view; you might want a more complex form for multiple courses.
    """
    student = get_object_or_404(Student, pk=student_id)
    if request.method == 'POST':
        form = EnrollmentForm(request.POST)
        if form.is_valid():
            enrollment = form.save(commit=False)
            enrollment.student = student
            # Check if enrollment already exists to prevent duplicates
            if not Enrollment.objects.filter(student=student, course=enrollment.course).exists():
                enrollment.save()
                messages.success(request, f"Student {student.user.username} enrolled in {enrollment.course.course_name} successfully!")
                return redirect('student_dashboard')  
                form.add_error(None, "Student is already enrolled in this course.")
                messages.warning(request, "Student is already enrolled in this course.")
    else:
        form = EnrollmentForm(initial={'student': student_id})  

    context = {
        'student': student,
        'form': form
    }
     
    return render(request, 'enroll_student.html', context)


# --- API Endpoints  

@login_required
@user_passes_test(is_student)
def update_student_profile_api(request):
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            user = request.user
            student_profile = user.student_profile

            user.first_name = data.get('first_name', user.first_name)
            user.last_name = data.get('last_name', user.last_name)
            if data.get('email'):
                if User.objects.filter(email=data['email']).exclude(pk=user.pk).exists():
                    return JsonResponse({'error': 'Email already in use.'}, status=400)
                user.email = data['email']
            user.save()

            student_profile.program = data.get('program', student_profile.program)
            student_profile.save()

            return JsonResponse({'message': 'Profile updated successfully.'})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)
    return JsonResponse({'error': 'Invalid request method.'}, status=405)


@login_required
@user_passes_test(is_student)
def enroll_face_api(request):
    """Enroll (register) a student's face encoding for AI recognition.

    POST JSON:
      { "image_data": "data:image/jpeg;base64,..." }

    Requires exactly one face in frame.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    try:
        from .face_engine import encode_single_face, match_face
    except Exception as exc:
        logger.exception("Failed to import face engine for enrollment")
        return JsonResponse(
            {
                'error': 'Face recognition service is unavailable on this server.',
                'details': str(exc),
            },
            status=503,
        )

    try:
        data = json.loads(request.body.decode('utf-8'))
        image_data_b64 = data.get('image_data')

        if not image_data_b64:
            return JsonResponse({'error': 'Missing image data.'}, status=400)

        student = request.user.student_profile

        # Decode base64
        if ';base64,' in image_data_b64:
            _fmt, imgstr = image_data_b64.split(';base64,')
        else:
            imgstr = image_data_b64

        image_bytes = base64.b64decode(imgstr)
        npimg = np.frombuffer(image_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if bgr is None:
            return JsonResponse({'error': 'Invalid image data.'}, status=400)

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        enc_result = encode_single_face(rgb)
        if enc_result.status == "NO_FACE":
            return JsonResponse({'error': 'No face detected. Please try again.'}, status=400)
        if enc_result.status == "MULTIPLE_FACES":
            return JsonResponse({'error': 'Multiple faces detected. Ensure only you are in the frame.'}, status=400)
        
        # ---- Prevent duplicate face enrollment (same person for multiple students) ----
        # Use a stricter threshold and ignore malformed historical encodings to reduce false positives.
        new_enc = np.array(enc_result.encoding, dtype=np.float32).reshape(-1)
        if new_enc.size != 128 or not np.isfinite(new_enc).all():
            return JsonResponse({'error': 'Invalid face signature generated. Please try again.'}, status=400)

        # Lower threshold means stricter matching; this helps avoid "already registered" false positives.
        DUPLICATE_THRESHOLD = 0.42

        known_encodings = []
        known_student_ids = []
        for fe in FaceEncoding.objects.select_related('student').exclude(student=student):
            old_enc = np.array(fe.encoding, dtype=np.float32).reshape(-1)
            if old_enc.size != 128 or not np.isfinite(old_enc).all():
                logger.warning("Skipping malformed FaceEncoding for student_id=%s", fe.student_id)
                continue
            known_encodings.append(old_enc)
            known_student_ids.append(fe.student_id)

        duplicate_match = match_face(
            encoding=new_enc,
            known_encodings=known_encodings,
            known_student_ids=known_student_ids,
            threshold=DUPLICATE_THRESHOLD,
        )
        if duplicate_match.status == "MATCH":
            logger.info(
                "Duplicate enrollment blocked: user_id=%s matched_student_id=%s distance=%.4f",
                request.user.id,
                duplicate_match.matched_student_id,
                duplicate_match.distance if duplicate_match.distance is not None else -1,
            )
            return JsonResponse(
                {
                    "error": "This face appears to already be enrolled under another student account.",
                    "matched_student_id": duplicate_match.matched_student_id,
                    "distance": float(duplicate_match.distance) if duplicate_match.distance is not None else None,
                },
                status=409,
            )

        FaceEncoding.objects.update_or_create(
            student=student,
            defaults={'encoding': enc_result.encoding.tolist()}
        )

        return JsonResponse({'message': 'Face enrolled successfully! You can now mark attendance using AI.'})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)
    except Exception as e:
        logger.exception("Face enrollment failed")
        return JsonResponse({'error': 'An internal error occurred while enrolling face data.'}, status=500)


@login_required
@user_passes_test(is_student)
def mark_attendance_api(request):
    """Mark attendance using AI face recognition.

    Flow:
      1) Student is logged in (so we know the claimed identity).
      2) Student captures an image from webcam.
      3) System detects a face, extracts an embedding (AI), and matches it.
      4) Attendance is only marked if the recognized face matches the logged-in student.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    try:
        from .face_engine import encode_single_face, match_face
    except Exception as exc:
        logger.exception("Failed to import face engine for attendance")
        return JsonResponse(
            {
                'error': 'Face recognition service is unavailable on this server.',
                'details': str(exc),
            },
            status=503,
        )

    try:
        data = json.loads(request.body.decode('utf-8'))
        session_id = data.get('session_id')
        image_data_b64 = data.get('image_data')

        if not session_id or not image_data_b64:
            return JsonResponse({'error': 'Missing session ID or image data.'}, status=400)

        session = get_object_or_404(ClassSession, pk=session_id)
        student = request.user.student_profile

        # --- Verify student enrollment for this session's course/module ---
        if session.module:
            # If session has a specific module, verify student is enrolled in that module
            enrollment_exists = Enrollment.objects.filter(
                student=student,
                course=session.course,
                modules=session.module
            ).exists()
        else:
            # If no module specified, just check course enrollment
            enrollment_exists = Enrollment.objects.filter(
                student=student,
                course=session.course
            ).exists()
        
        if not enrollment_exists:
            return JsonResponse({
                'error': 'You are not enrolled in the course/module for this session.'
            }, status=403)

        # --- Decode base64 image ---
        if ';base64,' in image_data_b64:
            fmt, imgstr = image_data_b64.split(';base64,')
            ext = fmt.split('/')[-1]
        else:
            imgstr = image_data_b64
            ext = 'png'

        image_bytes = base64.b64decode(imgstr)
        npimg = np.frombuffer(image_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if bgr is None:
            return JsonResponse({'error': 'Invalid image data.'}, status=400)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        # --- AI: detect & encode exactly one face ---
        enc_result = encode_single_face(rgb)
        if enc_result.status == "NO_FACE":
            return JsonResponse({'error': 'No face detected. Please try again in better lighting.'}, status=400)
        if enc_result.status == "MULTIPLE_FACES":
            return JsonResponse({'error': 'Multiple faces detected. Ensure only you are in the frame.'}, status=400)

        # --- Ensure the student has enrolled their face first ---
        try:
            claimed_encoding = FaceEncoding.objects.get(student=student)
        except FaceEncoding.DoesNotExist:
            return JsonResponse({
                'error': 'Face not enrolled yet. Please enroll your face first, then mark attendance.'
            }, status=400)

        # --- Match captured face against the logged-in student (verification) ---
        known_encodings = [np.array(claimed_encoding.encoding, dtype=np.float32)]
        known_ids = [student.user_id]  # Student primary key is user_id
        match = match_face(enc_result.encoding, known_encodings, known_ids, threshold=0.55)

        if match.status != "MATCH":
            return JsonResponse({
                'error': 'Face verification failed. Your face does not match the enrolled profile.',
                'confidence': match.confidence,
                'distance': match.distance
            }, status=403)

        # --- Save attendance image (audit trail) ---
        file_name = f"attendance_{student.user.username}_{session.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        content_file = ContentFile(image_bytes, name=file_name)

        # --- Determine status based on local configured timezone ---
        now_local = timezone.localtime(timezone.now())
        session_start_dt = timezone.make_aware(datetime.combine(now_local.date(), session.start_time))
        session_end_dt = timezone.make_aware(datetime.combine(now_local.date(), session.end_time))
        grace_deadline_dt = session_start_dt + timedelta(minutes=15)

        if now_local <= session_start_dt:
            attendance_status = 'Present'
        elif now_local <= grace_deadline_dt and now_local <= session_end_dt:
            attendance_status = 'Present'
        elif now_local <= session_end_dt:
            attendance_status = 'Late'
        else:
            attendance_status = 'Absent'

        attendance_record, created = Attendance.objects.update_or_create(
            student=student,
            session=session,
            defaults={
                'status': attendance_status,
                'image_data': content_file,
                'date_time': timezone.now()
            }
        )

        new_record_data = {
            'course_name': attendance_record.session.course.course_name,
            'course_code': attendance_record.session.course.course_code,
            'date_time': attendance_record.date_time.isoformat(),
            'status': attendance_record.status,
            'image_data_url': attendance_record.image_data.url if attendance_record.image_data else None,
            'session_id': attendance_record.session.id,
            'session_day': attendance_record.session.get_day_of_week_display(),
            'session_start_time': attendance_record.session.start_time.strftime('%H:%M'),
            'session_end_time': attendance_record.session.end_time.strftime('%H:%M'),
            'ai_confidence': match.confidence,
        }

        return JsonResponse({
            'message': 'Attendance saved successfully!',
            'status': attendance_record.status,
            'course_name': session.course.course_name,
            'ai_confidence': match.confidence,
            'new_record': new_record_data,
            'created': created
        })

    except ClassSession.DoesNotExist:
        return JsonResponse({'error': 'Class session not found.'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)



 
@login_required
def add_class_session(request):
    """
    Handles the creation of a new class session.
    Only accessible by logged-in lecturers.
    """
    
    if not hasattr(request.user, 'lecturer_profile'):
        messages.error(request, "You must be a lecturer to add class schedules.")
        return redirect('lecturer_dashboard')  

     
    lecturer_profile = request.user.lecturer_profile

    if request.method == 'POST':
        
        form = ClassSessionForm(request.POST, lecturer_profile=lecturer_profile)
        if form.is_valid():
            class_session = form.save(commit=False)
            class_session.lecturer = lecturer_profile  
            class_session.save()
            messages.success(request, "Class session scheduled successfully!")
            return redirect('lecturer_dashboard') # Redirect to the lecturer's dashboard after success
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # For GET request, instantiate an empty form and pass the lecturer_profile
        form = ClassSessionForm(lecturer_profile=lecturer_profile)

    # Render the form template, passing the form instance
    return render(request, 'lecturers/class_session_form.html', {'form': form})

@login_required
def edit_class_session(request, pk):
    """
    Handles the editing of an existing class session.
    Only accessible by logged-in lecturers, and only for sessions they conduct.
    """
    # Ensure the logged-in user is a lecturer
    if not hasattr(request.user, 'lecturer_profile'):
        messages.error(request, "You must be a lecturer to edit class schedules.")
        return redirect('lecturer_dashboard')

    # Get the lecturer profile associated with the logged-in user
    lecturer_profile = request.user.lecturer_profile

    # Get the class session object, ensuring it belongs to the current lecturer
    class_session = get_object_or_404(ClassSession, pk=pk, lecturer=lecturer_profile)

    if request.method == 'POST':
        # Pass the lecturer_profile to the form's __init__ method
        form = ClassSessionForm(request.POST, instance=class_session, lecturer_profile=lecturer_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Class session updated successfully!")
            return redirect('lecturer_dashboard') # Redirect to dashboard after success
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # For GET request, instantiate the form with the existing instance data and pass the lecturer_profile
        form = ClassSessionForm(instance=class_session, lecturer_profile=lecturer_profile)

    # 
    return render(request, 'lecturers/class_session_form.html', {'form': form, 'class_session': class_session})


@login_required
@user_passes_test(is_student)
def download_attendance(request):
    student = request.user.student_profile
    _backfill_missed_attendance(student)
    attendance_records = student.attendance_records.select_related('session__course').all()

    # Get filters from query params
    date = request.GET.get('date')
    subject = request.GET.get('subject')

    if date:
        attendance_records = attendance_records.filter(date_time__date=date)
    if subject:
        attendance_records = attendance_records.filter(session__course__course_name=subject)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance.csv"'

    writer = csv.writer(response)
    writer.writerow(['Course', 'Date/Time', 'Status'])

    for record in attendance_records:
        writer.writerow([
            record.session.course.course_name,
            record.date_time.strftime('%Y-%m-%d %H:%M'),
            record.status
        ])
    return response

@login_required
def download_timetable(request):
    student = request.user.student_profile
    courses = student.enrollments.all().select_related('course')
    sessions = ClassSession.objects.filter(course__in=[e.course for e in courses]).select_related('course', 'lecturer')

    timetable = [['Course', 'Day', 'Start Time', 'End Time', 'Room', 'Lecturer']]
    for session in sessions:
        timetable.append([
            session.course.course_name,
            session.day_of_week,
            session.start_time.strftime('%H:%M'),
            session.end_time.strftime('%H:%M'),
            session.room,
            f"{session.lecturer.user.first_name} {session.lecturer.user.last_name}"
        ])

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="timetable.csv"'
    writer = csv.writer(response)
    for row in timetable:
        writer.writerow(row)
    return response

@login_required
def contact_lecturers(request):
    student = request.user.student_profile  # Get the Student profile for the logged-in user
    # Get all enrollments for this student
    enrollments = student.enrollments.select_related('course')
    # Build a list of lecturer info for each enrolled course
    lecturer_info = []
    for enrollment in enrollments:
        course = enrollment.course
        for module in course.modules.all():
            for lecturer in module.lecturers.all():
                lecturer_info.append({
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'lecturer_name': f"{lecturer.user.first_name} {lecturer.user.last_name}",
                    'lecturer_email': lecturer.user.email,
                })
    return render(request, 'students/contact_lecturers.html', {'lecturer_info': lecturer_info})