"""
models.py — Timetable Planner
==============================

Phase 1: Foundation models

Models defined here:
    - Organisation          Company / school using the planner
    - WorkTypeLimit         Per-org weekly hour caps per employment type
    - User                  Workers (JWT-authenticated staff members)
    - Availability          Worker-declared availability per day per week
    - Timetable             Generated weekly schedule for an organisation
    - Shift                 Single work shift inside a timetable
    - JobHistory            Immutable audit log of every org a user has worked for
    - OrgToken              Session token for organisation admin login

Design decisions:
    - No is_active on Organisation or User.
      Workers are detached from an org (User.org = None) when removed;
      they are never soft-deleted. Re-hiring simply sets User.org again
      and opens a new JobHistory record.
    - JobHistory is append-only. left_at + is_current=False marks departure.
      Every organisation a user ever worked for is preserved forever.
    - Organisation management uses Org-Token auth (separate from JWT).
    - All JWT-authenticated users are Workers — there is only one user role.
"""

import secrets
import string
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


# ===========================================================================
# ID Generation Utilities
# ===========================================================================

# Base64url alphabet: A–Z, a–z, 0–9, -, _  →  64 characters
BASE64URL_ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits + '-_'

USER_ID_LENGTH = 11   # 64^11 ≈ 73.8 quintillion unique combinations
ORG_ID_LENGTH  = 8    # 64^8  ≈ 281 trillion  unique combinations


def generate_user_id():
    """
    Generate a globally unique 11-character Base64url user ID.

    Uses secrets.choice for cryptographically secure randomness.
    Retries on collision (probability is negligible but handled correctly).
    Uses apps.get_model() to avoid circular imports.
    """
    from django.apps import apps
    UserModel = apps.get_model('timetable_app', 'User')
    while True:
        uid = ''.join(secrets.choice(BASE64URL_ALPHABET) for _ in range(USER_ID_LENGTH))
        if not UserModel.objects.filter(user_id=uid).exists():
            return uid


def generate_org_id():
    """
    Generate a globally unique 8-character Base64url organisation ID.
    Used in all org-scoped URLs: /org/<org_id>/...

    Uses apps.get_model() to avoid circular imports.
    """
    from django.apps import apps
    OrgModel = apps.get_model('timetable_app', 'Organisation')
    while True:
        oid = ''.join(secrets.choice(BASE64URL_ALPHABET) for _ in range(ORG_ID_LENGTH))
        if not OrgModel.objects.filter(org_id=oid).exists():
            return oid


def generate_worker_password(length=10):
    """
    Generate a random, human-readable one-time password for a new worker.

    Guarantees at least one uppercase, one lowercase, one digit, and one
    special character. Shown ONCE to the org admin on worker creation —
    never stored in plain text after that.
    """
    alphabet = string.ascii_letters + string.digits + '!@#$%'
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice('!@#$%'),
    ]
    password += [secrets.choice(alphabet) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)


# ===========================================================================
# Organisation
# ===========================================================================

class Organisation(models.Model):
    """
    Represents a company, school, or any entity using the planner.

    Registration & login flow:
        1.  POST /api/org/register/  →  org created, OrgToken returned.
        2.  POST /api/org/login/     →  new OrgToken returned.
        3.  Org admin uses  Authorization: Org-Token <token>  on all admin calls.
        4.  Org admin creates Worker accounts (User rows) for their staff.
        5.  Workers log in via  POST /api/auth/login/  and receive a JWT.

    Removal flow (worker leaves or is removed):
        1.  Set  User.org = None.
        2.  Set  JobHistory.left_at = now(),  is_current = False.
        Worker can later be re-hired by any org — just set User.org again
        and open a new JobHistory record.

    Notes:
        - No is_active field. Organisations are never soft-deleted here.
        - password stores a bcrypt hash via set_password() / check_password().
        - shop_open / shop_close drive shift scheduling constraints.
    """

    org_id       = models.CharField(
                       max_length=8, unique=True, db_index=True,
                       blank=True, default='',
                       help_text='8-char Base64url public identifier used in all org URLs'
                   )
    name         = models.CharField(max_length=200, unique=True)
    email        = models.EmailField(
                       unique=True, blank=True, default='',
                       help_text='Login email for the organisation admin'
                   )
    password     = models.CharField(
                       max_length=255, blank=True, default='',
                       help_text='Bcrypt-hashed password — never store plain text here'
                   )
    owner_name   = models.CharField(
                       max_length=150, blank=True, default='',
                       help_text='Full name of the organisation owner / admin'
                   )
    phone        = models.CharField(
                       max_length=20, blank=True, default='',
                       help_text='Phone number with country code, e.g. +4917612345678'
                   )
    country_code = models.CharField(
                       max_length=6, blank=True, default='',
                       help_text='Dial code, e.g. +49'
                   )

    # -- Address --
    house_number = models.CharField(max_length=20,  blank=True, default='')
    street       = models.CharField(max_length=200, blank=True, default='')
    city         = models.CharField(max_length=100, blank=True, default='')
    country      = models.CharField(max_length=100, blank=True, default='')
    zip_code     = models.CharField(max_length=20,  blank=True, default='')

    # -- Operating hours (used as scheduling bounds for shifts) --
    shop_open    = models.TimeField(
                       default='08:00',
                       help_text='Daily opening time (HH:MM) — no shift may start before this'
                   )
    shop_close   = models.TimeField(
                       default='20:00',
                       help_text='Daily closing time (HH:MM) — no shift may end after this'
                   )

    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
        ordering            = ['name']
        verbose_name        = 'Organisation'
        verbose_name_plural = 'Organisations'


# ===========================================================================
# Work Type Hour Limits
# ===========================================================================

class WorkTypeLimit(models.Model):
    """
    Maximum weekly working hours for each employment type within an org.

    Org admins can customise these at any time. Falls back to system
    defaults if no custom limit exists for a given work type:
        FULL_TIME  →  40 hrs / week
        PART_TIME  →  20 hrs / week
        MINIJOB    →  10 hrs / week
    """

    class WorkType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full Time'
        PART_TIME = 'PART_TIME', 'Part Time'
        MINIJOB   = 'MINIJOB',   'Mini Job'

    org            = models.ForeignKey(
                         Organisation, on_delete=models.CASCADE,
                         related_name='work_limits'
                     )
    work_type      = models.CharField(max_length=20, choices=WorkType.choices)
    hours_per_week = models.PositiveSmallIntegerField(
                         help_text='Maximum working hours per week for this employment type'
                     )

    def __str__(self):
        return f'{self.org.name} | {self.work_type}: {self.hours_per_week} h/week'

    class Meta:
        unique_together     = ('org', 'work_type')
        verbose_name        = 'Work Type Limit'
        verbose_name_plural = 'Work Type Limits'


# ===========================================================================
# Custom User Manager
# ===========================================================================

class UserManager(BaseUserManager):
    """
    Custom manager for the User model.
    Handles creation of workers and Django superusers.
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
        extra_fields.setdefault('role', User.Role.WORKER)
        return self.create_user(user_id, full_name, password, **extra_fields)


# ===========================================================================
# User (Worker)
# ===========================================================================

class User(AbstractBaseUser, PermissionsMixin):
    """
    Central user model. All JWT-authenticated users are Workers.

    user_id
        Auto-generated 11-character Base64url string — never editable.
        Globally unique across all organisations.

    role
        Only one role: WORKER. Organisation management is handled via
        Org-Token auth — no separate admin user row is needed.

    org
        The organisation this worker currently belongs to.
        Set to None when a worker is removed from an org.
        Can be set to any org when re-hired.

    work_type
        Determines the weekly hour limit via WorkTypeLimit.

    plain_password
        Stored temporarily in plain text ONLY during the API response
        when a worker account is first created, so the org admin can
        hand the credential to the worker. Cleared immediately after.

    No is_active field.
        Workers are never soft-deleted. Removing a worker from an org
        simply sets User.org = None. Re-hiring sets it again and opens
        a new JobHistory entry.
    """

    class Role(models.TextChoices):
        WORKER = 'WORKER', 'Worker'

    class WorkType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full Time'
        PART_TIME = 'PART_TIME', 'Part Time'
        MINIJOB   = 'MINIJOB',   'Mini Job'

    # -- Identity --
    user_id    = models.CharField(
                     max_length=11, unique=True, db_index=True, editable=False,
                     help_text='Auto-generated 11-char Base64url unique identifier'
                 )
    first_name = models.CharField(max_length=80,  blank=True, default='')
    last_name  = models.CharField(max_length=80,  blank=True, default='')
    full_name  = models.CharField(max_length=150)

    # -- Contact (globally unique across all orgs) --
    email      = models.EmailField(
                     unique=True, blank=True, null=True,
                     help_text='Globally unique email address for this person'
                 )
    phone      = models.CharField(
                     max_length=20, unique=True, blank=True, null=True,
                     help_text='Globally unique phone number for this person'
                 )

    # -- Personal details --
    nationality = models.CharField(max_length=100, blank=True, default='')
    dob         = models.DateField(null=True, blank=True, help_text='Date of birth')

    # -- Banking --
    iban = models.CharField(max_length=34, blank=True, default='')
    bic  = models.CharField(max_length=11, blank=True, default='')

    # -- Role & Employment --
    role      = models.CharField(
                    max_length=20, choices=Role.choices, default=Role.WORKER
                )
    work_type = models.CharField(
                    max_length=20, choices=WorkType.choices,
                    blank=True, null=True,
                    help_text='Employment type — determines weekly hour limit'
                )

    # -- Current Organisation (None when not employed anywhere) --
    org = models.ForeignKey(
              Organisation, on_delete=models.SET_NULL,
              null=True, blank=True, related_name='users',
              help_text='Currently active organisation. Null = not employed anywhere.'
          )

    # -- Django internals --
    is_staff   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # -- One-time plain password (cleared after first read) --
    plain_password = models.CharField(
                         max_length=50, blank=True, null=True,
                         help_text='Shown once on creation to the org admin, then cleared'
                     )

    objects = UserManager()

    USERNAME_FIELD  = 'user_id'
    REQUIRED_FIELDS = ['full_name']

    # ------------------------------------------------------------------
    # Properties & helpers
    # ------------------------------------------------------------------

    @property
    def is_worker(self):
        """All JWT-authenticated users are workers."""
        return True

    def get_weekly_hour_limit(self):
        """
        Return the weekly hour limit for this worker.

        Looks up the org's custom WorkTypeLimit first. Falls back to
        system defaults if no custom limit is configured.
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

    def __str__(self):
        org_name = self.org.name if self.org else 'unassigned'
        return f'[{self.user_id}] {self.full_name} ({self.role}) @ {org_name}'

    class Meta:
        ordering            = ['full_name']
        verbose_name        = 'User'
        verbose_name_plural = 'Users'


# ===========================================================================
# Availability
# ===========================================================================

class Availability(models.Model):
    """
    A worker's declared availability for a specific day in a given week.

    Submission rules:
        - Workers submit each Saturday for the NEXT week (Mon–Sun).
        - Workers may only CREATE entries — not update or delete them.
        - Only org admins (employees) may modify or delete entries.

    week_start   Always the Monday of the target week.
    start_time   The earliest time the worker can begin a shift that day.
    end_time     The latest time the worker is available to work that day.
                 Allows the scheduler to respect the worker's upper bound,
                 not just their lower bound.
    """

    class Day(models.TextChoices):
        MONDAY    = 'MON', 'Monday'
        TUESDAY   = 'TUE', 'Tuesday'
        WEDNESDAY = 'WED', 'Wednesday'
        THURSDAY  = 'THU', 'Thursday'
        FRIDAY    = 'FRI', 'Friday'
        SATURDAY  = 'SAT', 'Saturday'
        SUNDAY    = 'SUN', 'Sunday'

    worker       = models.ForeignKey(
                       User, on_delete=models.CASCADE,
                       related_name='availabilities',
                       limit_choices_to={'role': User.Role.WORKER}
                   )
    week_start   = models.DateField(help_text='Monday of the target week')
    day          = models.CharField(max_length=3, choices=Day.choices)
    start_time   = models.TimeField(help_text='Earliest available start time on this day')
    end_time     = models.TimeField(
                       null=True, blank=True,
                       help_text='Latest available end time on this day (optional — worker sets upper bound)'
                   )
    submitted_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        end = f'–{self.end_time}' if self.end_time else ''
        return (
            f'{self.worker.full_name} | {self.get_day_display()} '
            f'{self.week_start} @ {self.start_time}{end}'
        )

    class Meta:
        unique_together     = ('worker', 'week_start', 'day')
        ordering            = ['week_start', 'day', 'worker__full_name']
        verbose_name        = 'Availability'
        verbose_name_plural = 'Availabilities'


# ===========================================================================
# Timetable
# ===========================================================================

class Timetable(models.Model):
    """
    A generated weekly timetable for an organisation.
    Contains many Shifts — one per worker per working day.

    status:
        DRAFT      Generated but not yet visible to workers.
        PUBLISHED  Visible to all workers in the org.
    """

    class Status(models.TextChoices):
        DRAFT     = 'DRAFT',     'Draft'
        PUBLISHED = 'PUBLISHED', 'Published'

    org          = models.ForeignKey(
                       Organisation, on_delete=models.SET_NULL,
                       null=True, blank=True, related_name='timetables'
                   )
    week_start   = models.DateField(help_text='Monday of the timetable week')
    generated_at = models.DateTimeField(auto_now_add=True)
    status       = models.CharField(
                       max_length=20, choices=Status.choices, default=Status.DRAFT
                   )

    @property
    def week_end(self):
        from datetime import timedelta
        return self.week_start + timedelta(days=6)

    def __str__(self):
        org_name = self.org.name if self.org else 'No Org'
        return f'{org_name} | Week of {self.week_start} [{self.status}]'

    class Meta:
        unique_together     = ('org', 'week_start')
        ordering            = ['-week_start']
        verbose_name        = 'Timetable'
        verbose_name_plural = 'Timetables'


# ===========================================================================
# Shift
# ===========================================================================

class Shift(models.Model):
    """
    A single work shift assigned to a worker within a Timetable.

    Constraints enforced by the scheduler at generation time:
        - start_time  >=  org.shop_open
        - end_time    <=  org.shop_close
        - (end_time - start_time)  <=  8 hours per shift
        - Total shift hours for worker in week  <=  weekly hour limit

    hours is auto-calculated from start_time and end_time on every save.
    """

    class Day(models.TextChoices):
        MONDAY    = 'MON', 'Monday'
        TUESDAY   = 'TUE', 'Tuesday'
        WEDNESDAY = 'WED', 'Wednesday'
        THURSDAY  = 'THU', 'Thursday'
        FRIDAY    = 'FRI', 'Friday'
        SATURDAY  = 'SAT', 'Saturday'
        SUNDAY    = 'SUN', 'Sunday'

    timetable  = models.ForeignKey(
                     Timetable, on_delete=models.CASCADE, related_name='shifts'
                 )
    worker     = models.ForeignKey(
                     User, on_delete=models.CASCADE, related_name='shifts',
                     limit_choices_to={'role': User.Role.WORKER}
                 )
    day        = models.CharField(max_length=3, choices=Day.choices)
    start_time = models.TimeField()
    end_time   = models.TimeField()
    hours      = models.DecimalField(
                     max_digits=4, decimal_places=2,
                     help_text='Shift duration in hours — auto-calculated on save'
                 )

    def save(self, *args, **kwargs):
        """Auto-calculate hours from start_time and end_time before saving."""
        from datetime import datetime, date
        start_dt  = datetime.combine(date.today(), self.start_time)
        end_dt    = datetime.combine(date.today(), self.end_time)
        self.hours = round((end_dt - start_dt).seconds / 3600, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f'{self.worker.full_name} | {self.get_day_display()} '
            f'{self.start_time}–{self.end_time} ({self.hours} h)'
        )

    class Meta:
        unique_together     = ('timetable', 'worker', 'day')
        ordering            = ['day', 'start_time']
        verbose_name        = 'Shift'
        verbose_name_plural = 'Shifts'


# ===========================================================================
# Job History
# ===========================================================================

class JobHistory(models.Model):
    """
    Immutable audit log of every organisation a user has ever worked for.

    Creation:
        A new record is created automatically whenever a user is added to
        an organisation (User.org is set).

    Departure:
        When a worker is removed from an org (User.org → None), set:
            left_at    = timezone.now()
            is_current = False
        The record is NEVER deleted — it provides a full employment history.

    Re-hire:
        When a user joins any org again, a brand-new JobHistory record is
        opened. Multiple records for the same (user, org) pair are allowed
        and expected over time.

    Fields:
        work_type    Snapshot of the employment type at the time of joining.
        joined_at    Auto-set to now() on creation.
        left_at      Set when the worker leaves this org (null while current).
        is_current   True only for the active employment record.
        created_by   The org that originally added this user.
    """

    user       = models.ForeignKey(
                     User, on_delete=models.CASCADE, related_name='job_history'
                 )
    org        = models.ForeignKey(
                     Organisation, on_delete=models.CASCADE, related_name='job_history'
                 )
    work_type  = models.CharField(
                     max_length=20, blank=True, default='',
                     help_text='Snapshot of work_type at the time of joining'
                 )
    joined_at  = models.DateTimeField(
                     auto_now_add=True,
                     help_text='Datetime when the user joined this organisation'
                 )
    left_at    = models.DateTimeField(
                     null=True, blank=True,
                     help_text='Datetime when the user left this organisation (null if still current)'
                 )
    is_current = models.BooleanField(
                     default=True,
                     help_text='True while the user is actively employed at this org'
                 )
    created_by = models.ForeignKey(
                     Organisation, on_delete=models.SET_NULL,
                     null=True, blank=True,
                     related_name='created_employments',
                     help_text='Org admin that added this user'
                 )

    def __str__(self):
        if self.is_current:
            status = 'current'
        else:
            status = f'left {self.left_at.strftime("%Y-%m-%d") if self.left_at else "unknown"}'
        return f'{self.user.full_name} @ {self.org.name} ({status})'

    class Meta:
        ordering            = ['-joined_at']
        verbose_name        = 'Job History'
        verbose_name_plural = 'Job Histories'


# ===========================================================================
# Organisation Session Token
# ===========================================================================

class OrgToken(models.Model):
    """
    Simple token-based session for Organisation admin login.

    Flow:
        POST /api/org/login/  →  token generated and stored here.
        Client sends:  Authorization: Org-Token <token>  on all admin requests.

    This is entirely separate from the JWT system used by Workers,
    keeping org-admin access cleanly isolated.

    Tokens expire 24 hours after creation. Expiry is checked on every request.
    """

    org        = models.ForeignKey(
                     Organisation, on_delete=models.CASCADE, related_name='tokens'
                 )
    token      = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @classmethod
    def create_for_org(cls, org):
        import datetime
        token   = secrets.token_hex(32)
        expires = timezone.now() + datetime.timedelta(hours=24)
        return cls.objects.create(org=org, token=token, expires_at=expires)

    def __str__(self):
        return f'OrgToken({self.org.name}, expires={self.expires_at})'

    class Meta:
        ordering = ['-created_at']