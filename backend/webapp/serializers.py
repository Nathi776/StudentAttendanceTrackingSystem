from rest_framework import serializers
from .models import User, Student, Lecturer, Module, Course, Enrollment, ClassSession, Attendance


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'user_type']


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['module_code', 'module_name']


class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    modules = ModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = ['user', 'program', 'modules', 'parent_email', 'parent_phone_num']


class LecturerSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    modules = ModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Lecturer
        fields = ['user', 'department', 'modules']


class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ['course_code', 'course_name', 'modules']


class ClassSessionSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    lecturer = LecturerSerializer(read_only=True)

    class Meta:
        model = ClassSession
        fields = [
            'id',
            'course',
            'lecturer',
            'day_of_week',
            'start_time',
            'end_time',
            'room',
        ]


class AttendanceSerializer(serializers.ModelSerializer):
    session = ClassSessionSerializer(read_only=True)

    class Meta:
        model = Attendance
        fields = ['id', 'session', 'date_time', 'status', 'image_data']


class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    modules = ModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'modules', 'enrollment_date']
