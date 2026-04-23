from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('webapp', '0009_remove_program_model'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='attendance',
            unique_together=set(),
        ),
    ]
