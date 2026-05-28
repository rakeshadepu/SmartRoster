# Migration 0003 — Add org_id field to Organisation
#
# This adds the 8-character Base64url public identifier used in all org URLs.
# The migration also auto-populates existing organisations with a generated org_id.
#
# TO APPLY:
#   cd backend
#   python manage.py migrate
#
# That's it — no other steps needed.

import secrets
import string

from django.db import migrations, models


BASE64URL_ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits + '-_'
ORG_ID_LENGTH = 8


def _generate_unique_org_id(existing_ids):
    """Generate an 8-char Base64url org_id not already in existing_ids."""
    while True:
        oid = ''.join(secrets.choice(BASE64URL_ALPHABET) for _ in range(ORG_ID_LENGTH))
        if oid not in existing_ids:
            existing_ids.add(oid)
            return oid


def populate_org_ids(apps, schema_editor):
    """
    Data migration: assign a unique org_id to every existing Organisation
    that doesn't have one yet (i.e. org_id is blank/empty after column add).
    """
    Organisation = apps.get_model('timetable_app', 'Organisation')
    existing_ids = set(
        Organisation.objects.exclude(org_id='').values_list('org_id', flat=True)
    )
    to_update = Organisation.objects.filter(org_id='')
    for org in to_update:
        org.org_id = _generate_unique_org_id(existing_ids)
        org.save(update_fields=['org_id'])


def reverse_populate(apps, schema_editor):
    """Reverse migration: clear all org_ids (idempotent)."""
    Organisation = apps.get_model('timetable_app', 'Organisation')
    Organisation.objects.all().update(org_id='')


class Migration(migrations.Migration):

    dependencies = [
        ('timetable_app', '0002_organisation_email_organisation_is_active_and_more'),
    ]

    operations = [
        # Step 1: Add the column (nullable/blank initially so existing rows are valid)
        migrations.AddField(
            model_name='organisation',
            name='org_id',
            field=models.CharField(
                max_length=8,
                unique=False,       # temporarily non-unique to allow bulk insert
                blank=True,
                default='',
                db_index=False,
                help_text='8-char Base64url public identifier used in all org URLs',
            ),
        ),

        # Step 2: Populate existing rows with generated org_ids
        migrations.RunPython(populate_org_ids, reverse_code=reverse_populate),

        # Step 3: Now enforce uniqueness and add the index
        migrations.AlterField(
            model_name='organisation',
            name='org_id',
            field=models.CharField(
                max_length=8,
                unique=True,
                blank=True,
                default='',
                db_index=True,
                help_text='8-char Base64url public identifier used in all org URLs',
            ),
        ),
    ]
