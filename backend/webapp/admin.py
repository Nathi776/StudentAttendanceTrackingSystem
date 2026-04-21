 

from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db import IntegrityError  
from django.contrib import messages
from django.http import JsonResponse
from django.urls import path

from .models import User, Student, Lecturer, Module, Course, Enrollment, ClassSession, Attendance
from .forms import CourseForm, EnrollmentForm, ModuleForm

class StudentInline(admin.StackedInline):
    model = Student
    can_delete = False
    verbose_name_plural = 'Student Profile'
    fk_name = 'user'

class LecturerInline(admin.StackedInline):
    model = Lecturer
    can_delete = False
    verbose_name_plural = 'Lecturer Profile'
    fk_name = 'user'

class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff', 'is_active')
    list_filter = ('user_type', 'is_staff', 'is_active')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'user_type')}),
        (('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions'),
        }),
        (('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'user_type', 'password1', 'password2'),
        }),
    )

    inlines = [StudentInline, LecturerInline]

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        
        if obj.user_type == 'Student':
            return [StudentInline(self.model, self.admin_site)]
        elif obj.user_type == 'Lecturer':
            return [LecturerInline(self.model, self.admin_site)]
        return []

    def save_model(self, request, obj, form, change):
        # Save the User object first
        super().save_model(request, obj, form, change)

        if change: # If an existing user is being modified
            old_user_type = User.objects.get(pk=obj.pk).user_type
            new_user_type = obj.user_type

            if old_user_type != new_user_type:
                # Try to delete the old profile (if it exists and matches old_user_type)
                try:
                    if old_user_type == 'Student' and hasattr(obj, 'student_profile'):
                        obj.student_profile.delete()
                        messages.info(request, f"Old Student profile deleted for {obj.username}.")
                    elif old_user_type == 'Lecturer' and hasattr(obj, 'lecturer_profile'):
                        obj.lecturer_profile.delete()
                        messages.info(request, f"Old Lecturer profile deleted for {obj.username}.")
                except Exception as e:
                    messages.error(request, f"Error deleting old profile ({old_user_type}) for {obj.username}: {e}")

                # Attempt to create the new profile only if it doesn't already exist
                if new_user_type == 'Student' and not hasattr(obj, 'student_profile'):
                    try:
                        Student.objects.create(user=obj)
                        messages.success(request, f"New Student profile created for {obj.username}.")
                    except IntegrityError:
                        messages.warning(request, f"A Student profile for {obj.username} already exists (IntegrityError).")
                    except Exception as e:
                        messages.error(request, f"Error creating new Student profile for {obj.username}: {e}")
                elif new_user_type == 'Lecturer' and not hasattr(obj, 'lecturer_profile'):
                    try:
                        Lecturer.objects.create(user=obj)
                        messages.success(request, f"New Lecturer profile created for {obj.username}.")
                    except IntegrityError:
                        messages.warning(request, f"A Lecturer profile for {obj.username} already exists (IntegrityError).")
                    except Exception as e:
                        messages.error(request, f"Error creating new Lecturer profile for {obj.username}: {e}")
                elif new_user_type == 'Admin':
                    messages.info(request, f"User type for {obj.username} set to Admin.")

        else:  
              
            # If this is a new user, create the appropriate profile based on user_type
            if obj.user_type == 'Student' and not hasattr(obj, 'student_profile'):
                try:
                    Student.objects.create(user=obj)
                    messages.success(request, f"Initial Student profile created for {obj.username}.")
                except IntegrityError:
                    messages.warning(request, f"Student profile for {obj.username} already exists (IntegrityError during initial create).")
                except Exception as e:
                    messages.error(request, f"Error creating initial Student profile for {obj.username}: {e}. Check if Student model has required fields other than 'user'.")
            elif obj.user_type == 'Lecturer' and not hasattr(obj, 'lecturer_profile'):
                try:
                    Lecturer.objects.create(user=obj)
                    messages.success(request, f"Initial Lecturer profile created for {obj.username}.")
                except IntegrityError:
                    messages.warning(request, f"Lecturer profile for {obj.username} already exists (IntegrityError during initial create).")
                except Exception as e:
                    messages.error(request, f"Error creating initial Lecturer profile for {obj.username}: {e}. Check if Lecturer model has required fields other than 'user'.")
             

 
admin.site.register(User, CustomUserAdmin)


class ModuleAdmin(admin.ModelAdmin):
    form = ModuleForm
    list_display = ('module_code', 'module_name')
    search_fields = ('module_code', 'module_name')


class CourseAdmin(admin.ModelAdmin):
    form = CourseForm
    list_display = ('course_code', 'course_name', 'module_list')
    search_fields = ('course_code', 'course_name')

    def module_list(self, obj):
        return ", ".join([m.module_code for m in obj.modules.all()])
    module_list.short_description = 'Modules'


class EnrollmentAdmin(admin.ModelAdmin):
    form = EnrollmentForm
    list_display = ('student', 'course', 'module_list', 'enrollment_date')
    list_filter = ('modules', 'enrollment_date')
    search_fields = ('student__user__username', 'course__course_code', 'modules__module_code')
    filter_horizontal = ('modules',)

    def module_list(self, obj):
        return ", ".join([m.module_code for m in obj.modules.all()])
    module_list.short_description = 'Modules'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'modules-for-course/',
                self.admin_site.admin_view(self.modules_for_course),
                name='webapp_enrollment_modules_for_course',
            ),
        ]
        return custom_urls + urls

    def modules_for_course(self, request):
        course_id = request.GET.get('course_id')
        data = {'modules': []}
        if course_id:
            try:
                course = Course.objects.get(pk=course_id)
                data['modules'] = [
                    {'id': m.pk, 'code': m.module_code, 'name': m.module_name}
                    for m in course.modules.all()
                ]
            except Course.DoesNotExist:
                pass
        return JsonResponse(data)


class LecturerAdmin(admin.ModelAdmin):
    list_display = ('user', 'department')
    filter_horizontal = ('modules',)


class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'program')
    filter_horizontal = ('modules',)


admin.site.register(Module, ModuleAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(Lecturer, LecturerAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(ClassSession)
admin.site.register(Attendance)

try:
    admin.site.unregister(Group)
except NotRegistered:
    pass

from .models import FaceEncoding
admin.site.register(FaceEncoding)
