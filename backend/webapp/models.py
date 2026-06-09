 
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    user_type_choices = (
        ('Student', 'Student'),
        ('Lecturer', 'Lecturer'),
        ('Admin', 'Admin'),
    )
    user_type = models.CharField(max_length=10, choices=user_type_choices, default='Admin')

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='%(app_label)s_%(class)s_groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='%(app_label)s_%(class)s_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

# --- 2. Student Model (Profile linked to User) ---
class Student(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='student_profile',
        limit_choices_to={'user_type': 'Student'}
    )
    
    program = models.CharField(max_length=100, blank=True, null=True, verbose_name='Course') # <-- ADD blank=True, null=True
    modules = models.ManyToManyField(
        'Module',
        blank=True,
        related_name='students',
        help_text='Modules that this student is enrolled in.'
    )
    parent_email = models.EmailField(blank=True, null=True, help_text="Parent's email address.")
    parent_phone_num = models.CharField(max_length=20, blank=True, null=True, help_text="Parent's phone number.")

    def __str__(self):
        return f"Student: {self.user.first_name} {self.user.last_name} ({self.program or 'No Program'})" # Added 'or No Program' for string representation

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def last_name(self):
        return self.user.last_name

    @property
    def email(self):
        return self.user.email

    class Meta:
        verbose_name = _('student')
        verbose_name_plural = _('students')


# --- 3. Lecturer Model (Profile linked to User) ---
class Lecturer(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='lecturer_profile',
        limit_choices_to={'user_type': 'Lecturer'}
    )
    # Adding a department field to the Lecturer model
    department = models.CharField(max_length=100, blank=True, null=True) # <-- ADD blank=True, null=True
    modules = models.ManyToManyField(
        'Module',
        blank=True,
        related_name='lecturers',
        help_text='Modules that this lecturer is assigned to.'
    )

    def __str__(self):
        return f"Lecturer: {self.user.first_name} {self.user.last_name} ({self.department or 'No Department'})" # Added 'or No Department'

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def last_name(self):
        return self.user.last_name

    @property
    def email(self):
        return self.user.email

    class Meta:
        verbose_name = _('lecturer')
        verbose_name_plural = _('lecturers')
 
# --- 4. Module Model ---
class Module(models.Model):
    """Represents a teaching module or subject area."""
    module_code = models.CharField(max_length=20, primary_key=True, help_text="Unique code for the module.")
    module_name = models.CharField(max_length=255, help_text="Human-readable name for the module.")
    description = models.TextField(blank=True, null=True, help_text="Optional description or notes about the module.")

    class Meta:
        verbose_name = _('module')
        verbose_name_plural = _('modules')
        ordering = ['module_code']

    def __str__(self):
        return f"{self.module_code} - {self.module_name}"


# --- 5. Course Model ---
class Course(models.Model):
    """Represents an academic course."""
    course_code = models.CharField(max_length=20, primary_key=True, help_text="Unique code for the course.")
    course_name = models.CharField(max_length=255)
    modules = models.ManyToManyField(
        Module,
        blank=True,
        related_name='courses',
        help_text="Modules associated with this course (e.g., Year 1, Year 2, etc.)."
    )

    def __str__(self):
        module_codes = ", ".join([m.module_code for m in self.modules.all()]) if self.modules.exists() else ""
        module_part = f" ({module_codes})" if module_codes else ""
        return f"{self.course_code} - {self.course_name}{module_part}"

    class Meta:
        verbose_name = _('course')
        verbose_name_plural = _('courses')
        ordering = ['course_code']


# --- 5. Enrollment Model (Many-to-Many through table with extra data) ---
class Enrollment(models.Model):
    """Records a student's enrollment in a specific course.

    This acts as a junction table between Student and Course with additional attributes.

    Students may be enrolled in multiple modules for the same course.
    """

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='enrollments',
        help_text="The student enrolled."
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments',
        help_text="The course being enrolled in."
    )
    modules = models.ManyToManyField(
        Module,
        blank=True,
        related_name='enrollments',
        help_text="The module(s) the student is enrolled in for this course."
    )
    enrollment_date = models.DateField(auto_now_add=True, help_text="Date of enrollment.")

    class Meta:
        unique_together = ('student', 'course')
        verbose_name = _('enrollment')
        verbose_name_plural = _('enrollments')
        ordering = ['-enrollment_date']

    def __str__(self):
        module_codes = ", ".join([m.module_code for m in self.modules.all()]) if self.modules.exists() else ""
        module_part = f" ({module_codes})" if module_codes else ""
        return f"{self.student.user.get_full_name()} enrolled in {self.course.course_name}{module_part}"


# --- 6. ClassSession Model ---
class ClassSession(models.Model):
    """
    Defines a scheduled class session for a specific course.
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='class_sessions',
        help_text="The course this session belongs to."
    )
    module = models.ForeignKey(
        'Module',
        on_delete=models.CASCADE,
        related_name='class_sessions',
        null=True,
        blank=True,
        help_text="The specific module covered in this session."
    )
    lecturer = models.ForeignKey(
        Lecturer,
        on_delete=models.CASCADE,
        related_name='class_sessions_conducted',
        help_text="The lecturer conducting this session."
    )
    day_of_week = models.CharField(
        max_length=10,
        choices=[
            ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
            ('Thursday', 'Thursday'), ('Friday', 'Friday'),('Saturday', 'Saturday'),('Sunday', 'Sunday')
        ],
        help_text="Day of the week the session is held."
    )
    start_time = models.TimeField(help_text="Start time of the session.")
    end_time = models.TimeField(help_text="End time of the session.")
    room = models.CharField(max_length=50, help_text="Physical room or virtual link for the session.")

    class Meta:
        verbose_name = _('class session')
        verbose_name_plural = _('class sessions')
        ordering = ['day_of_week', 'start_time']
         

    def __str__(self):
        return f"{self.course.course_code} - {self.day_of_week} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')} ({self.room})"


# --- 7. Attendance Model ---
class Attendance(models.Model):
    """
    Records a student's attendance for a specific class session.
    """
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        help_text="The student whose attendance is being recorded."
    )
    session = models.ForeignKey(
        ClassSession,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        help_text="The class session for which attendance is recorded."
    )
    date_time = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=[
            ('Present', 'Present'),
            ('Absent', 'Absent'),
            ('Late', 'Late'),
        ],
        help_text="Attendance status (Present, Absent, Late)."
    )
    image_data = models.ImageField(
        upload_to='attendance_images/',
        blank=True,
        null=True,
        help_text="Optional image data for attendance verification."
    )

    class Meta:
        verbose_name = _('attendance')
        verbose_name_plural = _('attendance')
        ordering = ['-date_time']

    def __str__(self):
        from django.utils import timezone

        return f"{self.student.user.get_full_name()} - {self.session.course.course_name} - {timezone.localtime(self.date_time).strftime('%Y-%m-%d %H:%M')} ({self.status})"


# --- 8. FaceEncoding Model (AI feature: store face embeddings) ---
class FaceEncoding(models.Model):
    """Stores a student's face embedding (128-D vector) for recognition."""
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name='face_encoding',
        help_text='Student profile linked to this face encoding.'
    )
    # JSON list of floats (128 values)
    encoding = models.JSONField(help_text='Face embedding vector (length 128).')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"FaceEncoding for {self.student.user.get_full_name()}"


# --- Signals ---
from django.db.models.signals import m2m_changed
from django.dispatch import receiver


@receiver(m2m_changed, sender=Student.modules.through)
def sync_student_enrollments_with_modules(sender, instance, action, reverse, model, pk_set, **kwargs):
    """Keep Enrollment records in sync with the student's selected Modules.

    When an admin selects modules for a student, automatically create or remove
    Enrollment records for courses that belong to those modules.

    This ensures the "Enrollments" tab reflects the current module selections.
    """
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return

    student_modules = set(instance.modules.all())

    # Courses that belong to any of the student's selected modules
    desired_courses = Course.objects.filter(modules__in=student_modules).distinct()

    # Update existing enrollments
    for enrollment in Enrollment.objects.filter(student=instance).select_related('course'):
        shared_modules = list(enrollment.course.modules.filter(pk__in=[m.pk for m in student_modules]))
        if shared_modules:
            enrollment.modules.set(shared_modules)
        else:
            # Student no longer wants any module for this course
            enrollment.delete()

    # Create enrollments for courses that do not yet exist
    existing_course_codes = set(
        Enrollment.objects.filter(student=instance).values_list('course__course_code', flat=True)
    )
    for course in desired_courses:
        if course.course_code not in existing_course_codes:
            modules_to_assign = list(course.modules.filter(pk__in=[m.pk for m in student_modules]))
            enrollment = Enrollment.objects.create(student=instance, course=course)
            if modules_to_assign:
                enrollment.modules.set(modules_to_assign)
