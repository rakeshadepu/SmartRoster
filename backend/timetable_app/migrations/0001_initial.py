

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Organisation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('shop_open', models.TimeField(default='08:00', help_text='Daily opening time (HH:MM)')),
                ('shop_close', models.TimeField(default='20:00', help_text='Daily closing time (HH:MM)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Organisation',
                'verbose_name_plural': 'Organisations',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Timetable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week_start', models.DateField(help_text='Monday of the timetable week')),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('PUBLISHED', 'Published')], default='DRAFT', max_length=20)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timetables', to='timetable_app.organisation')),
            ],
            options={
                'verbose_name': 'Timetable',
                'verbose_name_plural': 'Timetables',
                'ordering': ['-week_start'],
                'unique_together': {('org', 'week_start')},
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('user_id', models.CharField(db_index=True, editable=False, help_text='Auto-generated 11-char Base64url unique identifier', max_length=11, unique=True)),
                ('full_name', models.CharField(max_length=150)),
                ('role', models.CharField(choices=[('EMPLOYEE', 'Employee (Manager)'), ('WORKER', 'Worker')], default='WORKER', max_length=20)),
                ('work_type', models.CharField(blank=True, choices=[('FULL_TIME', 'Full Time'), ('PART_TIME', 'Part Time'), ('MINIJOB', 'Mini Job')], help_text='Only relevant for WORKER role', max_length=20, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plain_password', models.CharField(blank=True, help_text='Shown once to employee on worker creation, then cleared', max_length=50, null=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('org', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='users', to='timetable_app.organisation')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'User',
                'verbose_name_plural': 'Users',
                'ordering': ['full_name'],
            },
        ),
        migrations.CreateModel(
            name='WorkTypeLimit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('work_type', models.CharField(choices=[('FULL_TIME', 'Full Time'), ('PART_TIME', 'Part Time'), ('MINIJOB', 'Mini Job')], max_length=20)),
                ('hours_per_week', models.PositiveSmallIntegerField(help_text='Maximum working hours per week for this employment type')),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='work_limits', to='timetable_app.organisation')),
            ],
            options={
                'verbose_name': 'Work Type Limit',
                'verbose_name_plural': 'Work Type Limits',
                'unique_together': {('org', 'work_type')},
            },
        ),
        migrations.CreateModel(
            name='Shift',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.CharField(choices=[('MON', 'Monday'), ('TUE', 'Tuesday'), ('WED', 'Wednesday'), ('THU', 'Thursday'), ('FRI', 'Friday'), ('SAT', 'Saturday'), ('SUN', 'Sunday')], max_length=3)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('hours', models.DecimalField(decimal_places=2, help_text='Calculated shift duration in hours', max_digits=4)),
                ('timetable', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shifts', to='timetable_app.timetable')),
                ('worker', models.ForeignKey(limit_choices_to={'role': 'WORKER'}, on_delete=django.db.models.deletion.CASCADE, related_name='shifts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Shift',
                'verbose_name_plural': 'Shifts',
                'ordering': ['day', 'start_time'],
                'unique_together': {('timetable', 'worker', 'day')},
            },
        ),
        migrations.CreateModel(
            name='Availability',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week_start', models.DateField(help_text='Monday of the target week')),
                ('day', models.CharField(choices=[('MON', 'Monday'), ('TUE', 'Tuesday'), ('WED', 'Wednesday'), ('THU', 'Thursday'), ('FRI', 'Friday'), ('SAT', 'Saturday'), ('SUN', 'Sunday')], max_length=3)),
                ('start_time', models.TimeField(help_text='Preferred start time on this day')),
                ('submitted_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('worker', models.ForeignKey(limit_choices_to={'role': 'WORKER'}, on_delete=django.db.models.deletion.CASCADE, related_name='availabilities', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Availability',
                'verbose_name_plural': 'Availabilities',
                'ordering': ['week_start', 'day', 'worker__full_name'],
                'unique_together': {('worker', 'week_start', 'day')},
            },
        ),
    ]
