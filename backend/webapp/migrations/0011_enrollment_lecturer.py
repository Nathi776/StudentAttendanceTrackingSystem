from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('webapp', '0010_alter_attendance_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='lecturer',
            field=models.ForeignKey(blank=True, help_text='The lecturer this student is enrolled under for the course.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='enrollments', to='webapp.lecturer'),
        ),
        migrations.AlterUniqueTogether(
            name='enrollment',
            unique_together={('student', 'course', 'lecturer')},
        ),
    ]
