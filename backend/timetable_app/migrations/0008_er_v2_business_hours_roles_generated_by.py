# Generated for ER v2: BusinessHours, multi-role Users, Timetable.generated_by,
# ARCHIVED status, Availability.week_number.
#
# Ordering matters here: BusinessHours is created and *backfilled* from the
# old Organisation.shop_open/shop_close values before those columns are
# dropped, and Availability.week_number is backfilled from week_start
# (instead of the blunt default=1 Django would otherwise use for every
# existing row).

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


DAY_CODES = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']


def backfill_business_hours(apps, schema_editor):
    """Copy each org's old flat shop_open/shop_close into 7 BusinessHours rows."""
    Organisation = apps.get_model('timetable_app', 'Organisation')
    BusinessHours = apps.get_model('timetable_app', 'BusinessHours')
    for org in Organisation.objects.all():
        BusinessHours.objects.bulk_create([
            BusinessHours(
                org=org,
                day_of_week=day,
                open_time=org.shop_open,
                close_time=org.shop_close,
            )
            for day in DAY_CODES
        ])


def noop_reverse_business_hours(apps, schema_editor):
    # shop_open/shop_close are recreated (with their defaults) by the
    # reverse of the later RemoveField ops, so there's nothing to restore
    # into them here — this migration is not meant to be reversed in prod.
    pass


def backfill_week_number(apps, schema_editor):
    """Derive week_number from week_start's ISO calendar for existing rows."""
    Availability = apps.get_model('timetable_app', 'Availability')
    for avail in Availability.objects.all():
        avail.week_number = avail.week_start.isocalendar()[1]
        avail.save(update_fields=['week_number'])


def noop_reverse_week_number(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('timetable_app', '0007_alter_jobhistory_options_and_more'),
    ]

    operations = [
        # -- 1. Create BusinessHours, backfill from Organisation, then drop old fields --
        migrations.CreateModel(
            name='BusinessHours',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day_of_week', models.CharField(choices=[('MON', 'Monday'), ('TUE', 'Tuesday'), ('WED', 'Wednesday'), ('THU', 'Thursday'), ('FRI', 'Friday'), ('SAT', 'Saturday'), ('SUN', 'Sunday')], max_length=3)),
                ('open_time', models.TimeField(default='08:00', help_text='Opening time (HH:MM) — no shift may start before this')),
                ('close_time', models.TimeField(default='20:00', help_text='Closing time (HH:MM) — no shift may end after this')),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='business_hours', to='timetable_app.organisation')),
            ],
            options={
                'verbose_name': 'Business Hours',
                'verbose_name_plural': 'Business Hours',
                'ordering': ['org', 'day_of_week'],
                'unique_together': {('org', 'day_of_week')},
            },
        ),
        migrations.RunPython(backfill_business_hours, noop_reverse_business_hours),
        migrations.RemoveField(
            model_name='organisation',
            name='shop_close',
        ),
        migrations.RemoveField(
            model_name='organisation',
            name='shop_open',
        ),

        # -- 2. Availability.week_number, backfilled from week_start --
        migrations.AddField(
            model_name='availability',
            name='week_number',
            field=models.PositiveSmallIntegerField(blank=True, default=1, editable=False, help_text='ISO week-of-year for week_start (1-53) — auto-derived on save'),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_week_number, noop_reverse_week_number),

        # -- 3. Timetable.generated_by + ARCHIVED status --
        migrations.AddField(
            model_name='timetable',
            name='generated_by',
            field=models.ForeignKey(blank=True, help_text='The ADMIN/MANAGER user who triggered generation, if any', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_timetables', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='timetable',
            name='status',
            field=models.CharField(choices=[('DRAFT', 'Draft'), ('PUBLISHED', 'Published'), ('ARCHIVED', 'Archived')], default='DRAFT', max_length=20),
        ),

        # -- 4. User.employee_code + expanded roles --
        migrations.AddField(
            model_name='user',
            name='employee_code',
            field=models.CharField(blank=True, help_text='Org-facing employee code/badge number, e.g. for payroll or a badge', max_length=30, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('ADMIN', 'Admin'), ('MANAGER', 'Manager'), ('WORKER', 'Worker')], default='WORKER', max_length=20),
        ),
    ]
