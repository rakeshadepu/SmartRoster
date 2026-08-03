"""
serializers.py — Timetable Planner
=====================================

Serializers grouped by concern:

  Auth            LoginSerializer, UserMeSerializer
  Organisation    OrganisationSerializer, OrganisationUpdateSerializer,
                  OrgRegisterSerializer, OrgLoginSerializer, OrgDetailSerializer
  WorkTypeLimit   WorkTypeLimitSerializer
  Workers         WorkerListSerializer, WorkerCreateSerializer,
                  WorkerUpdateSerializer, WorkerPublicSerializer
  Availability    AvailabilitySerializer
  Timetable       TimetableSerializer, ShiftSerializer
  Misc            AddUserSerializer, GlobalUserSearchSerializer

Design notes:
  - No is_active on Organisation or User — removed entirely.
    Workers are detached from orgs (User.org = None), not deactivated.
    Orgs are never soft-deleted.
  - OrgLoginSerializer looks up orgs by email or org_id with no is_active filter.
  - All worker counts simply count by role and org membership.
"""

from django.contrib.auth import authenticate
# from django.db.models import Max
from rest_framework import serializers
from timetable_app.models import (
    Organisation, BusinessHours, WorkTypeLimit, User, Availability, Timetable, Shift, JobHistory
)


# ===========================================================================
# Auth Serializers
# ===========================================================================

class LoginSerializer(serializers.Serializer):
    """
    Worker login: accepts user_id + password.

    Login flow:
        1. Frontend fetches /api/org/<org_id>/workers/public/ — list of names + user_ids
        2. Worker selects their name → user_id is auto-filled
        3. Worker enters password → POST /api/auth/login/
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
            raise serializers.ValidationError('Invalid password.')

        data['user'] = user
        return data


class UserMeSerializer(serializers.ModelSerializer):
    """Minimal profile returned after login and on GET /api/auth/me/"""
    org_name     = serializers.CharField(source='org.name', read_only=True, default=None)
    weekly_hours = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'user_id', 'employee_code', 'full_name', 'role', 'work_type',
            'org', 'org_name', 'weekly_hours', 'created_at',
        ]
        read_only_fields = fields

    def get_weekly_hours(self, obj):
        return obj.get_weekly_hour_limit()


# ===========================================================================
# Organisation Serializers
# ===========================================================================

class BusinessHoursSerializer(serializers.ModelSerializer):
    """
    One organisation's opening/closing time for a single day of the week.
    Used both as a nested read-only list on Organisation, and standalone
    for the org admin's business-hours settings endpoint.
    """
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model  = BusinessHours
        fields = ['id', 'org', 'day_of_week', 'day_display', 'open_time', 'close_time']
        read_only_fields = ['id', 'day_display']
        extra_kwargs = {'org': {'required': False}}

    def validate(self, data):
        open_t  = data.get('open_time',  self.instance.open_time  if self.instance else None)
        close_t = data.get('close_time', self.instance.close_time if self.instance else None)
        if open_t and close_t and open_t >= close_t:
            raise serializers.ValidationError('open_time must be earlier than close_time.')
        return data


class OrganisationSerializer(serializers.ModelSerializer):
    """
    Read-only summary of an organisation.
    worker_count counts all staff currently assigned to the org, any role.
    business_hours is the full per-day-of-week schedule (see BusinessHours model).
    """
    worker_count   = serializers.SerializerMethodField()
    business_hours = BusinessHoursSerializer(many=True, read_only=True)

    class Meta:
        model  = Organisation
        fields = [
            'org_id', 'name', 'business_hours',
            'worker_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'worker_count', 'business_hours', 'created_at', 'updated_at']

    def get_worker_count(self, obj):
        # Count all staff currently assigned to this org (any role, org FK set)
        return obj.users.count()


class OrganisationUpdateSerializer(serializers.ModelSerializer):
    """
    Org admin: update name, email, and/or password.
    Business hours are managed separately via BusinessHoursSerializer /
    the /api/business-hours/ endpoint — one row per day of week.
    Email uniqueness is enforced globally across both Organisation and User tables.
    """
    password = serializers.CharField(
        min_length=8, write_only=True, required=False,
        style={'input_type': 'password'}
    )

    class Meta:
        model  = Organisation
        fields = ['name', 'email', 'password']
        extra_kwargs = {
            'name':  {'required': False},
            'email': {'required': False},
        }

    def validate_email(self, value):
        value = value.lower()
        qs = Organisation.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'Another organisation is already using this email address.'
            )
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'This email is already assigned to a worker account.'
            )
        return value

    def validate_name(self, value):
        qs = Organisation.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'An organisation with this name already exists.'
            )
        return value

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


# ===========================================================================
# WorkTypeLimit Serializer
# ===========================================================================

class WorkTypeLimitSerializer(serializers.ModelSerializer):
    work_type_display = serializers.CharField(source='get_work_type_display', read_only=True)

    class Meta:
        model  = WorkTypeLimit
        fields = ['id', 'org', 'work_type', 'work_type_display', 'hours_per_week']
        read_only_fields = ['id', 'work_type_display']

    def validate_hours_per_week(self, value):
        if value < 1 or value > 60:
            raise serializers.ValidationError('hours_per_week must be between 1 and 60.')
        return value


# ===========================================================================
# Worker / User Serializers
# ===========================================================================
class WorkerListSerializer(serializers.ModelSerializer):
    joined_at    = serializers.SerializerMethodField()
    weekly_hours = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'user_id',
            'employee_code',
            'full_name',
            'first_name',
            'last_name',
            'email',
            'phone',
            'nationality',
            'dob',
            'iban',
            'bic',
            'role',
            'role_display',
            'work_type',
            'weekly_hours',
            'joined_at',
        ]

    def get_weekly_hours(self, obj):
        return obj.get_weekly_hour_limit()

    def get_joined_at(self, obj):
        record = obj.job_history.filter(is_current=True).order_by('-joined_at').first()
        if record:
            return record.joined_at.strftime('%Y-%m-%d %H:%M')
        return None
    

class WorkerCreateSerializer(serializers.ModelSerializer):
    """
    Org admin: create a new worker.

    On creation the response includes plain_password — shown ONCE.
    The org admin must copy this and hand it to the worker.
    It is NOT stored in plain text after the response is sent.

    user_id is auto-generated (Base64url, 11 chars) via signals.py.
    """
    plain_password = serializers.CharField(read_only=True)
    user_id        = serializers.CharField(read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'user_id', 'employee_code', 'full_name', 'role', 'work_type', 'org', 'plain_password',
        ]
        read_only_fields = ['id', 'user_id', 'plain_password']
        extra_kwargs = {
            'role': {'required': False, 'default': User.Role.WORKER},
        }

    def validate_employee_code(self, value):
        if not value:
            return value
        qs = User.objects.filter(employee_code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('This employee code is already in use.')
        return value

    def validate(self, data):
        data.setdefault('role', User.Role.WORKER)
        if not data.get('work_type'):
            raise serializers.ValidationError({'work_type': 'work_type is required for workers.'})
        return data

    def create(self, validated_data):
        user = User(**validated_data)
        user.save()
        return user

    def to_representation(self, instance):
        """Inject plain_password for the creation response only."""
        ret = super().to_representation(instance)
        ret['plain_password'] = instance.plain_password  # None on subsequent reads
        return ret


class WorkerUpdateSerializer(serializers.ModelSerializer):
    """Org admin: update a worker's work_type, role, employee_code, full_name, or email."""

    class Meta:
        model  = User
        fields = ['full_name', 'work_type', 'role', 'employee_code', 'email']
        extra_kwargs = {
            'email':         {'required': False, 'allow_null': True, 'allow_blank': True},
            'role':          {'required': False},
            'employee_code': {'required': False, 'allow_null': True},
        }

    def validate_work_type(self, value):
        if value not in [c[0] for c in User.WorkType.choices]:
            raise serializers.ValidationError('Invalid work_type.')
        return value

    def validate_employee_code(self, value):
        if not value:
            return value
        qs = User.objects.filter(employee_code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('This employee code is already in use.')
        return value

    def validate_email(self, value):
        if not value:
            return value
        value = value.lower()
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'This email is already assigned to another worker account.'
            )
        if Organisation.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'This email is already assigned to an organisation account.'
            )
        return value


class WorkerPublicSerializer(serializers.ModelSerializer):
    """
    Unauthenticated: used on the worker login screen.
    Returns name + user_id only — no sensitive data.
    """
    class Meta:
        model  = User
        fields = ['user_id', 'full_name', 'org']


# ===========================================================================
# Availability Serializer
# ===========================================================================

class AvailabilitySerializer(serializers.ModelSerializer):
    """
    Worker availability for a specific day in a given week.

    On POST:
        - worker is always set from request.user (cannot be overridden).
        - end_time is optional — lets workers declare their upper bound.
    On GET:
        - worker_name and worker_id are read-only display fields.
    """
    worker_name = serializers.CharField(source='worker.full_name', read_only=True)
    worker_id   = serializers.CharField(source='worker.user_id',   read_only=True)
    day_display = serializers.CharField(source='get_day_display',  read_only=True)
    worker      = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model  = Availability
        fields = [
            'id', 'worker', 'worker_name', 'worker_id',
            'week_start', 'week_number', 'day', 'day_display',
            'start_time', 'end_time', 'submitted_at',
        ]
        read_only_fields = [
            'id', 'worker', 'worker_name', 'worker_id',
            'week_number', 'day_display', 'submitted_at',
        ]

    def validate_week_start(self, value):
        """week_start must always be a Monday."""
        if value.weekday() != 0:
            raise serializers.ValidationError(
                f'week_start must be a Monday. Got: {value.strftime("%A %Y-%m-%d")}'
            )
        return value

    def validate(self, data):
        """
        Submission window rules:
          - Sat / Sun  →  submit for NEXT week only
          - Mon – Fri  →  accept current week or next week
                          (allows early submission and edge-case testing)
        """
        import datetime
        from django.utils import timezone

        today      = timezone.now().date()
        week_start = data.get('week_start')

        if week_start:
            this_monday = today - datetime.timedelta(days=today.weekday())
            next_monday = this_monday + datetime.timedelta(weeks=1)

            if week_start not in (this_monday, next_monday):
                raise serializers.ValidationError(
                    f'week_start must be the Monday of the current or next working week. '
                    f'Expected {this_monday} or {next_monday}, got {week_start}.'
                )

        # end_time must be after start_time if both provided
        start_time = data.get('start_time')
        end_time   = data.get('end_time')
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError(
                'end_time must be later than start_time.'
            )

        return data

    def create(self, validated_data):
        """Always assign the logged-in worker as the owner."""
        request = self.context.get('request')
        validated_data['worker'] = request.user
        return super().create(validated_data)


# ===========================================================================
# Timetable & Shift Serializers
# ===========================================================================

class ShiftSerializer(serializers.ModelSerializer):
    worker_name = serializers.CharField(source='worker.full_name', read_only=True)
    worker_uid  = serializers.CharField(source='worker.user_id',   read_only=True)
    day_display = serializers.CharField(source='get_day_display',  read_only=True)
    work_type   = serializers.CharField(source='worker.work_type', read_only=True)

    class Meta:
        model  = Shift
        fields = [
            'id', 'worker', 'worker_name', 'worker_uid', 'work_type',
            'day', 'day_display', 'start_time', 'end_time', 'hours',
        ]
        read_only_fields = [
            'id', 'worker_name', 'worker_uid', 'day_display', 'hours', 'work_type',
        ]


class TimetableSerializer(serializers.ModelSerializer):
    shifts            = ShiftSerializer(many=True, read_only=True)
    org_name          = serializers.CharField(source='org.name',              read_only=True)
    status_display    = serializers.CharField(source='get_status_display',    read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.full_name', read_only=True, default=None)
    week_end          = serializers.DateField(read_only=True)
    total_shifts      = serializers.SerializerMethodField()

    class Meta:
        model  = Timetable
        fields = [
            'id', 'org', 'org_name', 'week_start', 'week_end',
            'generated_at', 'generated_by', 'generated_by_name',
            'status', 'status_display',
            'total_shifts', 'shifts',
        ]
        read_only_fields = [
            'id', 'org_name', 'week_end', 'generated_at',
            'generated_by', 'generated_by_name',
            'status_display', 'total_shifts', 'shifts',
        ]

    def get_total_shifts(self, obj):
        return obj.shifts.count()

    def validate_week_start(self, value):
        if value.weekday() != 0:
            raise serializers.ValidationError('week_start must be a Monday.')
        return value


# ===========================================================================
# Organisation Registration & Login
# ===========================================================================

# Phone digit-length rules per country dial code (digits only, no leading 0)
PHONE_LENGTH_RULES = {
    '+91' : 10,   # India
    '+49' : 11,   # Germany
    '+1'  : 10,   # USA / Canada
    '+44' : 10,   # UK
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

    On success:
        - Organisation row created with hashed password.
        - Default WorkTypeLimits seeded (FULL_TIME=40, PART_TIME=20, MINIJOB=10).
        - No User row created for the owner — org admin identity lives on Organisation itself.
    """
    org_name     = serializers.CharField(max_length=200)
    owner_name   = serializers.CharField(max_length=150)
    email        = serializers.EmailField()
    password     = serializers.CharField(min_length=8, write_only=True,
                                         style={'input_type': 'password'})
    country_code = serializers.CharField(max_length=6)
    phone        = serializers.CharField(max_length=20)
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
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'This email is already assigned to a worker account '
                'and cannot be used for an organisation.'
            )
        return value

    def validate(self, data):
        # Shop hours
        open_t  = data.get('shop_open',  '08:00')
        close_t = data.get('shop_close', '20:00')
        if str(open_t) >= str(close_t):
            raise serializers.ValidationError('shop_open must be earlier than shop_close.')

        # Phone validation
        code   = data.get('country_code', '').strip()
        phone  = data.get('phone', '').strip()
        digits = ''.join(c for c in phone if c.isdigit())

        if digits.startswith('0'):
            raise serializers.ValidationError(
                {'phone': 'Do not include a leading 0 (e.g. 17612345678 for Germany).'}
            )
        expected = PHONE_LENGTH_RULES.get(code)
        if expected and len(digits) != expected:
            raise serializers.ValidationError(
                {'phone': f'{code} numbers must be exactly {expected} digits '
                          f'(you entered {len(digits)}).'}
            )
        if len(digits) < 6:
            raise serializers.ValidationError({'phone': 'Phone number is too short.'})

        data['phone'] = digits
        return data

    def create(self, validated_data):
        from timetable_app.models import WorkTypeLimit, BusinessHours
        from django.db import transaction

        with transaction.atomic():
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
            )
            org.set_password(validated_data['password'])
            org.save()

            # Seed default WorkTypeLimits for this org
            for wt, hrs in [('FULL_TIME', 40), ('PART_TIME', 20), ('MINIJOB', 10)]:
                WorkTypeLimit.objects.create(org=org, work_type=wt, hours_per_week=hrs)

            # Seed BusinessHours for all 7 days using the submitted open/close
            # (orgs can later customise individual days via /api/business-hours/)
            open_t  = validated_data.get('shop_open',  '08:00')
            close_t = validated_data.get('shop_close', '20:00')
            BusinessHours.objects.bulk_create([
                BusinessHours(org=org, day_of_week=day, open_time=open_t, close_time=close_t)
                for day, _ in BusinessHours.Day.choices
            ])

        return org


class OrgLoginSerializer(serializers.Serializer):
    """
    Flexible org login. Accepts either:
        { "identifier": "admin@acme.com", "password": "..." }
        { "identifier": "aB3-xY7_",       "password": "..." }

    Detection:
        - Contains '@'          →  treat as email
        - 8 chars, Base64url    →  treat as org_id
        - Anything else         →  validation error
    """
    identifier = serializers.CharField(
        help_text='Organisation email address OR 8-character org ID'
    )
    password   = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        import string as _string

        identifier = data.get('identifier', '').strip()
        password   = data.get('password',   '').strip()

        if not identifier or not password:
            raise serializers.ValidationError('Identifier and password are required.')

        org = None
        BASE64URL = _string.ascii_letters + _string.digits + '-_'

        if '@' in identifier:
            # Email login — no is_active filter (orgs are never deactivated)
            try:
                org = Organisation.objects.get(email=identifier.lower())
            except Organisation.DoesNotExist:
                raise serializers.ValidationError(
                    'No organisation found with that email address.'
                )

        elif len(identifier) == 8 and all(c in BASE64URL for c in identifier):
            # org_id login
            try:
                org = Organisation.objects.get(org_id=identifier)
            except Organisation.DoesNotExist:
                raise serializers.ValidationError(
                    'No organisation found with that org ID.'
                )

        else:
            raise serializers.ValidationError(
                'Enter a valid email address or your 8-character org ID '
                '(letters, numbers, - and _ only).'
            )

        if not org.check_password(password):
            raise serializers.ValidationError('Incorrect password.')

        data['org'] = org
        return data


class OrgDetailSerializer(serializers.ModelSerializer):
    """
    Safe read-only representation of an Organisation (no password field).
    worker_count counts users currently assigned to this org.
    """
    worker_count   = serializers.SerializerMethodField()
    join_url       = serializers.SerializerMethodField()
    login_url      = serializers.SerializerMethodField()
    business_hours = BusinessHoursSerializer(many=True, read_only=True)

    class Meta:
        model  = Organisation
        fields = [
            'id', 'org_id', 'name', 'email', 'business_hours',
            'created_at', 'worker_count', 'join_url', 'login_url',
        ]
        read_only_fields = fields

    def get_worker_count(self, obj):
        # All staff currently assigned to this org (User.org is set), any role
        return obj.users.count()

    def get_join_url(self, obj):
        req = self.context.get('request')
        host = req.build_absolute_uri('/').rstrip('/') if req else ''
        return f'{host}/#/org/{obj.org_id}/join'

    def get_login_url(self, obj):
        req = self.context.get('request')
        host = req.build_absolute_uri('/').rstrip('/') if req else ''
        return f'{host}/#/org/{obj.org_id}/login'


# ===========================================================================
# Add User Serializer (full details, used by org admin form)
# ===========================================================================

class AddUserSerializer(serializers.Serializer):
    """
    Org admin creates a new worker with full personal details.

    Email and phone are globally unique across ALL organisations.
    If the user already exists (matched by email/phone), they are re-hired:
        - Their org is updated to the calling org.
        - The previous open JobHistory record is closed.
        - A new JobHistory record is opened.

    Work-type capacity rules (across all current active jobs):
        - 1 FULL_TIME only (cannot hold any other job simultaneously)
        - Up to 2 PART_TIME
        - Up to 4 MINIJOB
        - 1 PART_TIME + up to 2 MINIJOB
    """
    first_name    = serializers.CharField(max_length=80)
    last_name     = serializers.CharField(max_length=80)
    email         = serializers.EmailField()
    phone         = serializers.CharField(max_length=20)
    employee_code = serializers.CharField(max_length=30, required=False, allow_null=True, allow_blank=True)
    work_type     = serializers.ChoiceField(choices=['FULL_TIME', 'PART_TIME', 'MINIJOB'])
    role          = serializers.ChoiceField(choices=['ADMIN', 'MANAGER', 'WORKER'], default='WORKER')
    nationality  = serializers.CharField(max_length=100, required=False, default='')
    dob          = serializers.DateField(required=False, allow_null=True)
    iban         = serializers.CharField(max_length=34,  required=False, default='')
    bic          = serializers.CharField(max_length=11,  required=False, default='')
    house_number = serializers.CharField(max_length=20,  required=False, default='')
    street       = serializers.CharField(max_length=200, required=False, default='')
    city         = serializers.CharField(max_length=100, required=False, default='')
    country      = serializers.CharField(max_length=100, required=False, default='')
    zip_code     = serializers.CharField(max_length=20,  required=False, default='')

    def validate_email(self, value):
        value = value.lower()
        # Allow re-hire: if the email belongs to an existing user, that's fine —
        # capacity check and org re-assignment happen in validate() and create().
        if Organisation.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'This email is already assigned to an organisation account '
                'and cannot be used for a worker.'
            )
        return value

    def validate_phone(self, value):
        digits = ''.join(c for c in value if c.isdigit())
        if len(digits) < 6:
            raise serializers.ValidationError('Phone number is too short.')
        return digits

    def validate_employee_code(self, value):
        if not value:
            return value
        if User.objects.filter(employee_code=value).exists():
            raise serializers.ValidationError('This employee code is already in use.')
        return value

    def validate(self, data):
        """
        Capacity check: enforce work-type limits across all current active jobs.
        Only applies if the user already exists in the system.
        """
        email     = data.get('email', '')
        phone     = data.get('phone', '')
        work_type = data.get('work_type', '')

        existing_user = (
            User.objects.filter(email=email).first() or
            User.objects.filter(phone=phone).first()
        )

        if existing_user:
            current_jobs = list(
                JobHistory.objects.filter(user=existing_user, is_current=True)
                .values_list('work_type', flat=True)
            )

            def capacity_ok(new_wt, current):
                full = current.count('FULL_TIME')
                part = current.count('PART_TIME')
                mini = current.count('MINIJOB')
                if new_wt == 'FULL_TIME':
                    return full == 0 and part == 0 and mini == 0
                if new_wt == 'PART_TIME':
                    return full == 0 and part < 2 and (part + 1 + mini <= 3)
                if new_wt == 'MINIJOB':
                    return full == 0 and mini < 4 and (part * 2 + mini + 1 <= 4)
                return False

            if not capacity_ok(work_type, current_jobs):
                raise serializers.ValidationError({
                    'work_type': (
                        f'This person already has these active job(s): {current_jobs}. '
                        f'Cannot add another {work_type}. '
                        'Rules: 1 full-time only, up to 2 part-time, '
                        'up to 4 mini-jobs, or 1 part-time + 2 mini-jobs.'
                    )
                })

        return data

    def create(self, validated_data):
        from timetable_app.models import generate_user_id, generate_worker_password
        from django.utils import timezone
        from django.db import transaction

        org = validated_data.pop('org')

        with transaction.atomic():
            email     = validated_data.get('email')
            phone     = validated_data.get('phone')
            work_type = validated_data.get('work_type')
            role      = validated_data.get('role', 'WORKER')

            # Check if this person already has an account (re-hire flow)
            existing = (
                User.objects.filter(email=email).first() or
                User.objects.filter(phone=phone).first()
            )

            if existing:
                # Close any open JobHistory records for all orgs (worker is moving)
                JobHistory.objects.filter(user=existing, is_current=True).update(
                    left_at=timezone.now(),
                    is_current=False,
                )
                # Re-assign to the new org
                existing.org       = org
                existing.work_type = work_type
                existing.role      = role
                existing.save()

                JobHistory.objects.create(
                    user=existing, org=org, work_type=work_type,
                    is_current=True, created_by=org,
                )
                return existing, None  # no new plain_password for re-hired user

            # Brand-new user
            full_name    = f"{validated_data.get('first_name', '')} {validated_data.get('last_name', '')}".strip()
            raw_password = generate_worker_password(length=12)
            uid          = generate_user_id()

            user = User(
                user_id       = uid,
                employee_code = validated_data.get('employee_code') or None,
                first_name    = validated_data.get('first_name', ''),
                last_name     = validated_data.get('last_name',  ''),
                full_name     = full_name,
                email         = email,
                phone         = phone,
                nationality   = validated_data.get('nationality', ''),
                dob           = validated_data.get('dob'),
                iban          = validated_data.get('iban', ''),
                bic           = validated_data.get('bic', ''),
                role          = role,
                work_type     = work_type,
                org           = org,
                plain_password = raw_password,
            )
            user.set_password(raw_password)
            user.save()

            JobHistory.objects.create(
                user=user, org=org, work_type=work_type,
                is_current=True, created_by=org,
            )

        return user, raw_password


# ===========================================================================
# Global User Search Serializer
# ===========================================================================

class GlobalUserSearchSerializer(serializers.ModelSerializer):
    """
    Read-only: safe view of a user for the org admin's global search.
    Shows name, contact info, current org, and work status.
    No sensitive fields (password, IBAN, BIC) exposed.
    """
    current_org = serializers.SerializerMethodField()
    work_status = serializers.CharField(source='work_type', read_only=True)

    class Meta:
        model  = User
        fields = ['full_name', 'email', 'phone', 'current_org', 'work_status']

    def get_current_org(self, obj):
        if obj.org:
            return {'name': obj.org.name, 'org_id': obj.org.org_id}
        return None