"""
Report generation views for the Student Attendance Tracking System.
Provides comprehensive reporting with filtering, aggregation, and export capabilities.
"""
from datetime import datetime, timedelta
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q, F, Sum, Case, When, IntegerField, Avg
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status as rest_status

import csv
import json
from io import BytesIO

# PDF export imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from .models import (
    Student, Lecturer, Course, Enrollment, ClassSession, Attendance, User
)


# ============================================================================
# Helper Functions
# ============================================================================

def api_success(data=None, message=None):
    return Response({
        'success': True,
        'message': message,
        'data': data,
    })


def api_error(message, status_code=rest_status.HTTP_400_BAD_REQUEST, errors=None):
    payload = {
        'success': False,
        'message': message,
    }
    if errors is not None:
        payload['errors'] = errors
    return Response(payload, status=status_code)


def parse_date(date_str):
    """Parse date string in YYYY-MM-DD format."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


def get_date_range_defaults():
    """Get default date range: first day of current month to today."""
    today = timezone.now().date()
    first_day = today.replace(day=1)
    return first_day, today


def is_admin(user):
    """Check if user is admin."""
    return user.is_authenticated and user.user_type == 'Admin'


def is_lecturer(user):
    """Check if user is a lecturer."""
    return user.is_authenticated and hasattr(user, 'lecturer_profile')


def is_student(user):
    """Check if user is a student."""
    return user.is_authenticated and hasattr(user, 'student_profile')


# ============================================================================
# API Report Views
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attendance_report(request):
    """
    Attendance Report - Detailed attendance records with filtering.
    
    Filters:
    - start_date: YYYY-MM-DD (default: first day of current month)
    - end_date: YYYY-MM-DD (default: today)
    - status: Present|Absent|Late
    - course_code: Filter by specific course
    - student_id: Filter by specific student (admin/lecturer only)
    - format: json|csv|pdf
    """
    # Get filter parameters
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    status_filter = request.GET.get('status', '').strip()
    course_code = request.GET.get('course_code', '').strip()
    student_id = request.GET.get('student_id')
    export_format = request.GET.get('format', 'json').lower()
    
    # Parse dates with defaults
    start_date, end_date = get_date_range_defaults()
    if start_date_str:
        parsed = parse_date(start_date_str)
        if parsed:
            start_date = parsed
    if end_date_str:
        parsed = parse_date(end_date_str)
        if parsed:
            end_date = parsed
    
    # Base queryset
    attendance_qs = Attendance.objects.select_related(
        'student__user', 'session__course', 'session__lecturer__user'
    )
    
    # Apply user-specific filtering
    if is_student(request.user):
        # Students can only see their own attendance
        attendance_qs = attendance_qs.filter(student=request.user.student_profile)
    elif is_lecturer(request.user):
        # Lecturers see attendance for their classes
        attendance_qs = attendance_qs.filter(session__lecturer=request.user.lecturer_profile)
    elif not is_admin(request.user):
        return api_error('Insufficient permissions', rest_status.HTTP_403_FORBIDDEN)
    
    # Apply date range filter
    attendance_qs = attendance_qs.filter(
        date_time__date__gte=start_date,
        date_time__date__lte=end_date
    )
    
    # Apply status filter
    if status_filter:
        attendance_qs = attendance_qs.filter(status=status_filter)
    
    # Apply course filter
    if course_code:
        attendance_qs = attendance_qs.filter(session__course__course_code=course_code)
    
    # Apply student filter (admin/lecturer only)
    if student_id and (is_admin(request.user) or is_lecturer(request.user)):
        attendance_qs = attendance_qs.filter(student__user__id=student_id)
    
    # Prepare data for response
    attendance_list = []
    for record in attendance_qs.order_by('-date_time'):
        attendance_list.append({
            'id': record.id,
            'student_name': record.student.user.get_full_name(),
            'student_id': record.student.user.id,
            'course_code': record.session.course.course_code,
            'course_name': record.session.course.course_name,
            'date': timezone.localtime(record.date_time).strftime('%Y-%m-%d'),
            'time': timezone.localtime(record.date_time).strftime('%H:%M'),
            'status': record.status,
            'lecturer': record.session.lecturer.user.get_full_name() if record.session.lecturer else 'N/A',
        })
    
    # Handle different export formats
    if export_format == 'csv':
        return _export_attendance_csv(attendance_list)
    elif export_format == 'pdf':
        return _export_attendance_pdf(attendance_list, start_date, end_date)
    else:
        return api_success({
            'count': len(attendance_list),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'records': attendance_list,
        }, 'Attendance report retrieved successfully.')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def enrollment_report(request):
    """
    Enrollment Report - Shows all student enrollments and course registration.
    
    Filters:
    - course_code: Filter by specific course
    - start_date: Enrollment date range start (YYYY-MM-DD)
    - end_date: Enrollment date range end (YYYY-MM-DD)
    - format: json|csv|pdf
    """
    # Check permissions
    if not (is_admin(request.user) or is_lecturer(request.user)):
        return api_error('Insufficient permissions', rest_status.HTTP_403_FORBIDDEN)
    
    # Get filter parameters
    course_code = request.GET.get('course_code', '').strip()
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    export_format = request.GET.get('format', 'json').lower()
    
    # Parse dates
    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None
    
    # Base queryset
    enrollment_qs = Enrollment.objects.select_related('student__user', 'course', 'lecturer__user')
    
    # Apply filters
    if course_code:
        enrollment_qs = enrollment_qs.filter(course__course_code=course_code)
    
    if start_date:
        enrollment_qs = enrollment_qs.filter(enrollment_date__gte=start_date)
    
    if end_date:
        enrollment_qs = enrollment_qs.filter(enrollment_date__lte=end_date)
    
    # Prepare data
    enrollment_list = []
    for enrollment in enrollment_qs.order_by('-enrollment_date'):
        modules = ', '.join([m.module_code for m in enrollment.modules.all()]) or 'N/A'
        enrollment_list.append({
            'student_id': enrollment.student.user.id,
            'student_name': enrollment.student.user.get_full_name(),
            'student_number': enrollment.student.user.username,
            'email': enrollment.student.user.email,
            'course_code': enrollment.course.course_code,
            'course_name': enrollment.course.course_name,
            'lecturer_name': enrollment.lecturer.user.get_full_name() if enrollment.lecturer else 'N/A',
            'lecturer_username': enrollment.lecturer.user.username if enrollment.lecturer else 'N/A',
            'modules': modules,
            'enrollment_date': enrollment.enrollment_date.isoformat(),
        })
    
    # Handle export formats
    if export_format == 'csv':
        return _export_enrollment_csv(enrollment_list)
    elif export_format == 'pdf':
        return _export_enrollment_pdf(enrollment_list)
    else:
        return api_success({
            'count': len(enrollment_list),
            'records': enrollment_list,
        }, 'Enrollment report retrieved successfully.')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def course_attendance_summary(request):
    """
    Course Attendance Summary Report - Aggregated attendance statistics per course.
    
    Returns:
    - Total sessions per course
    - Average attendance rate per course
    - Students per course
    - Breakdown by status (Present, Absent, Late)
    
    Filters:
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - format: json|csv|pdf
    """
    # Check permissions
    if not (is_admin(request.user) or is_lecturer(request.user)):
        return api_error('Insufficient permissions', rest_status.HTTP_403_FORBIDDEN)
    
    # Get filter parameters
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    export_format = request.GET.get('format', 'json').lower()
    
    # Parse dates with defaults
    start_date, end_date = get_date_range_defaults()
    if start_date_str:
        parsed = parse_date(start_date_str)
        if parsed:
            start_date = parsed
    if end_date_str:
        parsed = parse_date(end_date_str)
        if parsed:
            end_date = parsed
    
    # Get all courses
    courses = Course.objects.annotate(
        total_students=Count('enrollments__student', distinct=True),
        total_sessions=Count('class_sessions', distinct=True)
    )
    
    # Build summary for each course
    summary_list = []
    for course in courses:
        # Get attendance records for this course in date range
        attendance_qs = Attendance.objects.filter(
            session__course=course,
            date_time__date__gte=start_date,
            date_time__date__lte=end_date
        )
        
        total_records = attendance_qs.count()
        present = attendance_qs.filter(status='Present').count()
        absent = attendance_qs.filter(status='Absent').count()
        late = attendance_qs.filter(status='Late').count()
        
        attendance_rate = (present / total_records * 100) if total_records > 0 else 0
        
        summary_list.append({
            'course_code': course.course_code,
            'course_name': course.course_name,
            'total_students': course.total_students,
            'total_sessions': course.total_sessions,
            'total_attendance_records': total_records,
            'attendance_rate_percent': round(attendance_rate, 2),
            'present': present,
            'absent': absent,
            'late': late,
        })
    
    # Handle export formats
    if export_format == 'csv':
        return _export_course_summary_csv(summary_list)
    elif export_format == 'pdf':
        return _export_course_summary_pdf(summary_list, start_date, end_date)
    else:
        return api_success({
            'count': len(summary_list),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'records': summary_list,
        }, 'Course attendance summary retrieved successfully.')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_performance_report(request):
    """
    Student Performance Report - Individual student attendance analysis.
    
    For Admins/Lecturers: Shows performance metrics for all students
    For Students: Shows only their own performance
    
    Filters:
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - student_id: Filter by specific student (admin/lecturer only)
    - course_code: Filter by course
    - format: json|csv|pdf
    """
    # Get filter parameters
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    student_id = request.GET.get('student_id')
    course_code = request.GET.get('course_code', '').strip()
    export_format = request.GET.get('format', 'json').lower()
    
    # Parse dates with defaults
    start_date, end_date = get_date_range_defaults()
    if start_date_str:
        parsed = parse_date(start_date_str)
        if parsed:
            start_date = parsed
    if end_date_str:
        parsed = parse_date(end_date_str)
        if parsed:
            end_date = parsed
    
    # Determine which students to include
    if is_student(request.user):
        students = [request.user.student_profile]
    elif is_lecturer(request.user):
        # Show students in lecturer's courses
        lecturer = request.user.lecturer_profile
        course_ids = ClassSession.objects.filter(
            lecturer=lecturer
        ).values_list('course_id', flat=True).distinct()
        students = Student.objects.filter(
            enrollments__course__in=course_ids
        ).distinct()
    elif is_admin(request.user):
        students = Student.objects.all()
        if student_id:
            students = students.filter(user__id=student_id)
    else:
        return api_error('Insufficient permissions', rest_status.HTTP_403_FORBIDDEN)
    
    # Build performance report for each student
    performance_list = []
    for student in students:
        # Get attendance for this student in date range
        attendance_qs = Attendance.objects.filter(
            student=student,
            date_time__date__gte=start_date,
            date_time__date__lte=end_date
        )
        
        # Apply course filter if provided
        if course_code:
            attendance_qs = attendance_qs.filter(session__course__course_code=course_code)
        
        total = attendance_qs.count()
        present = attendance_qs.filter(status='Present').count()
        absent = attendance_qs.filter(status='Absent').count()
        late = attendance_qs.filter(status='Late').count()
        
        attendance_rate = (present / total * 100) if total > 0 else 0
        performance_score = attendance_rate  # Simple scoring based on attendance
        
        performance_list.append({
            'student_id': student.user.id,
            'student_name': student.user.get_full_name(),
            'student_number': student.user.username,
            'email': student.user.email,
            'total_sessions': total,
            'present': present,
            'absent': absent,
            'late': late,
            'attendance_rate_percent': round(attendance_rate, 2),
            'performance_score': round(performance_score, 2),
        })
    
    # Sort by performance score descending
    performance_list.sort(key=lambda x: x['performance_score'], reverse=True)
    
    # Handle export formats
    if export_format == 'csv':
        return _export_performance_csv(performance_list)
    elif export_format == 'pdf':
        return _export_performance_pdf(performance_list, start_date, end_date)
    else:
        return api_success({
            'count': len(performance_list),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'records': performance_list,
        }, 'Student performance report retrieved successfully.')


# ============================================================================
# Export Helper Functions (CSV)
# ============================================================================

def _export_attendance_csv(attendance_list):
    """Export attendance data to CSV format."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Student Name', 'Student ID', 'Course Code', 'Course Name',
        'Date', 'Time', 'Status', 'Lecturer'
    ])
    
    for record in attendance_list:
        writer.writerow([
            record['student_name'],
            record['student_id'],
            record['course_code'],
            record['course_name'],
            record['date'],
            record['time'],
            record['status'],
            record['lecturer'],
        ])
    
    return response


def _export_enrollment_csv(enrollment_list):
    """Export enrollment data to CSV format."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="enrollment_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Student Number', 'Student Name', 'Email', 'Course Code',
        'Course Name', 'Modules', 'Enrollment Date'
    ])
    
    for record in enrollment_list:
        writer.writerow([
            record['student_number'],
            record['student_name'],
            record['email'],
            record['course_code'],
            record['course_name'],
            record['modules'],
            record['enrollment_date'],
        ])
    
    return response


def _export_course_summary_csv(summary_list):
    """Export course attendance summary to CSV format."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="course_attendance_summary.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Course Code', 'Course Name', 'Total Students', 'Total Sessions',
        'Total Attendance Records', 'Attendance Rate (%)',
        'Present', 'Absent', 'Late'
    ])
    
    for record in summary_list:
        writer.writerow([
            record['course_code'],
            record['course_name'],
            record['total_students'],
            record['total_sessions'],
            record['total_attendance_records'],
            record['attendance_rate_percent'],
            record['present'],
            record['absent'],
            record['late'],
        ])
    
    return response


def _export_performance_csv(performance_list):
    """Export student performance data to CSV format."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_performance_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Student Number', 'Student Name', 'Email',
        'Total Sessions', 'Present', 'Absent', 'Late',
        'Attendance Rate (%)', 'Performance Score'
    ])
    
    for record in performance_list:
        writer.writerow([
            record['student_number'],
            record['student_name'],
            record['email'],
            record['total_sessions'],
            record['present'],
            record['absent'],
            record['late'],
            record['attendance_rate_percent'],
            record['performance_score'],
        ])
    
    return response


# ============================================================================
# Export Helper Functions (PDF)
# ============================================================================

def _create_pdf_response(filename):
    """Create a PDF response object."""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _export_attendance_pdf(attendance_list, start_date, end_date):
    """Export attendance data to PDF format."""
    if not REPORTLAB_AVAILABLE:
        return HttpResponse(
            'PDF export not available. Please install reportlab.',
            status=500
        )
    
    response = _create_pdf_response('attendance_report.pdf')
    doc = SimpleDocTemplate(response, pagesize=letter)
    story = []
    
    # Add title
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2E5090'),
        spaceAfter=12,
    )
    story.append(Paragraph('Attendance Report', title_style))
    story.append(Paragraph(f'Period: {start_date} to {end_date}', styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Create table data
    table_data = [[
        'Student', 'Course', 'Date', 'Time', 'Status', 'Lecturer'
    ]]
    
    for record in attendance_list[:50]:  # Limit to first 50 for PDF
        table_data.append([
            record['student_name'][:20],
            record['course_code'],
            record['date'],
            record['time'],
            record['status'],
            record['lecturer'][:15],
        ])
    
    if len(attendance_list) > 50:
        table_data.append(['...', '...', f'({len(attendance_list) - 50} more records)', '...', '...', '...'])
    
    # Create and style table
    table = Table(table_data, colWidths=[1.5*inch, 1*inch, 1*inch, 0.8*inch, 0.8*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5090')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    story.append(table)
    doc.build(story)
    return response


def _export_enrollment_pdf(enrollment_list):
    """Export enrollment data to PDF format."""
    if not REPORTLAB_AVAILABLE:
        return HttpResponse(
            'PDF export not available. Please install reportlab.',
            status=500
        )
    
    response = _create_pdf_response('enrollment_report.pdf')
    doc = SimpleDocTemplate(response, pagesize=letter)
    story = []
    
    # Add title
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2E5090'),
        spaceAfter=12,
    )
    story.append(Paragraph('Enrollment Report', title_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Create table data
    table_data = [[
        'Student', 'Email', 'Course', 'Modules', 'Date'
    ]]
    
    for record in enrollment_list[:50]:
        table_data.append([
            record['student_name'][:20],
            record['email'][:20],
            record['course_code'],
            record['modules'][:20],
            record['enrollment_date'],
        ])
    
    if len(enrollment_list) > 50:
        table_data.append(['...', '...', f'({len(enrollment_list) - 50} more)', '...', '...'])
    
    # Create and style table
    table = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1*inch, 1.5*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5090')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    story.append(table)
    doc.build(story)
    return response


def _export_course_summary_pdf(summary_list, start_date, end_date):
    """Export course attendance summary to PDF format."""
    if not REPORTLAB_AVAILABLE:
        return HttpResponse(
            'PDF export not available. Please install reportlab.',
            status=500
        )
    
    response = _create_pdf_response('course_attendance_summary.pdf')
    doc = SimpleDocTemplate(response, pagesize=letter)
    story = []
    
    # Add title
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2E5090'),
        spaceAfter=12,
    )
    story.append(Paragraph('Course Attendance Summary', title_style))
    story.append(Paragraph(f'Period: {start_date} to {end_date}', styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Create table data
    table_data = [[
        'Course', 'Students', 'Sessions', 'Attendance %',
        'Present', 'Absent', 'Late'
    ]]
    
    for record in summary_list[:40]:
        table_data.append([
            f"{record['course_code']}",
            str(record['total_students']),
            str(record['total_sessions']),
            f"{record['attendance_rate_percent']}%",
            str(record['present']),
            str(record['absent']),
            str(record['late']),
        ])
    
    if len(summary_list) > 40:
        table_data.append(['...', '...', '...', f'({len(summary_list) - 40} more)', '...', '...', '...'])
    
    # Create and style table
    table = Table(table_data, colWidths=[1.2*inch, 1*inch, 1*inch, 1.2*inch, 0.8*inch, 0.8*inch, 0.8*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5090')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    story.append(table)
    doc.build(story)
    return response


def _export_performance_pdf(performance_list, start_date, end_date):
    """Export student performance data to PDF format."""
    if not REPORTLAB_AVAILABLE:
        return HttpResponse(
            'PDF export not available. Please install reportlab.',
            status=500
        )
    
    response = _create_pdf_response('student_performance_report.pdf')
    doc = SimpleDocTemplate(response, pagesize=letter)
    story = []
    
    # Add title
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2E5090'),
        spaceAfter=12,
    )
    story.append(Paragraph('Student Performance Report', title_style))
    story.append(Paragraph(f'Period: {start_date} to {end_date}', styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Create table data
    table_data = [[
        'Student', 'Sessions', 'Present', 'Absent', 'Late',
        'Attendance %', 'Score'
    ]]
    
    for record in performance_list[:45]:
        table_data.append([
            record['student_name'][:18],
            str(record['total_sessions']),
            str(record['present']),
            str(record['absent']),
            str(record['late']),
            f"{record['attendance_rate_percent']}%",
            f"{record['performance_score']}",
        ])
    
    if len(performance_list) > 45:
        table_data.append(['...', '...', '...', '...', '...', f'({len(performance_list) - 45} more)', '...'])
    
    # Create and style table
    table = Table(table_data, colWidths=[1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch, 0.9*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5090')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    story.append(table)
    doc.build(story)
    return response
