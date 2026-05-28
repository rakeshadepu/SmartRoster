# Migration 0004 — Add owner_name, phone, country_code, address fields to Organisation
#
# TO APPLY:
#   cd backend
#   python manage.py migrate

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timetable_app', '0003_organisation_org_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='owner_name',
            field=models.CharField(blank=True, default='', max_length=150,
                                   help_text='Full name of the organisation owner/admin'),
        ),
        migrations.AddField(
            model_name='organisation',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=20,
                                   help_text='Phone digits only e.g. 17612345678'),
        ),
        migrations.AddField(
            model_name='organisation',
            name='country_code',
            field=models.CharField(blank=True, default='', max_length=6,
                                   help_text='Dial code e.g. +49'),
        ),
        migrations.AddField(
            model_name='organisation',
            name='house_number',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='organisation',
            name='street',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='organisation',
            name='city',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='organisation',
            name='country',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='organisation',
            name='zip_code',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
    ]
