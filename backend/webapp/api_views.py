from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Student, Lecturer, Course, Enrollment, ClassSession, Attendance, FaceEncoding
from .serializers import (
    UserSerializer,
    StudentSerializer,
    LecturerSerializer,
    EnrollmentSerializer,
    ClassSessionSerializer,
    AttendanceSerializer,
)


def api_success(data=None, message=None):
    return Response({
        'success': True,
        'message': message,
        'data': data,
    })


def api_error(message, status_code=status.HTTP_400_BAD_REQUEST, errors=None):
    payload = {
        'success': False,
        'message': message,
    }
    if errors is not None:
        payload['errors'] = errors
    return Response(payload, status=status_code)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_status(request):
    """Simple health check endpoint."""
    return api_success({'status': 'ok'})


@ensure_csrf_cookie
@api_view(['GET'])
@permission_classes([AllowAny])
def api_csrf(request):
    """Set CSRF cookie for browser clients before state-changing requests."""
    return api_success({'csrf_cookie_set': True})


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def api_login(request):
    """Authenticate a user and create a session cookie."""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return api_error('Missing username or password.', status_code=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return api_error('Invalid username or password', status_code=status.HTTP_401_UNAUTHORIZED)

    login(request, user)
    user_data = UserSerializer(user).data
    return api_success({'user': user_data}, message='Logged in successfully.')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    logout(request)
    return api_success(message='Logged out successfully.')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_current_user(request):
    return api_success({'user': UserSerializer(request.user).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_student_dashboard(request):
    if not hasattr(request.user, 'student_profile'):
        return api_error('User is not a student', status_code=status.HTTP_403_FORBIDDEN)

    student_profile = request.user.student_profile

    # Basic profile info
    student_data = StudentSerializer(student_profile).data

    # Enrolled subjects
    enrolled_courses = Enrollment.objects.filter(student=student_profile).select_related('course')
    subjects_data = []
    for e in enrolled_courses:
        course = e.course
        lecturer_names = set()
        for module in course.modules.all():
            for lecturer in module.lecturers.all():
                lecturer_names.add(lecturer.user.get_full_name())
        subjects_data.append({
            'course_code': course.course_code,
            'course_name': course.course_name,
            'lecturer_name': ", ".join(sorted(lecturer_names)) if lecturer_names else None,
        })

    # Attendance records
    attendance = Attendance.objects.filter(student=student_profile).select_related('session__course')[:20]
    attendance_data = [
        {
            'course_name': a.session.course.course_name,
            'course_code': a.session.course.course_code,
            'date_time': a.date_time.isoformat(),
            'status': a.status,
        }
        for a in attendance
    ]

    # Class schedule
    enrolled_course_codes = [e.course.course_code for e in enrolled_courses]
    schedule_qs = ClassSession.objects.filter(course__course_code__in=enrolled_course_codes).select_related('course', 'lecturer__user')
    schedule_data = [
        {
            'id': s.id,
            'course_code': s.course.course_code,
            'course_name': s.course.course_name,
            'day_of_week': s.day_of_week,
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M'),
            'room': s.room,
            'lecturer': s.lecturer.user.get_full_name() if s.lecturer else None,
        }
        for s in schedule_qs
    ]

    return api_success(
        {
            'student': student_data,
            'subjects': subjects_data,
            'attendance_records': attendance_data,
            'class_schedule': schedule_data,
        }
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_lecturer_dashboard(request):
    if not hasattr(request.user, 'lecturer_profile'):
        return api_error('User is not a lecturer', status_code=status.HTTP_403_FORBIDDEN)

    lecturer_profile = request.user.lecturer_profile

    # Courses taught (determined by modules assigned to this lecturer)
    courses = Course.objects.filter(modules__in=lecturer_profile.modules.all()).distinct()
    course_data = [
        {
            'course_code': c.course_code,
            'course_name': c.course_name,
        }
        for c in courses
    ]

    # Upcoming sessions
    sessions = ClassSession.objects.filter(lecturer=lecturer_profile).select_related('course')[:20]
    sessions_data = [
        {
            'id': s.id,
            'course_code': s.course.course_code,
            'course_name': s.course.course_name,
            'day_of_week': s.day_of_week,
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M'),
            'room': s.room,
        }
        for s in sessions
    ]

    return api_success(
        {
            'lecturer': LecturerSerializer(lecturer_profile).data,
            'courses': course_data,
            'sessions': sessions_data,
        }
    )
