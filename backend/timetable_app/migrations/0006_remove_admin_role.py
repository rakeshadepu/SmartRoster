# Migration 0006 — Remove ADMIN role from User model
# Deletes any existing ADMIN User rows and restricts role to EMPLOYEE/WORKER only.
# Run: python manage.py migrate

from django.db import migrations, models


def delete_admin_users(apps, schema_editor):
    """Remove all User rows with role='ADMIN' — org owners now live on Organisation."""
    User = apps.get_model('timetable_app', 'User')
    deleted, _ = User.objects.filter(role='ADMIN').delete()
    if deleted:
        print(f'  Deleted {deleted} ADMIN user row(s).')


def reverse_noop(apps, schema_editor):
    pass  # Cannot restore deleted users — irreversible


class Migration(migrations.Migration):

    dependencies = [
        ('timetable_app', '0005_user_fields_admin_role_jobhistory'),
    ]

    operations = [
        # Step 1: Delete existing ADMIN user rows
        migrations.RunPython(delete_admin_users, reverse_code=reverse_noop),

        # Step 2: Restrict role field to EMPLOYEE and WORKER only
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                max_length=20,
                default='WORKER',
                choices=[
                    ('EMPLOYEE', 'Employee (Manager)'),
                    ('WORKER',   'Worker'),
                ],
            ),
        ),
    ]
