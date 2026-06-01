"""
serializers.py — Timetable Planner Phase 1

Serializers for:
  - Auth (Login, Token)
  - Organisation & WorkTypeLimit
  - User (Employee view of workers — includes plain_password on creation)
  - Availability
  - Timetable & Shift
"""

from django.contrib.auth import authenticate
from rest_framework import serializers
from timetable_app.models import (
    Organisation, WorkTypeLimit, User, Availability, Timetable, Shift
)


# ---------------------------------------------------------------------------
# Auth Serializers
# ---------------------------------------------------------------------------

class LoginSerializer(serializers.Serializer):
    """
    Accepts user_id + password.
    The worker login flow:
        1. Frontend shows a list of all workers (names).
        2. Worker selects their name → their user_id is auto-filled.
        3. Worker enters their password.
        4. POST to /api/auth/login/ with {user_id, password}.
    """
    user_id  = serializers.CharField(max_length=11)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        user_id  = data.get('user_id')
        password = data.get('password')

        if not user_id or not password:
            raise serializers.ValidationError('user_id and password are required.')

        user = authenticate(
            request=self.context.get('request'),
            username=user_id,
            password=password,
        )

        if not user:
            raise serializers.ValidationError('Invalid user_id or password.')

        if not user.is_active:
            raise serializers.ValidationError('This account has been deactivated.')

        data['user'] = user
        return data


class UserMeSerializer(serializers.ModelSerializer):
    """Minimal profile returned after login / in /api/auth/me/"""
    org_name     = serializers.CharField(source='org.name', read_only=True, default=None)
    weekly_hours = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'user_id', 'full_name', 'role', 'work_type',
            'org', 'org_name', 'weekly_hours', 'is_active', 'created_at',
        ]
        read_only_fields = fields

    def get_weekly_hours(self, obj):
        return obj.get_weekly_hour_limit()


# ---------------------------------------------------------------------------
# Organisation Serializers
# ---------------------------------------------------------------------------

class OrganisationSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()

    class Meta:
        model  = Organisation
        fields = ['org_id', 'name', 'shop_open', 'shop_close', 'user_count',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'user_count', 'created_at', 'updated_at']

    def get_user_count(self, obj):
        return obj.users.filter(is_active=True).count()


class OrganisationUpdateSerializer(serializers.ModelSerializer):
    """Organisation admin-only: update shop open/close times."""
    class Meta:
        model  = Organisation
        fields = ['shop_open', 'shop_close']

    def validate(self, data):
        open_t  = data.get('shop_open',  self.instance.shop_open  if self.instance else None)
        close_t = data.get('shop_close', self.instance.shop_close if self.instance else None)
        if open_t and close_t and open_t >= close_t:
            raise serializers.ValidationError(
                'shop_open must be earlier than shop_close.'
            )
        return data


# ---------------------------------------------------------------------------
# WorkTypeLimit Serializers
# ---------------------------------------------------------------------------

class WorkTypeLimitSerializer(serializers.ModelSerializer):
    work_type_display = serializers.CharField(source='get_work_type_display', read_only=True)

    class Meta:
        model  = WorkTypeLimit
        fields = ['id', 'org', 'work_type', 'work_type_display', 'hours_per_week']
        read_only_fields = ['id', 'work_type_display']

    def validate_hours_per_week(self, value):
        if value < 1 or value > 60:
            raise serializers.ValidationError(
                'hours_per_week must be between 1 and 60.'
            )
        return value


# ---------------------------------------------------------------------------
# Worker / User Serializers
# ---------------------------------------------------------------------------

class WorkerListSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for listing workers.
    Used by the org admin on the /api/workers/ GET endpoint.
    Also used by the worker login screen to show name list.
    """
    org_name         = serializers.CharField(source='org.name', read_only=True, default=None)
    weekly_hours     = serializers.SerializerMethodField()
    work_type_display = serializers.CharField(source='get_work_type_display', read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'user_id', 'full_name', 'role', 'work_type',
            'work_type_display', 'org', 'org_name',
            'weekly_hours', 'is_active', 'created_at',
        ]

    def get_weekly_hours(self, obj):
        return obj.get_weekly_hour_limit()


class WorkerCreateSerializer(serializers.ModelSerializer):
    """
    Employee-only: create a new worker.

    On creation the response includes `plain_password` — shown ONCE.
    The frontend must display this to the org admin so they can hand it
    to the worker. It is not stored in plain text after the response.

    user_id is auto-generated (Base64url, 11 chars) via signals.py.
    """
    plain_password = serializers.CharField(read_only=True)
    user_id        = serializers.CharField(read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'user_id', 'full_name', 'role', 'work_type',
            'org', 'plain_password', 'is_active',
        ]
        read_only_fields = ['id', 'user_id', 'plain_password']

    def validate(self, data):
        # Role is always WORKER — all JWT users are workers
        data['role'] = User.Role.WORKER
        if not data.get('work_type'):
            raise serializers.ValidationError({'work_type': 'work_type is required for workers.'})
        return data

    def create(self, validated_data):
        """
        Signals handle user_id generation and password assignment.
        We just save here. After save, plain_password is available on the instance.
        """
        user = User(**validated_data)
        user.save()
        return user

    def to_representation(self, instance):
        """
        Include plain_password in response (only for create).
        After this representation is built, the view clears plain_password.
        """
        ret = super().to_representation(instance)
        ret['plain_password'] = instance.plain_password  # may be None on updates
        return ret


class WorkerUpdateSerializer(serializers.ModelSerializer):
    """Employee-only: update a worker's work_type or active status."""
    class Meta:
        model  = User
        fields = ['full_name', 'work_type', 'is_active']

    def validate_work_type(self, value):
        if value not in [c[0] for c in User.WorkType.choices]:
            raise serializers.ValidationError('Invalid work_type.')
        return value


class WorkerPublicSerializer(serializers.ModelSerializer):
    """
    Public (unauthenticated) serializer used on the login screen.
    Returns just name + user_id so the worker can select their name
    and have their user_id auto-filled. No sensitive data exposed.
    """
    class Meta:
        model  = User
        fields = ['user_id', 'full_name', 'org']


# ---------------------------------------------------------------------------
# Availability Serializers
# ---------------------------------------------------------------------------

class AvailabilitySerializer(serializers.ModelSerializer):
    worker_name = serializers.CharField(source='worker.full_name', read_only=True)
    worker_id   = serializers.CharField(source='worker.user_id',   read_only=True)
    day_display = serializers.CharField(source='get_day_display',  read_only=True)
    # worker is assigned automatically from request.user in create()
    # It is read-only on input; shown in output for reference
    worker      = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model  = Availability
        fields = [
            'id', 'worker', 'worker_name', 'worker_id',
            'week_start', 'day', 'day_display',
            'start_time', 'submitted_at',
        ]
        read_only_fields = ['id', 'worker', 'worker_name', 'worker_id',
                            'day_display', 'submitted_at']

    def validate_week_start(self, value):
        """week_start must be a Monday."""
        if value.weekday() != 0:  # 0 = Monday
            raise serializers.ValidationError(
                f'week_start must be a Monday. Got: {value.strftime("%A %Y-%m-%d")}'
            )
        return value

    def validate(self, data):
        """
        Workers can submit availability for the upcoming week.

        Submission rules:
          - Saturday/Sunday  → submit for NEXT week (Mon–Sun starting next Monday)
          - Mon–Fri          → submit for the CURRENT week (Mon–Sun starting this Monday)
                               This relaxed rule allows testing and covers edge cases where
                               an employee opens the window early.

        The week_start must always be a Monday (enforced by validate_week_start).
        """
        import datetime
        from django.utils import timezone

        today      = timezone.now().date()
        week_start = data.get('week_start')

        if week_start:
            # Monday of the current week
            this_monday = today - datetime.timedelta(days=today.weekday())
            # Monday of next week
            next_monday = this_monday + datetime.timedelta(weeks=1)

            # On Saturday/Sunday workers submit for the NEXT week
            if today.weekday() >= 5:   # 5=Sat, 6=Sun
                valid_monday = next_monday
                label        = f'next week ({next_monday})'
            else:
                # Mon–Fri: accept either current or next week
                valid_monday = this_monday
                label        = f'current or next week'

            # Accept current week or next week (flexible for employee-managed edge cases)
            if week_start not in (this_monday, next_monday):
                raise serializers.ValidationError(
                    f'week_start must be the Monday of the current or next working week. '
                    f'Expected {this_monday} or {next_monday}, got {week_start}.'
                )

        return data


    def create(self, validated_data):
        """
        Assign the current logged-in worker as the owner.
        Enforced here even if worker field is passed in the request body.
        """
        request = self.context.get('request')
        validated_data['worker'] = request.user
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# Timetable & Shift Serializers
# ---------------------------------------------------------------------------

class ShiftSerializer(serializers.ModelSerializer):
    worker_name  = serializers.CharField(source='worker.full_name', read_only=True)
    worker_uid   = serializers.CharField(source='worker.user_id',   read_only=True)
    day_display  = serializers.CharField(source='get_day_display',  read_only=True)
    work_type    = serializers.CharField(source='worker.work_type',  read_only=True)

    class Meta:
        model  = Shift
        fields = [
            'id', 'worker', 'worker_name', 'worker_uid', 'work_type',
            'day', 'day_display', 'start_time', 'end_time', 'hours',
        ]
        read_only_fields = ['id', 'worker_name', 'worker_uid', 'day_display', 'hours', 'work_type']


class TimetableSerializer(serializers.ModelSerializer):
    shifts          = ShiftSerializer(many=True, read_only=True)
    org_name        = serializers.CharField(source='org.name',      read_only=True)
    status_display  = serializers.CharField(source='get_status_display', read_only=True)
    week_end        = serializers.DateField(read_only=True)
    total_shifts    = serializers.SerializerMethodField()

    class Meta:
        model  = Timetable
        fields = [
            'id', 'org', 'org_name', 'week_start', 'week_end',
            'generated_at', 'status', 'status_display',
            'total_shifts', 'shifts',
        ]
        read_only_fields = ['id', 'org_name', 'week_end', 'generated_at',
                            'status_display', 'total_shifts', 'shifts']

    def get_total_shifts(self, obj):
        return obj.shifts.count()

    def validate_week_start(self, value):
        if value.weekday() != 0:
            raise serializers.ValidationError('week_start must be a Monday.')
        return value


# ---------------------------------------------------------------------------
# Organisation Registration & Login Serializers
# ---------------------------------------------------------------------------

# Phone length rules per country dial code (digits only, excluding leading 0)
PHONE_LENGTH_RULES = {
    '+91' : 10,   # India
    '+49' : 11,   # Germany (without leading 0)
    '+1'  : 10,   # USA / Canada
    '+44' : 10,   # UK (without leading 0)
    '+33' : 9,    # France
    '+39' : 10,   # Italy
    '+34' : 9,    # Spain
    '+31' : 9,    # Netherlands
    '+32' : 9,    # Belgium
    '+41' : 9,    # Switzerland
    '+43' : 10,   # Austria
    '+61' : 9,    # Australia
    '+81' : 10,   # Japan
    '+86' : 11,   # China
    '+55' : 11,   # Brazil
    '+7'  : 10,   # Russia
    '+27' : 9,    # South Africa
    '+971': 9,    # UAE
    '+966': 9,    # Saudi Arabia
    '+65' : 8,    # Singapore
}


class OrgRegisterSerializer(serializers.ModelSerializer):
    """
    Public registration for a new organisation.
    Creates the org + seeds default WorkTypeLimits + auto-creates first Employee from owner_name.
    employee_name field removed — employee is created from owner_name automatically.
    """
    org_name     = serializers.CharField(max_length=200)
    owner_name   = serializers.CharField(max_length=150, help_text='Full name of the organisation owner')
    email        = serializers.EmailField()
    password     = serializers.CharField(min_length=8, write_only=True,
                                         style={'input_type': 'password'})
    country_code = serializers.CharField(max_length=6,  help_text='Dial code e.g. +49')
    phone        = serializers.CharField(max_length=20, help_text='Phone number digits only, no leading zero')
    house_number = serializers.CharField(max_length=20,  required=False, default='')
    street       = serializers.CharField(max_length=200, required=False, default='')
    city         = serializers.CharField(max_length=100, required=False, default='')
    country      = serializers.CharField(max_length=100, required=False, default='')
    zip_code     = serializers.CharField(max_length=20,  required=False, default='')
    shop_open    = serializers.TimeField(default='08:00', required=False)
    shop_close   = serializers.TimeField(default='20:00', required=False)

    class Meta:
        model  = Organisation
        fields = [
            'org_name', 'owner_name', 'email', 'password',
            'country_code', 'phone',
            'house_number', 'street', 'city', 'country', 'zip_code',
            'shop_open', 'shop_close',
        ]

    def validate_org_name(self, value):
        if Organisation.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(
                f'An organisation named "{value}" already exists.'
            )
        return value

    def validate_email(self, value):
        if Organisation.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'An organisation with this email already exists.'
            )
        return value

    def validate(self, data):
        # Shop hours
        open_t  = data.get('shop_open',  '08:00')
        close_t = data.get('shop_close', '20:00')
        if str(open_t) >= str(close_t):
            raise serializers.ValidationError('shop_open must be earlier than shop_close.')

        # Phone validation
        code  = data.get('country_code', '').strip()
        phone = data.get('phone', '').strip()

        # Strip all non-digit characters for length check
        digits = ''.join(c for c in phone if c.isdigit())

        # Remove leading zero if present (common mistake)
        if digits.startswith('0'):
            raise serializers.ValidationError(
                {'phone': f'Do not include a leading 0. Enter the number without it (e.g. 17612345678 for Germany).'}
            )

        expected = PHONE_LENGTH_RULES.get(code)
        if expected and len(digits) != expected:
            raise serializers.ValidationError(
                {'phone': f'{code} numbers must be exactly {expected} digits (you entered {len(digits)}).'}
            )
        if len(digits) < 6:
            raise serializers.ValidationError(
                {'phone': 'Phone number is too short.'}
            )

        # Store cleaned digits-only version
        data['phone'] = digits
        return data

    def create(self, validated_data):
        from timetable_app.models import WorkTypeLimit, User, generate_user_id, generate_worker_password
        from django.db import transaction

        with transaction.atomic():
            # 1. Create organisation
            org = Organisation(
                name         = validated_data['org_name'],
                owner_name   = validated_data['owner_name'],
                email        = validated_data['email'].lower(),
                country_code = validated_data.get('country_code', ''),
                phone        = validated_data.get('phone', ''),
                house_number = validated_data.get('house_number', ''),
                street       = validated_data.get('street', ''),
                city         = validated_data.get('city', ''),
                country      = validated_data.get('country', ''),
                zip_code     = validated_data.get('zip_code', ''),
                shop_open    = validated_data.get('shop_open',  '08:00'),
                shop_close   = validated_data.get('shop_close', '20:00'),
            )
            org.set_password(validated_data['password'])
            org.save()

            # 2. Seed default WorkTypeLimits
            for wt, hrs in [('FULL_TIME', 40), ('PART_TIME', 20), ('MINIJOB', 10)]:
                WorkTypeLimit.objects.create(org=org, work_type=wt, hours_per_week=hrs)

            # No User row for the org owner — owner details live on Organisation itself.
            # (owner_name and email are already on the org object above)

        return org  # no employee, no password


class OrgLoginSerializer(serializers.Serializer):
    """
    Flexible login — accepts either:
      - org_id   (8-char Base64url)  + password
      - email                        + password

    Detection logic:
      - If identifier contains '@'  → treat as email
      - Else if len == 8 and all chars in Base64url alphabet → treat as org_id
      - Else → validation error with helpful message
    """
    identifier = serializers.CharField(
        help_text='Your organisation email address OR your 8-character org ID'
    )
    password   = serializers.CharField(
        write_only=True, style={'input_type': 'password'}
    )

    def validate(self, data):
        identifier = data.get('identifier', '').strip()
        password   = data.get('password',   '').strip()

        if not identifier or not password:
            raise serializers.ValidationError('Identifier and password are required.')

        org = None

        # ── Detect type ───────────────────────────────────────────────
        if '@' in identifier:
            # Treat as email
            try:
                org = Organisation.objects.get(
                    email=identifier.lower(), is_active=True
                )
            except Organisation.DoesNotExist:
                raise serializers.ValidationError(
                    'No active organisation found with that email address.'
                )

        else:
            import string as _string
            BASE64URL = _string.ascii_letters + _string.digits + '-_'
            is_org_id = (
                len(identifier) == 8 and
                all(c in BASE64URL for c in identifier)
            )

            if is_org_id:
                try:
                    org = Organisation.objects.get(
                        org_id=identifier, is_active=True
                    )
                except Organisation.DoesNotExist:
                    raise serializers.ValidationError(
                        'No active organisation found with that org ID.'
                    )
            else:
                raise serializers.ValidationError(
                    'Enter a valid email address or your 8-character org ID '
                    '(letters, numbers, - and _ only).'
                )

        # ── Check password ────────────────────────────────────────────
        if not org.check_password(password):
            raise serializers.ValidationError('Incorrect password.')

        data['org'] = org
        return data

class OrgDetailSerializer(serializers.ModelSerializer):
    """Safe read-only representation of an Organisation (no password)."""
    worker_count   = serializers.SerializerMethodField()

    join_url       = serializers.SerializerMethodField()
    login_url      = serializers.SerializerMethodField()

    class Meta:
        model  = Organisation
        fields = ['id', 'org_id', 'name', 'email', 'shop_open', 'shop_close',
                  'is_active', 'created_at', 'worker_count',
                  'join_url', 'login_url']
        read_only_fields = fields

    def get_worker_count(self, obj):
        return obj.users.filter(role='WORKER', is_active=True).count()


    def get_join_url(self, obj):
        """URL workers use to join this organisation — provided by the org admin."""
        req = self.context.get('request')
        if req:
            host = req.build_absolute_uri('/').rstrip('/')
            return f'{host}/#/org/{obj.org_id}/join'
        return f'/#/org/{obj.org_id}/join'

    def get_login_url(self, obj):
        """Direct login URL for this organisation."""
        req = self.context.get('request')
        if req:
            host = req.build_absolute_uri('/').rstrip('/')
            return f'{host}/#/org/{obj.org_id}/login'
        return f'/#/org/{obj.org_id}/login'




# ---------------------------------------------------------------------------
# Add User Serializer (Org-admin creates a full user with all details)
# ---------------------------------------------------------------------------
class AddUserSerializer(serializers.Serializer):
    """
    Org-admin creates a new worker via the add-user form.

    Email and phone are globally unique across ALL organisations.
    If either already exists the serializer returns a clear error.

    Work-type capacity rules enforced per user across all current jobs:
      - 1 FULL_TIME  only
      - up to 2 PART_TIME
      - up to 4 MINIJOB
      - 1 PART_TIME + up to 2 MINIJOB
    """
    first_name  = serializers.CharField(max_length=80)
    last_name   = serializers.CharField(max_length=80)
    email       = serializers.EmailField()
    phone       = serializers.CharField(max_length=20)
    work_type   = serializers.ChoiceField(choices=['FULL_TIME', 'PART_TIME', 'MINIJOB'])
    role        = serializers.ChoiceField(choices=['WORKER'], default='WORKER')
    nationality = serializers.CharField(max_length=100, required=False, default='')
    dob         = serializers.DateField(required=False, allow_null=True)
    iban        = serializers.CharField(max_length=34, required=False, default='')
    bic         = serializers.CharField(max_length=11, required=False, default='')
    # Address
    house_number = serializers.CharField(max_length=20,  required=False, default='')
    street       = serializers.CharField(max_length=200, required=False, default='')
    city         = serializers.CharField(max_length=100, required=False, default='')
    country      = serializers.CharField(max_length=100, required=False, default='')
    zip_code     = serializers.CharField(max_length=20,  required=False, default='')

    def validate_email(self, value):
        from timetable_app.models import User as U
        if U.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'A user with this email already exists in another organisation.'
            )
        return value.lower()

    def validate_phone(self, value):
        from timetable_app.models import User as U
        digits = ''.join(c for c in value if c.isdigit())
        if U.objects.filter(phone=digits).exists():
            raise serializers.ValidationError(
                'A user with this mobile number already exists in another organisation.'
            )
        return digits

    def validate(self, data):
        # Work-type capacity check for this person across ALL current jobs
        from timetable_app.models import JobHistory
        email = data.get('email', '')
        phone = data.get('phone', '')
        work_type = data.get('work_type', '')
        from timetable_app.models import User as U

        # Find existing user by email or phone (may be joining a 2nd org)
        existing_user = (
            U.objects.filter(email=email).first() or
            U.objects.filter(phone=phone).first()
        )

        if existing_user:
            current_jobs = JobHistory.objects.filter(
                user=existing_user, is_current=True
            ).values_list('work_type', flat=True)
            current_list = list(current_jobs)

            def capacity_ok(new_wt, current):
                full  = current.count('FULL_TIME')
                part  = current.count('PART_TIME')
                mini  = current.count('MINIJOB')
                if new_wt == 'FULL_TIME':
                    return full == 0 and part == 0 and mini == 0
                if new_wt == 'PART_TIME':
                    return full == 0 and part < 2 and (part + 1 + mini <= 3)
                if new_wt == 'MINIJOB':
                    return full == 0 and mini < 4 and (part * 2 + mini + 1 <= 4)
                return False

            if not capacity_ok(work_type, current_list):
                raise serializers.ValidationError({
                    'work_type': (
                        f'This person already has {current_list} job(s). '
                        f'Cannot add another {work_type}. '
                        'Rules: 1 full-time only, up to 2 part-time, '
                        'up to 4 mini-jobs, or 1 part-time + 2 mini-jobs.'
                    )
                })

        return data

    def create(self, validated_data):
        from timetable_app.models import (
            User as U, JobHistory, generate_user_id, generate_worker_password
        )
        from django.db import transaction

        org = validated_data.pop('org')

        with transaction.atomic():
            email     = validated_data.get('email')
            phone     = validated_data.get('phone')
            work_type = validated_data.get('work_type')
            role      = validated_data.get('role', 'WORKER')

            # Check if user already exists globally
            existing = (
                U.objects.filter(email=email).first() or
                U.objects.filter(phone=phone).first()
            )

            if existing:
                # User exists — just update their org and add job history
                prev_job = JobHistory.objects.filter(user=existing, is_current=True).first()
                if prev_job:
                    prev_job.is_current = False
                    prev_job.left_at    = __import__('django.utils.timezone', fromlist=['timezone']).timezone.now()
                    prev_job.save()

                existing.org       = org
                existing.work_type = work_type
                existing.role      = role
                existing.is_active = True
                existing.save()

                JobHistory.objects.create(
                    user=existing, org=org, work_type=work_type,
                    is_current=True, created_by=org
                )
                return existing, None   # no plain_password for existing user

            # New user
            full_name    = f"{validated_data.get('first_name','')} {validated_data.get('last_name','')}".strip()
            raw_password = generate_worker_password(length=12)
            uid          = generate_user_id()

            user = U(
                user_id     = uid,
                first_name  = validated_data.get('first_name', ''),
                last_name   = validated_data.get('last_name', ''),
                full_name   = full_name,
                email       = email,
                phone       = phone,
                nationality = validated_data.get('nationality', ''),
                dob         = validated_data.get('dob'),
                iban        = validated_data.get('iban', ''),
                bic         = validated_data.get('bic', ''),
                role        = role,
                work_type   = work_type,
                org         = org,
                is_active   = True,
                plain_password = raw_password,
            )
            user.set_password(raw_password)
            user.save()

            JobHistory.objects.create(
                user=user, org=org, work_type=work_type,
                is_current=True, created_by=org
            )

        return user, raw_password


# ---------------------------------------------------------------------------
# Global User Search Serializer
# ---------------------------------------------------------------------------
class GlobalUserSearchSerializer(serializers.ModelSerializer):
    """Read-only: show name, email, phone, current org, work_type. No sensitive data."""
    current_org  = serializers.SerializerMethodField()
    work_status  = serializers.CharField(source='work_type', read_only=True)

    class Meta:
        from timetable_app.models import User as U
        model  = U
        fields = ['full_name', 'email', 'phone', 'current_org', 'work_status', 'is_active']

    def get_current_org(self, obj):
        if obj.org:
            return {'name': obj.org.name}
        return None
