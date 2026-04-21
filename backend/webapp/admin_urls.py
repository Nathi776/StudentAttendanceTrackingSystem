from django.urls import path

from . import admin_views

urlpatterns = [
    path('', admin_views.AdminDashboardView.as_view(), name='admin_dashboard'),

    # User management
    path('users/', admin_views.AdminUserListView.as_view(), name='admin_user_list'),
    path('users/add/', admin_views.AdminUserCreateView.as_view(), name='admin_user_add'),
    path('users/<str:pk>/edit/', admin_views.AdminUserUpdateView.as_view(), name='admin_user_edit'),
    path('users/<str:pk>/password/', admin_views.AdminUserPasswordChangeView.as_view(), name='admin_user_password'),
    path('users/<str:pk>/delete/', admin_views.AdminUserDeleteView.as_view(), name='admin_user_delete'),

    # Student management
    path('students/', admin_views.AdminStudentListView.as_view(), name='admin_student_list'),
    path('students/add/', admin_views.AdminStudentCreateView.as_view(), name='admin_student_add'),
    path('students/<str:pk>/edit/', admin_views.AdminStudentUpdateView.as_view(), name='admin_student_edit'),
    path('students/<str:pk>/delete/', admin_views.AdminStudentDeleteView.as_view(), name='admin_student_delete'),

    # Lecturer management
    path('lecturers/', admin_views.AdminLecturerListView.as_view(), name='admin_lecturer_list'),
    path('lecturers/add/', admin_views.AdminLecturerCreateView.as_view(), name='admin_lecturer_add'),
    path('lecturers/<str:pk>/edit/', admin_views.AdminLecturerUpdateView.as_view(), name='admin_lecturer_edit'),
    path('lecturers/<str:pk>/delete/', admin_views.AdminLecturerDeleteView.as_view(), name='admin_lecturer_delete'),

    # Module management
    path('modules/', admin_views.AdminModuleListView.as_view(), name='admin_module_list'),
    path('modules/add/', admin_views.AdminModuleCreateView.as_view(), name='admin_module_add'),
    path('modules/<str:pk>/edit/', admin_views.AdminModuleUpdateView.as_view(), name='admin_module_edit'),
    path('modules/<str:pk>/delete/', admin_views.AdminModuleDeleteView.as_view(), name='admin_module_delete'),

    # Course management
    path('courses/', admin_views.AdminCourseListView.as_view(), name='admin_course_list'),
    path('courses/add/', admin_views.AdminCourseCreateView.as_view(), name='admin_course_add'),
    path('courses/<str:pk>/edit/', admin_views.AdminCourseUpdateView.as_view(), name='admin_course_edit'),
    path('courses/<str:pk>/delete/', admin_views.AdminCourseDeleteView.as_view(), name='admin_course_delete'),

    # Enrollment management
    path('enrollments/', admin_views.AdminEnrollmentListView.as_view(), name='admin_enrollment_list'),
    path('enrollments/add/', admin_views.AdminEnrollmentCreateView.as_view(), name='admin_enrollment_add'),
    path('enrollments/<str:pk>/edit/', admin_views.AdminEnrollmentUpdateView.as_view(), name='admin_enrollment_edit'),
    path('enrollments/<str:pk>/delete/', admin_views.AdminEnrollmentDeleteView.as_view(), name='admin_enrollment_delete'),
    path('enrollments/modules-for-course/', admin_views.AdminEnrollmentModulesForCourseView.as_view(), name='admin_enrollment_modules_for_course'),

    # Class Session management
    path('sessions/', admin_views.AdminClassSessionListView.as_view(), name='admin_classsession_list'),
    path('sessions/add/', admin_views.AdminClassSessionCreateView.as_view(), name='admin_classsession_add'),
    path('sessions/<str:pk>/edit/', admin_views.AdminClassSessionUpdateView.as_view(), name='admin_classsession_edit'),
    path('sessions/<str:pk>/delete/', admin_views.AdminClassSessionDeleteView.as_view(), name='admin_classsession_delete'),

    # Attendance management
    path('attendance/', admin_views.AdminAttendanceListView.as_view(), name='admin_attendance_list'),
    path('attendance/add/', admin_views.AdminAttendanceCreateView.as_view(), name='admin_attendance_add'),
    path('attendance/<str:pk>/edit/', admin_views.AdminAttendanceUpdateView.as_view(), name='admin_attendance_edit'),
    path('attendance/<str:pk>/delete/', admin_views.AdminAttendanceDeleteView.as_view(), name='admin_attendance_delete'),

    # Face encoding management
    path('face-encodings/', admin_views.AdminFaceEncodingListView.as_view(), name='admin_faceencoding_list'),
    path('face-encodings/add/', admin_views.AdminFaceEncodingCreateView.as_view(), name='admin_faceencoding_add'),
    path('face-encodings/<str:pk>/edit/', admin_views.AdminFaceEncodingUpdateView.as_view(), name='admin_faceencoding_edit'),
    path('face-encodings/<str:pk>/delete/', admin_views.AdminFaceEncodingDeleteView.as_view(), name='admin_faceencoding_delete'),

    path('permissions/', admin_views.AdminPermissionListView.as_view(), name='admin_permission_list'),
    path('permissions/add/', admin_views.AdminPermissionCreateView.as_view(), name='admin_permission_add'),
    path('permissions/<str:pk>/edit/', admin_views.AdminPermissionUpdateView.as_view(), name='admin_permission_edit'),
    path('permissions/<str:pk>/delete/', admin_views.AdminPermissionDeleteView.as_view(), name='admin_permission_delete'),
]
