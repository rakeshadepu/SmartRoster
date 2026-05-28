# Migration 0005 — Add ADMIN role, new User fields, JobHistory table
# Run: python manage.py migrate

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timetable_app', '0004_organisation_owner_phone_address'),
    ]

    operations = [
        # ── New User fields ───────────────────────────────────────────────
        migrations.AddField(
            model_name='user', name='first_name',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.AddField(
            model_name='user', name='last_name',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.AddField(
            model_name='user', name='email',
            field=models.EmailField(blank=True, null=True, unique=True,
                                    help_text='Globally unique email'),
        ),
        migrations.AddField(
            model_name='user', name='phone',
            field=models.CharField(blank=True, null=True, max_length=20, unique=True,
                                   help_text='Globally unique phone digits'),
        ),
        migrations.AddField(
            model_name='user', name='nationality',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='user', name='dob',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user', name='iban',
            field=models.CharField(blank=True, default='', max_length=34),
        ),
        migrations.AddField(
            model_name='user', name='bic',
            field=models.CharField(blank=True, default='', max_length=11),
        ),
        # ── Update role field to include ADMIN ────────────────────────────
        migrations.AlterField(
            model_name='user', name='role',
            field=models.CharField(
                max_length=20, default='WORKER',
                choices=[
                    ('ADMIN',    'Organisation Admin'),
                    ('EMPLOYEE', 'Employee (Manager)'),
                    ('WORKER',   'Worker'),
                ],
            ),
        ),
        # ── JobHistory table ──────────────────────────────────────────────
        migrations.CreateModel(
            name='JobHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('work_type',  models.CharField(blank=True, default='', max_length=20)),
                ('joined_at',  models.DateTimeField(auto_now_add=True)),
                ('left_at',    models.DateTimeField(blank=True, null=True)),
                ('is_current', models.BooleanField(default=True)),
                ('org', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='job_history',
                    to='timetable_app.organisation')),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='job_history',
                    to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_employments',
                    to='timetable_app.organisation')),
            ],
            options={'ordering': ['-joined_at']},
        ),
    ]
