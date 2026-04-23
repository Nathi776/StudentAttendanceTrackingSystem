from django.urls import path
from . import api_views

app_name = 'api'

urlpatterns = [
    path('status/', api_views.api_status, name='status'),
    path('auth/csrf/', api_views.api_csrf, name='csrf'),
    path('auth/login/', api_views.api_login, name='login'),
    path('auth/logout/', api_views.api_logout, name='logout'),
    path('auth/me/', api_views.api_current_user, name='current_user'),

    path('student/dashboard/', api_views.api_student_dashboard, name='student_dashboard'),
    path('lecturer/dashboard/', api_views.api_lecturer_dashboard, name='lecturer_dashboard'),
]
