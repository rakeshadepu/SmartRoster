"""
signals.py — Timetable Planner Phase 1

Handles automatic generation of:
  - user_id  : 11-character Base64url unique identifier
  - password : random secure password shown once to the employee

Signal flow:
    Employee POSTs to /api/workers/  →  WorkerCreateView saves User
    →  pre_save fires: assigns user_id if not already set
    →  pre_save fires: generates plain_password + hashes it (new workers only)
    →  User row is written to DB
    →  View reads plain_password from instance, sends it in response ONCE
    →  View calls  User.objects.filter(pk=...).update(plain_password=None)
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver


@receiver(pre_save, sender='timetable_app.User')
def assign_user_id(sender, instance, **kwargs):
    """
    Before saving a User, assign a unique Base64url user_id if not already set.
    Uses string-based sender to avoid circular imports at module load time.
    """
    if not instance.user_id:
        from timetable_app.models import generate_user_id
        instance.user_id = generate_user_id()


@receiver(pre_save, sender='timetable_app.User')
def assign_initial_password(sender, instance, **kwargs):
    """
    When a WORKER is being created (pk is None), generate a secure random
    password, store plain version in plain_password temporarily, and hash it.
    Only fires for new records with no password set yet.
    """
    if instance.pk is None and instance.role == 'WORKER':
        if not instance.password:
            from timetable_app.models import generate_worker_password
            raw_password = generate_worker_password(length=10)
            instance.plain_password = raw_password
            instance.set_password(raw_password)
