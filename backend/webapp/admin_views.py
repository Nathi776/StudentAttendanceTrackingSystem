from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.forms import SetPasswordForm
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, FormView

from django.contrib.auth.models import Group, Permission

from .models import (
    User,
    Student,
    Lecturer,
    Module,
    Program,
    Course,
    Enrollment,
    ClassSession,
    Attendance,
    FaceEncoding,
)
from .forms import (
    CustomUserChangeForm,
    CustomUserCreationForm,
    StudentForm,
    LecturerForm,
    ModuleForm,
    CourseForm,
    EnrollmentForm,
    ClassSessionForm,
    AttendanceForm,
)


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict access to users who are marked as staff/admin."""

    login_url = 'login'

    def test_func(self):
        user = self.request.user
        # Allow access for superusers, staff users, and users explicitly marked as Admin.
        return bool(
            user.is_authenticated
            and (
                user.is_superuser
                or user.is_staff
                or getattr(user, 'user_type', None) == 'Admin'
            )
        )


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = 'admin/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'total_users': User.objects.count(),
                'total_students': Student.objects.count(),
                'total_lecturers': Lecturer.objects.count(),
                'total_modules': Module.objects.count(),
                'total_programs': Program.objects.count(),
                'total_courses': Course.objects.count(),
                'total_enrollments': Enrollment.objects.count(),
                'total_sessions': ClassSession.objects.count(),
                'total_attendance': Attendance.objects.count(),
                'total_face_encodings': FaceEncoding.objects.count(),
                'total_groups': Group.objects.count(),
                'total_permissions': Permission.objects.count(),
                # Provide lists for the dashboard quick-links
                'students': [
                    {
                        'studentNumber': s.user.username,
                        'firstName': s.user.first_name,
                        'lastName': s.user.last_name,
                        'email': s.user.email,
                    }
                    for s in Student.objects.select_related('user').order_by('-user__date_joined')[:10]
                ],
                'lecturers': [
                    {
                        'staffNumber': l.user.username,
                        'firstName': l.user.first_name,
                        'lastName': l.user.last_name,
                        'email': l.user.email,
                    }
                    for l in Lecturer.objects.select_related('user').order_by('-user__date_joined')[:10]
                ],
            }
        )
        return context


class AdminModelListView(AdminRequiredMixin, ListView):
    """Generic list view for admin-managed models."""

    template_name = 'admin/model_list.html'
    paginate_by = 30

    # Set these in subclasses or in as_view(...) kwargs
    model = None
    list_display = None
    search_fields = None
    add_url_name = None
    change_url_name = None
    change_password_url_name = None
    delete_url_name = None

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q and self.search_fields:
            from django.db.models import Q

            query = Q()
            for field in self.search_fields:
                query |= Q(**{f"{field}__icontains": q})
            qs = qs.filter(query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model = self.model
        context.update(
            {
                'model_name': model._meta.verbose_name.title(),
                'model_name_plural': model._meta.verbose_name_plural.title(),
                'add_url_name': self.add_url_name,
                'change_url_name': self.change_url_name,
                'change_password_url_name': self.change_password_url_name,
                'delete_url_name': self.delete_url_name,
                'search_query': self.request.GET.get('q', ''),
            }
        )
        return context


class AdminModelFormView(AdminRequiredMixin):
    """Base mixin for create/update views in the admin interface."""

    template_name = 'admin/model_form.html'
    success_url = None
    form_class = None
    model = None

    def get_success_url(self):
        if self.success_url:
            return self.success_url
        return reverse_lazy(f'admin_{self.model._meta.model_name}_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model = self.model
        context.update(
            {
                'model_name': model._meta.verbose_name.title(),
                'model_name_plural': model._meta.verbose_name_plural.title(),
                'list_url_name': f'admin_{model._meta.model_name}_list',
            }
        )
        return context


class AdminModelDeleteView(AdminRequiredMixin, DeleteView):
    template_name = 'admin/confirm_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model = self.model
        context.update(
            {
                'model_name': model._meta.verbose_name.title(),
                'model_name_plural': model._meta.verbose_name_plural.title(),
                'list_url_name': f'admin_{model._meta.model_name}_list',
            }
        )
        return context

    def get_success_url(self):
        return reverse_lazy(f'admin_{self.model._meta.model_name}_list')

class AdminEnrollmentModulesForCourseView(AdminRequiredMixin, View):
    """Provides a JSON list of modules for the given course.

    Used by the admin Enrollment form JS to filter available modules based on the selected course.
    """

    def get(self, request, *args, **kwargs):
        course_id = request.GET.get('course_id')
        modules_data = []
        if course_id:
            try:
                course = Course.objects.get(pk=course_id)
                modules_data = list(
                    course.modules.values('id', 'module_code', 'module_name')
                )
            except Course.DoesNotExist:
                modules_data = []

        return JsonResponse(
            {
                'modules': [
                    {'id': m['id'], 'code': m['module_code'], 'name': m['module_name']}
                    for m in modules_data
                ]
            }
        )

# --- Specialized Views (Users + Profiles) ---

class AdminUserListView(AdminModelListView):
    model = User
    list_display = ['username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    add_url_name = 'admin_user_add'
    change_url_name = 'admin_user_edit'
    change_password_url_name = 'admin_user_password'
    delete_url_name = 'admin_user_delete'


class AdminUserCreateView(AdminModelFormView, CreateView):
    model = User
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('admin_user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object

        # Ensure profile is created in line with user_type
        if user.user_type == 'Student':
            Student.objects.get_or_create(user=user)
        elif user.user_type == 'Lecturer':
            Lecturer.objects.get_or_create(user=user)
        return response


class AdminUserUpdateView(AdminModelFormView, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    success_url = reverse_lazy('admin_user_list')

    def form_valid(self, form):
        previous = self.get_object()
        previous_user_type = previous.user_type
        response = super().form_valid(form)
        new_user = self.object

        # Handle switching profiles when user_type changes
        if previous_user_type != new_user.user_type:
            if previous_user_type == 'Student' and hasattr(new_user, 'student_profile'):
                new_user.student_profile.delete()
            if previous_user_type == 'Lecturer' and hasattr(new_user, 'lecturer_profile'):
                new_user.lecturer_profile.delete()

            if new_user.user_type == 'Student':
                Student.objects.get_or_create(user=new_user)
            elif new_user.user_type == 'Lecturer':
                Lecturer.objects.get_or_create(user=new_user)

        return response


class AdminUserPasswordChangeView(AdminRequiredMixin, FormView):
    template_name = 'admin/user_password_form.html'
    form_class = SetPasswordForm
    success_url = reverse_lazy('admin_user_list')

    def dispatch(self, request, *args, **kwargs):
        self.user_obj = get_object_or_404(User, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.user_obj
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'model_name': 'User',
                'user_obj': self.user_obj,
                'list_url_name': 'admin_user_list',
            }
        )
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Password updated for {self.user_obj.username}.")
        return response


class AdminUserDeleteView(AdminModelDeleteView):
    model = User


# --- Group / Permission Views (to mirror Django admin capabilities) ---

class AdminGroupListView(AdminModelListView):
    model = Group
    search_fields = ['name']
    add_url_name = 'admin_group_add'
    change_url_name = 'admin_group_edit'
    delete_url_name = 'admin_group_delete'


class AdminGroupCreateView(AdminModelFormView, CreateView):
    model = Group
    fields = '__all__'


class AdminGroupUpdateView(AdminModelFormView, UpdateView):
    model = Group
    fields = '__all__'


class AdminGroupDeleteView(AdminModelDeleteView):
    model = Group


class AdminPermissionListView(AdminModelListView):
    model = Permission
    search_fields = ['name', 'codename', 'content_type__app_label']
    add_url_name = 'admin_permission_add'
    change_url_name = 'admin_permission_edit'
    delete_url_name = 'admin_permission_delete'


class AdminPermissionCreateView(AdminModelFormView, CreateView):
    model = Permission
    fields = '__all__'


class AdminPermissionUpdateView(AdminModelFormView, UpdateView):
    model = Permission
    fields = '__all__'


class AdminPermissionDeleteView(AdminModelDeleteView):
    model = Permission


# --- Student / Lecturer Views ---

class AdminStudentListView(AdminModelListView):
    model = Student
    list_display = ['user__username', 'user__first_name', 'user__last_name', 'program']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'program']
    add_url_name = 'admin_student_add'
    change_url_name = 'admin_student_edit'
    delete_url_name = 'admin_student_delete'


class AdminStudentCreateView(AdminRequiredMixin, TemplateView):
    template_name = 'admin/student_form.html'

    def get(self, request, *args, **kwargs):
        context = {
            'user_form': CustomUserCreationForm(initial={'user_type': 'Student'}),
            'student_form': StudentForm(),
        }
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        user_form = CustomUserCreationForm(request.POST)
        student_form = StudentForm(request.POST)
        if user_form.is_valid() and student_form.is_valid():
            user = user_form.save(commit=False)
            user.user_type = 'Student'
            # Students are not site administrators; keep is_staff False by default.
            user.is_staff = False
            user.save()

            student = student_form.save(commit=False)
            student.user = user
            student.save()

            # Ensure m2m fields (like modules) are saved and trigger the m2m signal
            if hasattr(student_form, 'save_m2m'):
                student_form.save_m2m()

            messages.success(request, 'Student created successfully.')
            return redirect('admin_student_list')

        messages.error(request, 'There were problems creating the student. Please check the form below.')
        return self.render_to_response({
            'user_form': user_form,
            'student_form': student_form,
        })


class AdminStudentUpdateView(AdminRequiredMixin, TemplateView):
    template_name = 'admin/student_form.html'

    def get_object(self):
        return Student.objects.select_related('user').get(pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        student = self.get_object()
        context = {
            'user_form': CustomUserChangeForm(instance=student.user),
            'student_form': StudentForm(instance=student),
            'is_update': True,
        }
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        student = self.get_object()
        user_form = CustomUserChangeForm(request.POST, instance=student.user)
        student_form = StudentForm(request.POST, instance=student)
        if user_form.is_valid() and student_form.is_valid():
            user = user_form.save()
            student_form.save()
            # Ensure profile mapping stays consistent
            if user.user_type != 'Student' and hasattr(user, 'student_profile'):
                user.student_profile.delete()
            if user.user_type == 'Student' and not hasattr(user, 'student_profile'):
                Student.objects.create(user=user)
            messages.success(request, 'Student updated successfully.')
            return redirect('admin_student_list')

        return self.render_to_response({
            'user_form': user_form,
            'student_form': student_form,
            'is_update': True,
        })


class AdminStudentDeleteView(AdminModelDeleteView):
    model = Student


class AdminLecturerListView(AdminModelListView):
    model = Lecturer
    list_display = ['user__username', 'user__first_name', 'user__last_name', 'department']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'department']
    add_url_name = 'admin_lecturer_add'
    change_url_name = 'admin_lecturer_edit'
    delete_url_name = 'admin_lecturer_delete'


class AdminLecturerCreateView(AdminRequiredMixin, TemplateView):
    template_name = 'admin/lecturer_form.html'

    def get(self, request, *args, **kwargs):
        context = {
            'user_form': CustomUserCreationForm(initial={'user_type': 'Lecturer'}),
            'lecturer_form': LecturerForm(),
        }
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        user_form = CustomUserCreationForm(request.POST)
        lecturer_form = LecturerForm(request.POST)
        if user_form.is_valid() and lecturer_form.is_valid():
            user = user_form.save(commit=False)
            user.user_type = 'Lecturer'
            # Lecturers typically are not site administrators.
            user.is_staff = False
            user.save()
            lecturer = lecturer_form.save(commit=False)
            lecturer.user = user
            lecturer.save()
            messages.success(request, 'Lecturer created successfully.')
            return redirect('admin_lecturer_list')

        messages.error(request, 'There were problems creating the lecturer. Please check the form below.')
        return self.render_to_response({
            'user_form': user_form,
            'lecturer_form': lecturer_form,
        })


class AdminLecturerUpdateView(AdminRequiredMixin, TemplateView):
    template_name = 'admin/lecturer_form.html'

    def get_object(self):
        return Lecturer.objects.select_related('user').get(pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        lecturer = self.get_object()
        context = {
            'user_form': CustomUserChangeForm(instance=lecturer.user),
            'lecturer_form': LecturerForm(instance=lecturer),
            'is_update': True,
        }
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        lecturer = self.get_object()
        user_form = CustomUserChangeForm(request.POST, instance=lecturer.user)
        lecturer_form = LecturerForm(request.POST, instance=lecturer)
        if user_form.is_valid() and lecturer_form.is_valid():
            user = user_form.save()
            lecturer_form.save()
            if user.user_type != 'Lecturer' and hasattr(user, 'lecturer_profile'):
                user.lecturer_profile.delete()
            if user.user_type == 'Lecturer' and not hasattr(user, 'lecturer_profile'):
                Lecturer.objects.create(user=user)
            messages.success(request, 'Lecturer updated successfully.')
            return redirect('admin_lecturer_list')

        return self.render_to_response({
            'user_form': user_form,
            'lecturer_form': lecturer_form,
            'is_update': True,
        })


class AdminLecturerDeleteView(AdminModelDeleteView):
    model = Lecturer


# --- Other models managed by generic views ---

class AdminModuleListView(AdminModelListView):
    model = Module
    search_fields = ['module_code', 'module_name']
    add_url_name = 'admin_module_add'
    change_url_name = 'admin_module_edit'
    delete_url_name = 'admin_module_delete'


class AdminModuleCreateView(AdminModelFormView, CreateView):
    model = Module
    form_class = ModuleForm


class AdminModuleUpdateView(AdminModelFormView, UpdateView):
    model = Module
    form_class = ModuleForm


class AdminModuleDeleteView(AdminModelDeleteView):
    model = Module


class AdminProgramListView(AdminModelListView):
    model = Program
    search_fields = ['program_code', 'program_name']
    add_url_name = 'admin_program_add'
    change_url_name = 'admin_program_edit'
    delete_url_name = 'admin_program_delete'


class AdminProgramCreateView(AdminModelFormView, CreateView):
    model = Program
    fields = '__all__'


class AdminProgramUpdateView(AdminModelFormView, UpdateView):
    model = Program
    fields = '__all__'


class AdminProgramDeleteView(AdminModelDeleteView):
    model = Program


class AdminCourseListView(AdminModelListView):
    model = Course
    search_fields = ['course_code', 'course_name']
    add_url_name = 'admin_course_add'
    change_url_name = 'admin_course_edit'
    delete_url_name = 'admin_course_delete'


class AdminCourseCreateView(AdminModelFormView, CreateView):
    model = Course
    form_class = CourseForm


class AdminCourseUpdateView(AdminModelFormView, UpdateView):
    model = Course
    form_class = CourseForm


class AdminCourseDeleteView(AdminModelDeleteView):
    model = Course


class AdminEnrollmentListView(AdminModelListView):
    model = Enrollment
    search_fields = ['student__user__username', 'course__course_code']
    add_url_name = 'admin_enrollment_add'
    change_url_name = 'admin_enrollment_edit'
    delete_url_name = 'admin_enrollment_delete'


class AdminEnrollmentCreateView(AdminModelFormView, CreateView):
    model = Enrollment
    form_class = EnrollmentForm


class AdminEnrollmentUpdateView(AdminModelFormView, UpdateView):
    model = Enrollment
    form_class = EnrollmentForm


class AdminEnrollmentDeleteView(AdminModelDeleteView):
    model = Enrollment


class AdminClassSessionListView(AdminModelListView):
    model = ClassSession
    search_fields = ['course__course_code', 'lecturer__user__username', 'module__module_code']
    add_url_name = 'admin_classsession_add'
    change_url_name = 'admin_classsession_edit'
    delete_url_name = 'admin_classsession_delete'


class AdminClassSessionCreateView(AdminModelFormView, CreateView):
    model = ClassSession
    form_class = ClassSessionForm


class AdminClassSessionUpdateView(AdminModelFormView, UpdateView):
    model = ClassSession
    form_class = ClassSessionForm


class AdminClassSessionDeleteView(AdminModelDeleteView):
    model = ClassSession


class AdminAttendanceListView(AdminModelListView):
    model = Attendance
    search_fields = ['student__user__username', 'session__course__course_code']
    add_url_name = 'admin_attendance_add'
    change_url_name = 'admin_attendance_edit'
    delete_url_name = 'admin_attendance_delete'


class AdminAttendanceCreateView(AdminModelFormView, CreateView):
    model = Attendance
    form_class = AttendanceForm


class AdminAttendanceUpdateView(AdminModelFormView, UpdateView):
    model = Attendance
    form_class = AttendanceForm


class AdminAttendanceDeleteView(AdminModelDeleteView):
    model = Attendance


class AdminFaceEncodingListView(AdminModelListView):
    model = FaceEncoding
    search_fields = ['student__user__username']
    add_url_name = 'admin_faceencoding_add'
    change_url_name = 'admin_faceencoding_edit'
    delete_url_name = 'admin_faceencoding_delete'


class AdminFaceEncodingCreateView(AdminModelFormView, CreateView):
    model = FaceEncoding
    fields = '__all__'


class AdminFaceEncodingUpdateView(AdminModelFormView, UpdateView):
    model = FaceEncoding
    fields = '__all__'


class AdminFaceEncodingDeleteView(AdminModelDeleteView):
    model = FaceEncoding
