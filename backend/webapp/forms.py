# academics/forms.py

from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Student, Lecturer, Course, Enrollment, ClassSession, Attendance, Module



class AnnouncementForm(forms.Form):
    
    course_code = forms.ChoiceField(
        label="Select Course (or leave blank for all your Modules)",
        required=False,
        choices=[],  
        widget=forms.Select(attrs={'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm'})
    )
    
    subject = forms.CharField(
        label="Subject",
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm', 'placeholder': 'e.g., Class Cancellation: DBP316D'})
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={'rows': 8, 'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm', 'placeholder': 'Dear students, please be advised that...'}),
        help_text="Write your announcement here. It will be sent to all students enrolled in the selected course(s)."
    )








# --- 1. User Forms (for custom User model) ---

class CustomUserCreationForm(UserCreationForm):
    """
    A form for creating new users, with all the fields from our custom User model.
    Inherits from Django's UserCreationForm for handling password hashing and verification.
    """
    class Meta:
        model = User
 
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
       
        pass

class CustomUserChangeForm(UserChangeForm):
    """
    A form for updating existing users, with all the fields from our custom User model.
    Inherits from Django's UserChangeForm.
    """
    class Meta:
        model = User
        
        fields = '__all__'  

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
      
        pass


# --- 2. Student Form ---
class StudentForm(forms.ModelForm):
    """
    Form for creating and updating Student profiles.
    Note: The 'user' field (the OneToOneField) is typically handled separately
    when creating a new student, often by creating the User first and then the Student profile.
    For existing students, this form can be used to update their profile specific details.
    """
    class Meta:
        model = Student
  
        exclude = ('user',)
       
        labels = {
            'program': 'Course',
            'parent_email': 'Parent/Guardian Email',
            'parent_phone_num': 'Parent/Guardian Phone Number',
        }
        widgets = {
            'program': forms.TextInput(attrs={'placeholder': 'e.g., Computer Science'}),
            'parent_email': forms.EmailInput(attrs={'placeholder': 'parent@mail.com'}),
            'parent_phone_num': forms.TextInput(attrs={'placeholder': '+27123456789'}),
        }


# --- 3. Lecturer Form ---
class LecturerForm(forms.ModelForm):
    """Form for creating and updating Lecturer profiles.
    Similar to StudentForm, the 'user' field is typically excluded."""

    class Meta:
        model = Lecturer
        exclude = ('user',)

        labels = {
            'department': 'Department',
        }
        widgets = {
            'department': forms.TextInput(attrs={'placeholder': 'e.g., Electrical Engineering'}),
        }


class ModuleForm(forms.ModelForm):
    """Form for creating/updating modules with the ability to assign lecturers."""

    lecturers = forms.ModelMultipleChoiceField(
        queryset=Lecturer.objects.all(),
        required=False,
        widget=FilteredSelectMultiple('Lecturers', is_stacked=False),
        help_text='Select one or more lecturers who teach this module.',
    )

    class Meta:
        model = Module
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['lecturers'].initial = self.instance.lecturers.all()

    def save(self, commit=True):
        module = super().save(commit=commit)
        if commit:
            module.lecturers.set(self.cleaned_data.get('lecturers'))
        else:
            def save_m2m():
                module.lecturers.set(self.cleaned_data.get('lecturers'))
            self.save_m2m = save_m2m
        return module


# --- 4. Course Form ---
class CourseForm(forms.ModelForm):
    """Form for creating and updating Courses."""

    class Meta:
        model = Course
        fields = '__all__'
        labels = {
            'course_code': 'Course Code',
            'course_name': 'Course Name',
            'modules': 'Modules',
        }
        widgets = {
            'course_code': forms.TextInput(attrs={'placeholder': 'e.g., CSC101'}),
            'course_name': forms.TextInput(attrs={'placeholder': 'e.g., Introduction to Programming'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Force module selection in the admin form
        self.fields['modules'].required = True

    def clean(self):
        cleaned_data = super().clean()
        modules = cleaned_data.get('modules')
        if not modules or len(modules) == 0:
            raise forms.ValidationError("Please select at least one module for this course.")
        return cleaned_data


# --- 5. Enrollment Form ---
class EnrollmentForm(forms.ModelForm):
    """Form for managing student enrollments in courses."""

    class Meta:
        model = Enrollment
        fields = '__all__'
        labels = {
            'student': 'Student',
            'course': 'Course',
            'modules': 'Modules',
            'enrollment_date': 'Enrollment Date',
        }
        widgets = {
            'enrollment_date': forms.DateInput(attrs={'type': 'date'}),  # HTML5 date picker
        }

    class Media:
        js = ('webapp/js/enrollment_modules.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure student/course/modules are selectable in the admin form
        # Provide friendly labels for student choices (username - full name)
        self.fields['student'].queryset = Student.objects.select_related('user').order_by('user__username')
        try:
            # Provide a readable label for student choices
            self.fields['student'].label_from_instance = lambda obj: f"{obj.user.username} - {obj.user.get_full_name()}"
        except Exception:
            pass

        # Order courses for easier selection
        self.fields['course'].queryset = Course.objects.all().order_by('course_code')

        # Make modules required and use admin-friendly multi-select widget
        self.fields['modules'].required = True
        self.fields['modules'].widget = FilteredSelectMultiple('Modules', is_stacked=False)
        # Ensure modules queryset is available so JS can populate it correctly
        self.fields['modules'].queryset = Module.objects.all().order_by('module_code')

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        modules = cleaned_data.get('modules')

        if course and modules:
            invalid_modules = [m for m in modules if m not in course.modules.all()]
            if invalid_modules:
                raise forms.ValidationError(
                    "Selected module(s) must belong to the selected course."
                )
        elif course and (not modules or len(modules) == 0):
            # Try auto-select if only one module belongs to the course
            course_modules = list(course.modules.all())
            if len(course_modules) == 1:
                cleaned_data['modules'] = course_modules
            else:
                raise forms.ValidationError(
                    "Please select at least one module for this enrollment."
                )

        return cleaned_data


# --- 6. ClassSession Form ---
class ClassSessionForm(forms.ModelForm):
    """
    Form for scheduling and updating class sessions.
    """
    class Meta:
        model = ClassSession
        exclude = ['lecturer']  
        labels = {
            'day_of_week': 'Day of Week',
            'start_time': 'Start Time',
            'end_time': 'End Time',
        }
        widgets = {
            'day_of_week': forms.Select(choices=ClassSession.day_of_week.field.choices),  
            'start_time': forms.TimeInput(attrs={'type': 'time'}),  
            'end_time': forms.TimeInput(attrs={'type': 'time'}),    
            'room': forms.TextInput(attrs={'placeholder': 'e.g., Room A101, Zoom Link'}),
        }
 
    def __init__(self, *args, **kwargs):
        #  
        self.lecturer_profile = kwargs.pop('lecturer_profile', None)
        super().__init__(*args, **kwargs)

 
        if self.lecturer_profile:
            # Courses are now associated via Modules, and Lecturers are assigned to Modules.
            # Show only courses that include at least one module taught by this lecturer.
            lecturer_modules = self.lecturer_profile.modules.all()
            self.fields['course'].queryset = Course.objects.filter(
                modules__in=lecturer_modules
            ).distinct()

            # Show only the lecturer's modules in the module dropdown.
            if 'module' in self.fields:
                self.fields['module'].queryset = lecturer_modules

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        module = cleaned_data.get('module')

        if course and module:
            # Ensure the module is part of the selected course
            if module not in course.modules.all():
                raise forms.ValidationError("Selected module does not belong to the selected course.")

            # Ensure module is assigned to the lecturer
            if self.lecturer_profile and module not in self.lecturer_profile.modules.all():
                raise forms.ValidationError("You can only schedule sessions for modules assigned to you.")

        # Require module selection if course is selected
        if course and not module:
            raise forms.ValidationError("Please select a module for this class session.")

        return cleaned_data

# --- 7. Attendance Form ---
class AttendanceForm(forms.ModelForm):
    """
    Form for recording student attendance for sessions.
    """
    class Meta:
        model = Attendance
 
        fields = ('student', 'session', 'status', 'image_data')
        labels = {
            'student': 'Student',
            'session': 'Class Session',
            'status': 'Attendance Status',
            'image_data': 'Verification Image',
        }
        widgets = {
            'status': forms.Select(choices=Attendance.status.field.choices),
        }
    
    
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data