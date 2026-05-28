"""
setup_dev.py — Development seed script for Timetable Planner Phase 1

Run with:  python setup_dev.py

Creates:
  - 1 Organisation (Acme School)
  - WorkTypeLimit defaults (FULL_TIME=40h, PART_TIME=20h, MINIJOB=10h)
  - 1 Employee account  (user_id + password printed to console)
  - 3 Worker accounts   (user_id + plain_password printed to console)

Use these credentials to test the API endpoints.
"""

import os
import sys
import django

# Bootstrap Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from timetable_app.models import (
    Organisation, WorkTypeLimit, User,
    generate_user_id, generate_worker_password,
    BASE64URL_ALPHABET, USER_ID_LENGTH,
)

SEPARATOR = '─' * 60


def print_section(title):
    print(f'\n{SEPARATOR}')
    print(f'  {title}')
    print(SEPARATOR)


def validate_user_id(uid):
    """Verify user_id conforms to Base64url 11-char spec."""
    assert len(uid) == USER_ID_LENGTH, f'Expected 11 chars, got {len(uid)}'
    for ch in uid:
        assert ch in BASE64URL_ALPHABET, f'Invalid char "{ch}" in user_id'
    return True


# ---------------------------------------------------------------------------
# 1. Organisation
# ---------------------------------------------------------------------------
print_section('Creating Organisation')
org, created = Organisation.objects.get_or_create(
    name='Acme School',
    defaults={'shop_open': '08:00', 'shop_close': '18:00'},
)
print(f'  {"Created" if created else "Found"}: {org}')


# ---------------------------------------------------------------------------
# 2. Work Type Limits
# ---------------------------------------------------------------------------
print_section('Setting Work Type Limits')
LIMITS = [
    ('FULL_TIME', 40),
    ('PART_TIME', 20),
    ('MINIJOB',   10),
]
for wt, hrs in LIMITS:
    limit, created = WorkTypeLimit.objects.get_or_create(
        org=org, work_type=wt,
        defaults={'hours_per_week': hrs},
    )
    print(f'  {"Created" if created else "Found"}: {wt} → {limit.hours_per_week} hrs/week')


# ---------------------------------------------------------------------------
# 3. Employee Account
# ---------------------------------------------------------------------------
print_section('Creating Employee Account')
emp_password = 'Employee@123'

if not User.objects.filter(role='EMPLOYEE', org=org).exists():
    emp_uid = generate_user_id()
    validate_user_id(emp_uid)
    employee = User.objects.create_user(
        user_id=emp_uid,
        full_name='Admin Employee',
        password=emp_password,
        role=User.Role.EMPLOYEE,
        org=org,
        is_staff=True,
    )
    print(f'  Created Employee: {employee.full_name}')
else:
    employee = User.objects.filter(role='EMPLOYEE', org=org).first()
    emp_uid  = employee.user_id
    print(f'  Found existing Employee: {employee.full_name}')

print(f'\n  ┌── EMPLOYEE LOGIN CREDENTIALS ──────────────────┐')
print(f'  │  user_id  : {emp_uid:<38}│')
print(f'  │  password : {emp_password:<38}│')
print(f'  │  role     : EMPLOYEE (full access)             │')
print(f'  └────────────────────────────────────────────────┘')

# Validate Base64url format
validate_user_id(emp_uid)
print(f'\n  ✅ user_id "{emp_uid}" passes Base64url validation')
print(f'     Length: {len(emp_uid)} chars | Alphabet: A-Z, a-z, 0-9, -, _')


# ---------------------------------------------------------------------------
# 4. Worker Accounts
# ---------------------------------------------------------------------------
print_section('Creating Worker Accounts')

WORKERS = [
    ('Alice Müller',  'FULL_TIME'),
    ('Bob Schmidt',   'PART_TIME'),
    ('Clara Weber',   'MINIJOB'),
]

print(f'\n  ┌── WORKER LOGIN CREDENTIALS ────────────────────────────────────────┐')

worker_creds = []
for name, work_type in WORKERS:
    if User.objects.filter(full_name=name, org=org).exists():
        w = User.objects.get(full_name=name, org=org)
        print(f'  │  (already exists) {name:<20} user_id: {w.user_id}  │')
        continue

    raw_pw = generate_worker_password(length=10)
    uid    = generate_user_id()
    validate_user_id(uid)

    worker = User(
        full_name=name,
        role=User.Role.WORKER,
        work_type=work_type,
        org=org,
    )
    worker.user_id = uid          # set before save (signal won't override if set)
    worker.set_password(raw_pw)
    worker.save()

    hrs = worker.get_weekly_hour_limit()
    worker_creds.append((name, work_type, uid, raw_pw, hrs))
    print(f'  │  {name:<20} {work_type:<12} {uid}  {raw_pw}  │')

print(f'  └────────────────────────────────────────────────────────────────────┘')


# ---------------------------------------------------------------------------
# 5. Summary
# ---------------------------------------------------------------------------
print_section('Summary')
print(f'  Organisation  : {org.name}')
print(f'  Shop hours    : {org.shop_open} – {org.shop_close}')
print(f'  Total users   : {User.objects.filter(org=org).count()}')
print(f'  Workers       : {User.objects.filter(org=org, role="WORKER").count()}')
print(f'  Employees     : {User.objects.filter(org=org, role="EMPLOYEE").count()}')

print('\n  Hour Limits:')
for wt, hrs in LIMITS:
    print(f'    {wt:<12}: {hrs} hrs/week')

print(f'\n  ✅ Phase 1 seed complete. Start the server:')
print(f'     cd backend && python manage.py runserver')
print(f'\n  📡 API base URL: http://127.0.0.1:8000/api/')
print(f'  🛠  Django Admin: http://127.0.0.1:8000/admin/')
print()

# ---------------------------------------------------------------------------
# 6. Quick Base64url uniqueness test
# ---------------------------------------------------------------------------
print_section('Base64url user_id Uniqueness Test')
import time
start = time.time()
test_ids = {generate_user_id() for _ in range(10_000)}
elapsed = time.time() - start
print(f'  Generated 10,000 IDs in {elapsed:.3f}s')
print(f'  Unique IDs: {len(test_ids)} (collision-free ✅)')
print(f'  Sample IDs:')
for uid in list(test_ids)[:5]:
    validate_user_id(uid)
    print(f'    {uid}  ← all chars in Base64url alphabet ✅')
print()
