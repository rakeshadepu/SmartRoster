"""
models.py — Timetable Planner
Phase 1: Foundation models with custom User, Organisation,
         WorkTypeLimit, Availability, Timetable, Shift
"""

import secrets
import string
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


# ---------------------------------------------------------------------------
# Base64url alphabet (A–Z, a–z, 0–9, -, _)  → 64 chars
# 11-character ID gives 64^11 = ~73 quintillion unique combinations
# ---------------------------------------------------------------------------
BASE64URL_ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits + '-_'
USER_ID_LENGTH = 11


def generate_user_id():
    """
    Generate a globally unique 11-character Base64url user ID.
    Characters: A-Z (26) + a-z (26) + 0-9 (10) + '-' + '_' = 64 chars
    Space: 64^11 ≈ 73.8 quintillion combinations.

    Uses secrets.choice for cryptographically secure randomness.
    Retries until a unique ID is found (collision probability is negligible).

    Uses apps.get_model() to avoid circular imports — safe to call
    both from signals (pre_save) and from setup scripts.
    """
    from django.apps import apps
    UserModel = apps.get_model('timetable_app', 'User')
    while True:
        uid = ''.join(secrets.choice(BASE64URL_ALPHABET) for _ in range(USER_ID_LENGTH))
        if not UserModel.objects.filter(user_id=uid).exists():
            return uid


def generate_worker_password(length=10):
    """
    Generate a random human-readable password.
    Mix of uppercase, lowercase, digits and safe special chars.
    Shown ONCE to the employee when creating a worker — never stored in plain text.
    """
    alphabet = string.ascii_letters + string.digits + '!@#$%'
    # Ensure at least one of each category
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice('!@#$%'),
    ]
    password += [secrets.choice(alphabet) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)



ORG_ID_LENGTH = 8


def generate_org_id():
    """
    Generate a globally unique 8-character Base64url organisation ID.
    Alphabet: A-Z (26) + a-z (26) + 0-9 (10) + '-' + '_' = 64 characters.
    Space: 64^8 = 281,474,976,710,656 (~281 trillion) unique combinations.

    Used in all org-scoped URLs:  /org/<org_id>/...
    """
    from django.apps import apps
    OrgModel = apps.get_model('timetable_app', 'Organisation')
    while True:
        oid = ''.join(secrets.choice(BASE64URL_ALPHABET) for _ in range(ORG_ID_LENGTH))
        if not OrgModel.objects.filter(org_id=oid).exists():
            return oid

# ---------------------------------------------------------------------------
# Organisation
# ---------------------------------------------------------------------------
class Organisation(models.Model):
    """
    Represents a company, school, or any organisation using the planner.

    Registration flow:
        1.  Organisation registers at /api/org/register/ with name, email, password.
        2.  On success, gets back an org_token (JWT-like simple token) to log in with.
        3.  POST /api/org/login/  → receives session token.
        4.  With that token, the org admin creates Employee accounts.
        5.  Employees then log in via /api/auth/login/ and manage workers normally.

    password_hash stores bcrypt hash via Django's make_password / check_password.
    email is the org's login identifier (unique).
    """
    org_id       = models.CharField(
                       max_length=8, unique=True, db_index=True, blank=True, default='',
                       help_text='8-char Base64url public identifier used in all org URLs'
                   )
    name         = models.CharField(max_length=200, unique=True)
    email        = models.EmailField(unique=True, blank=True, default='', help_text='Login email for the organisation admin')
    password     = models.CharField(max_length=255, blank=True, default='', help_text='Hashed password')
    owner_name   = models.CharField(max_length=150, blank=True, default='', help_text='Full name of the organisation owner/admin')
    phone        = models.CharField(max_length=20,  blank=True, default='', help_text='Phone with country code e.g. +4917612345678')
    country_code = models.CharField(max_length=6,   blank=True, default='', help_text='Dial code e.g. +49')
    # Address
    house_number = models.CharField(max_length=20,  blank=True, default='')
    street       = models.CharField(max_length=200, blank=True, default='')
    city         = models.CharField(max_length=100, blank=True, default='')
    country      = models.CharField(max_length=100, blank=True, default='')
    zip_code     = models.CharField(max_length=20,  blank=True, default='')
    shop_open    = models.TimeField(default='08:00', help_text='Daily opening time (HH:MM)')
    shop_close   = models.TimeField(default='20:00', help_text='Daily closing time (HH:MM)')
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.org_id:
            self.org_id = generate_org_id()
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)

    def __str__(self):
        return f'{self.name} <{self.email}> ({self.shop_open}–{self.shop_close})'

    class Meta:
        ordering = ['name']
        verbose_name        = 'Organisation'
        verbose_name_plural = 'Organisations'


# ---------------------------------------------------------------------------
# Work Type Hour Limits
# ---------------------------------------------------------------------------
class WorkTypeLimit(models.Model):
    """
    Defines the maximum weekly working hours for each employment type
    within an organisation. Employees can adjust these at any time.

    Defaults:
        FULL_TIME  → 40 hrs/week
        PART_TIME  → 20 hrs/week
        MINIJOB    → 10 hrs/week
    """
    class WorkType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full Time'
        PART_TIME = 'PART_TIME', 'Part Time'
        MINIJOB   = 'MINIJOB',   'Mini Job'

    org            = models.ForeignKey(Organisation, on_delete=models.CASCADE,
                                       related_name='work_limits')
    work_type      = models.CharField(max_length=20, choices=WorkType.choices)
    hours_per_week = models.PositiveSmallIntegerField(
        help_text='Maximum working hours per week for this employment type'
    )

    class Meta:
        unique_together = ('org', 'work_type')
        verbose_name        = 'Work Type Limit'
        verbose_name_plural = 'Work Type Limits'

    def __str__(self):
        return f'{self.org.name} | {self.work_type}: {self.hours_per_week}h/week'


# ---------------------------------------------------------------------------
# Custom User Manager
# ---------------------------------------------------------------------------
class UserManager(BaseUserManager):
    """
    Custom manager for the User model.
    Handles creation of workers (by employee) and superusers.
    """

    def create_user(self, user_id, full_name, password=None, **extra_fields):
        if not user_id:
            raise ValueError('user_id is required')
        if not full_name:
            raise ValueError('full_name is required')
        user = self.model(user_id=user_id, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_id, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.EMPLOYEE)
        return self.create_user(user_id, full_name, password, **extra_fields)


# ---------------------------------------------------------------------------
# Custom User Model
# ---------------------------------------------------------------------------
class User(AbstractBaseUser, PermissionsMixin):
    """
    Central user model for both Employees and Workers.

    user_id:
        11-character Base64url encoded string.
        Alphabet: A-Z + a-z + 0-9 + '-' + '_'  (64 characters)
        Space:    64^11 ≈ 73.8 quintillion combinations.
        Globally unique — same namespace across all organisations.
        Auto-generated on creation, never editable.

    role:
        EMPLOYEE — manager/admin; full CRUD on workers and timetables.
        WORKER   — staff member; can only submit availability and view timetable.

    work_type:
        Only applies to WORKER role. Determines weekly hour limit via WorkTypeLimit.

    plain_password:
        Stored TEMPORARILY (plain text) only during the API response
        when a worker account is first created. After that, it is cleared.
        This allows the employee to see it once and hand it to the worker.
        The actual authentication uses the hashed `password` field.
    """

    class Role(models.TextChoices):
        EMPLOYEE = 'EMPLOYEE', 'Employee (Manager)'
        WORKER   = 'WORKER',   'Worker'
        # ADMIN role removed — org owner IS the Organisation, not a User row

    class WorkType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full Time'
        PART_TIME = 'PART_TIME', 'Part Time'
        MINIJOB   = 'MINIJOB',   'Mini Job'

    # --- Identity ---
    user_id     = models.CharField(
        max_length=11, unique=True, db_index=True, editable=False,
        help_text='Auto-generated 11-char Base64url unique identifier'
    )
    first_name  = models.CharField(max_length=80, blank=True, default='')
    last_name   = models.CharField(max_length=80, blank=True, default='')
    full_name   = models.CharField(max_length=150)

    # --- Contact (globally unique across all orgs) ---
    email       = models.EmailField(unique=True, blank=True, null=True,
                                    help_text='Globally unique email for this person')
    phone       = models.CharField(max_length=20, unique=True, blank=True, null=True,
                                   help_text='Globally unique phone digits for this person')

    # --- Personal details ---
    nationality = models.CharField(max_length=100, blank=True, default='')
    dob         = models.DateField(null=True, blank=True, help_text='Date of birth')

    # --- Banking ---
    iban        = models.CharField(max_length=34, blank=True, default='')
    bic         = models.CharField(max_length=11, blank=True, default='')

    # --- Role & Employment ---
    role        = models.CharField(max_length=20, choices=Role.choices, default=Role.WORKER)
    work_type   = models.CharField(
        max_length=20, choices=WorkType.choices,
        blank=True, null=True,
        help_text='Employment type — relevant for WORKER and EMPLOYEE roles'
    )

    # --- Organisation ---
    org         = models.ForeignKey(
        Organisation, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='users'
    )

    # --- Django required fields ---
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    # --- One-time plain password (cleared after first read) ---
    plain_password = models.CharField(
        max_length=50, blank=True, null=True,
        help_text='Shown once on creation, then cleared'
    )

    objects = UserManager()

    USERNAME_FIELD  = 'user_id'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        ordering = ['full_name']
        verbose_name        = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f'[{self.user_id}] {self.full_name} ({self.role})'

    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def is_worker(self):
        return self.role == self.Role.WORKER

    def get_weekly_hour_limit(self):
        """
        Returns the weekly hour limit for this worker based on their
        work_type and their organisation's WorkTypeLimit settings.
        Falls back to system defaults if no custom limit is set.
        """
        defaults = {
            self.WorkType.FULL_TIME: 40,
            self.WorkType.PART_TIME: 20,
            self.WorkType.MINIJOB:   10,
        }
        if not self.work_type:
            return 0
        if self.org:
            try:
                limit = WorkTypeLimit.objects.get(org=self.org, work_type=self.work_type)
                return limit.hours_per_week
            except WorkTypeLimit.DoesNotExist:
                pass
        return defaults.get(self.work_type, 0)


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------
class Availability(models.Model):
    """
    A worker's declared availability for a specific day in a given week.

    Workers submit this each Saturday for the NEXT week (Mon–Sun).
    They can only CREATE — not update or delete — their submissions.
    Only employees can make any modifications.

    week_start: Always the Monday of the target week.
    start_time: The time the worker is available to begin working that day.
    """

    class Day(models.TextChoices):
        MONDAY    = 'MON', 'Monday'
        TUESDAY   = 'TUE', 'Tuesday'
        WEDNESDAY = 'WED', 'Wednesday'
        THURSDAY  = 'THU', 'Thursday'
        FRIDAY    = 'FRI', 'Friday'
        SATURDAY  = 'SAT', 'Saturday'
        SUNDAY    = 'SUN', 'Sunday'

    worker       = models.ForeignKey(User, on_delete=models.CASCADE,
                                     related_name='availabilities',
                                     limit_choices_to={'role': User.Role.WORKER})
    week_start   = models.DateField(help_text='Monday of the target week')
    day          = models.CharField(max_length=3, choices=Day.choices)
    start_time   = models.TimeField(help_text='Preferred start time on this day')
    submitted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('worker', 'week_start', 'day')
        ordering        = ['week_start', 'day', 'worker__full_name']
        verbose_name        = 'Availability'
        verbose_name_plural = 'Availabilities'

    def __str__(self):
        return (f'{self.worker.full_name} | {self.get_day_display()} '
                f'{self.week_start} @ {self.start_time}')


# ---------------------------------------------------------------------------
# Timetable
# ---------------------------------------------------------------------------
class Timetable(models.Model):
    """
    A generated weekly timetable for an organisation.
    Contains many Shifts, one per worker per working day.

    status:
        DRAFT     — generated but not yet published to workers.
        PUBLISHED — visible to all workers.
    """

    class Status(models.TextChoices):
        DRAFT     = 'DRAFT',     'Draft'
        PUBLISHED = 'PUBLISHED', 'Published'

    org          = models.ForeignKey(Organisation, on_delete=models.CASCADE,
                                     related_name='timetables')
    week_start   = models.DateField(help_text='Monday of the timetable week')
    generated_at = models.DateTimeField(auto_now_add=True)
    status       = models.CharField(max_length=20, choices=Status.choices,
                                    default=Status.DRAFT)

    class Meta:
        unique_together = ('org', 'week_start')
        ordering        = ['-week_start']
        verbose_name        = 'Timetable'
        verbose_name_plural = 'Timetables'

    def __str__(self):
        return f'{self.org.name} | Week of {self.week_start} [{self.status}]'

    @property
    def week_end(self):
        from datetime import timedelta
        return self.week_start + timedelta(days=6)


# ---------------------------------------------------------------------------
# Shift
# ---------------------------------------------------------------------------
class Shift(models.Model):
    """
    A single work shift assigned to a worker within a Timetable.

    Constraints enforced by the scheduler:
      - start_time >= shop_open
      - end_time   <= shop_close
      - (end_time - start_time) <= 8 hours per day
      - sum of all shift hours for worker in week <= weekly hour limit
    """

    class Day(models.TextChoices):
        MONDAY    = 'MON', 'Monday'
        TUESDAY   = 'TUE', 'Tuesday'
        WEDNESDAY = 'WED', 'Wednesday'
        THURSDAY  = 'THU', 'Thursday'
        FRIDAY    = 'FRI', 'Friday'
        SATURDAY  = 'SAT', 'Saturday'
        SUNDAY    = 'SUN', 'Sunday'

    timetable  = models.ForeignKey(Timetable, on_delete=models.CASCADE,
                                   related_name='shifts')
    worker     = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='shifts',
                                   limit_choices_to={'role': User.Role.WORKER})
    day        = models.CharField(max_length=3, choices=Day.choices)
    start_time = models.TimeField()
    end_time   = models.TimeField()
    hours      = models.DecimalField(max_digits=4, decimal_places=2,
                                     help_text='Calculated shift duration in hours')

    class Meta:
        unique_together = ('timetable', 'worker', 'day')
        ordering        = ['day', 'start_time']
        verbose_name        = 'Shift'
        verbose_name_plural = 'Shifts'

    def __str__(self):
        return (f'{self.worker.full_name} | {self.get_day_display()} '
                f'{self.start_time}–{self.end_time} ({self.hours}h)')

    def save(self, *args, **kwargs):
        """Auto-calculate hours from start and end time."""
        from datetime import datetime, date
        start_dt = datetime.combine(date.today(), self.start_time)
        end_dt   = datetime.combine(date.today(), self.end_time)
        delta    = end_dt - start_dt
        self.hours = round(delta.seconds / 3600, 2)
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Job History  (tracks which org a user has worked for and when)
# ---------------------------------------------------------------------------
class JobHistory(models.Model):
    """
    Immutable log of a user's employment at an organisation.
    Created automatically when a user is added to an org.
    A new record is added each time they change organisation.
    Never deleted — provides a full audit trail.
    """
    user       = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='job_history')
    org        = models.ForeignKey(Organisation, on_delete=models.CASCADE,
                                   related_name='job_history')
    work_type  = models.CharField(max_length=20, blank=True, default='')
    joined_at  = models.DateTimeField(auto_now_add=True)
    left_at    = models.DateTimeField(null=True, blank=True,
                                      help_text='Set when user leaves or changes org')
    is_current = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        Organisation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_employments',
        help_text='Org admin that originally created/added this user'
    )

    class Meta:
        ordering = ['-joined_at']

    def __str__(self):
        status = 'current' if self.is_current else f'left {self.left_at}'
        return f'{self.user.full_name} @ {self.org.name} ({status})'


# ---------------------------------------------------------------------------
# Organisation Session Token
# ---------------------------------------------------------------------------
class OrgToken(models.Model):
    """
    Simple token-based session for Organisation login.

    When an org logs in via POST /api/org/login/, a secure random token is
    generated and stored here. The token is sent in the Authorization header
    as:   Org-Token <token>

    This is separate from the JWT system used by Employee/Worker accounts,
    keeping org-admin access cleanly isolated.

    Tokens expire after 24 hours (checked on every request).
    """
    org        = models.ForeignKey(Organisation, on_delete=models.CASCADE,
                                   related_name='tokens')
    token      = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'OrgToken({self.org.name}, expires={self.expires_at})'

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @classmethod
    def create_for_org(cls, org):
        import secrets
        from django.utils import timezone
        import datetime
        token = secrets.token_hex(32)
        expires = timezone.now() + datetime.timedelta(hours=24)
        return cls.objects.create(org=org, token=token, expires_at=expires)
