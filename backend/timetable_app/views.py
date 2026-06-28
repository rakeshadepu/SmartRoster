"""
views.py — Timetable Planner
==============================

API Views grouped by concern:

  Auth          LoginView, LogoutView, RefreshTokenView, MeView
                  JWT-based — workers only

  Organisation  OrgRegisterView, OrgLoginView, OrgLoginGlobalView,
                OrgLogoutView, OrgMeView, OrgListView,
                OrgPublicView, OrgJoinInfoView
                  Org-Token auth for all admin operations

  Settings      OrganisationView (GET + PATCH)
  WorkLimits    WorkTypeLimitListView (GET + POST)

  Workers       WorkerListCreateView, WorkerDetailView,
                WorkerResetPasswordView, WorkerPublicListView
                  Managed by org admin via Org-Token
                  Detach (not soft-delete) on removal — JobHistory closed

  Availability  AvailabilityView, AvailabilityDetailView
                  Workers submit; org admin reads all

  Timetable     TimetableListView, TimetableDetailView,
                TimetableGenerateView, TimetablePublishView,
                TimetableShiftEditView, TimetableShiftDeleteView,
                TimetableWorkerView, TimetablePDFView, TimetableHTMLView

  Misc          AddUserView, GlobalUserSearchView, EmailConflictView
"""

from django.contrib.auth import logout
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from timetable_app.models import (
    Organisation, WorkTypeLimit, User,
    Availability, Timetable, Shift, JobHistory,
)
from timetable_app.serializers import (
    LoginSerializer,
    UserMeSerializer,
    OrganisationSerializer,
    OrganisationUpdateSerializer,
    WorkTypeLimitSerializer,
    WorkerListSerializer,
    WorkerCreateSerializer,
    WorkerUpdateSerializer,
    WorkerPublicSerializer,
    AvailabilitySerializer,
    TimetableSerializer,
    ShiftSerializer,
)
from timetable_app.permissions import (
    IsWorker,
    IsOrgAdmin,
    IsSameOrgWorker,
    IsOwnerWorkerOrOrgAdmin,
    IsOrgAdminOrWorker,
    IsOrgAdminOrEmployee,
    IsOrgAdminOrReadOnly,
)


# ===========================================================================
# Internal helpers
# ===========================================================================

def _get_tokens(user):
    """Generate JWT access + refresh token pair for a worker."""
    refresh = RefreshToken.for_user(user)
    return {
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
    }


def _get_org_from_request(request):
    """
    Return the Organisation for the current request regardless of auth method.

    - Org-Token path  →  IsOrgAdmin middleware sets request.org
    - JWT worker path →  user.org FK
    """
    if hasattr(request, 'org') and request.org:
        return request.org
    if request.user and request.user.is_authenticated:
        return request.user.org
    return None


def _validate_org(request, org_id):
    """
    Resolve and validate the org for this request against a URL org_id.

    Returns (org, None) on success or (None, error_Response) on failure.
    """
    org = _get_org_from_request(request)
    if not org:
        return None, Response(
            {'error': 'Organisation not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    if org.org_id != org_id:
        return None, Response(
            {'error': 'Organisation mismatch.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return org, None


def _get_org_or_404(org_id):
    """Look up an Organisation by its public org_id. Returns None if absent."""
    try:
        return Organisation.objects.get(org_id=org_id)
    except Organisation.DoesNotExist:
        return None


def _open_job_history(user, org, created_by=None):
    """
    Open a new JobHistory record when a worker joins (or re-joins) an org.

    Any previously current record for this (user, org) pair is left intact —
    multiple records per pair are intentional (re-hire support).
    """
    JobHistory.objects.create(
        user=user,
        org=org,
        work_type=user.work_type or '',
        is_current=True,
        created_by=created_by,
    )


def _close_job_history(user, org):
    """
    Close all open JobHistory records for this (user, org) pair.
    Called when a worker is removed from an org.
    """
    from django.utils import timezone
    JobHistory.objects.filter(
        user=user,
        org=org,
        is_current=True,
    ).update(
        left_at=timezone.now(),
        is_current=False,
    )


# ===========================================================================
# AUTH VIEWS
# ===========================================================================

class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: { "user_id": "...", "password": "..." }

    Worker login flow:
        1. GET /api/org/<org_id>/workers/public/ — name + user_id list (no auth)
        2. Worker selects their name → user_id auto-filled
        3. Worker types password → POST here

    Returns JWT tokens + user profile on success.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user    = serializer.validated_data['user']
        tokens  = _get_tokens(user)
        profile = UserMeSerializer(user).data
        return Response({
            'success': True,
            'message': f'Welcome, {user.full_name}!',
            'tokens':  tokens,
            'user':    profile,
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Body: { "refresh": "<refresh_token>" }
    Blacklists the refresh token so it cannot be reused.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                RefreshToken(refresh_token).blacklist()
        except (TokenError, Exception):
            pass  # already invalid — acceptable
        logout(request)
        return Response(
            {'success': True, 'message': 'Logged out successfully.'},
            status=status.HTTP_200_OK,
        )


class RefreshTokenView(APIView):
    """
    POST /api/auth/refresh/
    Body: { "refresh": "<refresh_token>" }
    Returns a new access token (and rotated refresh token).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'refresh token required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            return Response({
                'access':  str(token.access_token),
                'refresh': str(token),
            })
        except TokenError as e:
            return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class MeView(APIView):
    """
    GET /api/auth/me/
    Returns the logged-in worker's profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'success': True, 'user': UserMeSerializer(request.user).data})


# ===========================================================================
# ORGANISATION SETTINGS
# ===========================================================================

class OrganisationView(APIView):
    """
    GET  /api/org/<org_id>/settings/  →  read org details
    PATCH /api/org/<org_id>/settings/ →  update shop_open / shop_close / address etc.

    Org-Token required.
    """
    permission_classes = [IsOrgAdmin]

    def _get_org(self, request, org_id):
        org = _get_org_from_request(request)
        if not org:
            return None, Response(
                {'error': 'No organisation assigned to your account.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if org.org_id != org_id:
            return None, Response(
                {'error': 'Organisation mismatch.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return org, None

    def get(self, request, org_id):
        org, err = self._get_org(request, org_id)
        if err:
            return err
        return Response({'success': True, 'organisation': OrganisationSerializer(org).data})

    def patch(self, request, org_id):
        org, err = self._get_org(request, org_id)
        if err:
            return err
        serializer = OrganisationUpdateSerializer(org, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success':      True,
                'message':      'Organisation settings updated.',
                'organisation': OrganisationSerializer(org).data,
            })
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ===========================================================================
# WORK TYPE LIMITS
# ===========================================================================

class WorkTypeLimitListView(APIView):
    """
    GET  /api/org/<org_id>/work-limits/  →  list all hour caps for this org
    POST /api/org/<org_id>/work-limits/  →  create or override a cap (upsert)

    Org-Token required.
    """
    permission_classes = [IsOrgAdmin]

    def get(self, request):
        org = request.org
        if not org:
            return Response(
                {'error': 'No organisation assigned.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        limits     = WorkTypeLimit.objects.filter(org=org)
        serializer = WorkTypeLimitSerializer(limits, many=True)
        return Response({'success': True, 'limits': serializer.data})

    def post(self, request):
        org       = request.org
        data      = {**request.data, 'org': org.id}
        work_type = data.get('work_type')

        # Upsert: update existing limit or create new one
        instance   = WorkTypeLimit.objects.filter(org=org, work_type=work_type).first()
        serializer = (
            WorkTypeLimitSerializer(instance, data=data)
            if instance
            else WorkTypeLimitSerializer(data=data)
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': f'{work_type} limit saved.',
                'limit':   serializer.data,
            }, status=status.HTTP_200_OK)
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ===========================================================================
# WORKER VIEWS
# ===========================================================================

class WorkerPublicListView(APIView):
    """
    GET /api/org/<org_id>/workers/public/   (no auth)

    Returns worker names + user_ids only — no sensitive data.
    Used on the login screen so workers can select their name from a list.
    """
    permission_classes = [AllowAny]

    def get(self, request, org_id=None):
        qs = User.objects.filter(role=User.Role.WORKER)
        if org_id:
            qs = qs.filter(org__org_id=org_id)
        return Response({
            'success': True,
            'workers': WorkerPublicSerializer(qs, many=True).data,
        })


class WorkerListCreateView(APIView):
    """
    GET  /api/org/<org_id>/workers/  →  list all workers currently in this org
    POST /api/org/<org_id>/workers/  →  create a new worker and assign to this org

    Org-Token required.

    On POST:
        - Worker is created with User.org set.
        - A JobHistory record is opened (is_current=True).
        - plain_password is returned ONCE in the response then cleared from DB.
    """
    permission_classes = [IsOrgAdmin]

    def get(self, request, org_id):
        org = request.org
        if not org or org.org_id != org_id:
            return Response(
                {'error': 'Organisation mismatch or not found.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        from django.db.models import Subquery, OuterRef
        from timetable_app.models import JobHistory

        # Annotate each worker with their most recent joined_at for this org
        latest_join = JobHistory.objects.filter(
            user=OuterRef('pk'),
            org=org,
            is_current=True,
        ).order_by('-joined_at').values('joined_at')[:1]

        qs = (
            User.objects
            .filter(org=org, role=User.Role.WORKER)
            .annotate(latest_joined=Subquery(latest_join))
            .order_by('-latest_joined')   # newest first by default
        )

        work_type = request.query_params.get('work_type')
        if work_type:
            qs = qs.filter(work_type=work_type)

        return Response({
            'success': True,
            'count':   qs.count(),
            'workers': WorkerListSerializer(qs, many=True).data,
        })

    def post(self, request, org_id):
        org, error = _validate_org(request, org_id)
        if error:
            return error

        data       = {**request.data, 'org': org.id}
        serializer = WorkerCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        worker = serializer.save()

        # Open employment history for this worker at this org
        _open_job_history(worker, org, created_by=org)

        # Capture plain_password before clearing it from DB
        plain_pwd = worker.plain_password
        User.objects.filter(pk=worker.pk).update(plain_password=None)

        response_data               = WorkerCreateSerializer(worker).data
        response_data['plain_password'] = plain_pwd  # injected for this response only

        return Response({
            'success': True,
            'message': (
                f'Worker "{worker.full_name}" created. '
                'Save the password below — it will NOT be shown again.'
            ),
            'worker': response_data,
        }, status=status.HTTP_201_CREATED)


class WorkerDetailView(APIView):
    """
    GET    /api/org/<org_id>/workers/<user_id>/  →  read worker details
    PATCH  /api/org/<org_id>/workers/<user_id>/  →  update work_type, full_name, etc.
    DELETE /api/org/<org_id>/workers/<user_id>/  →  remove worker from this org

    DELETE behaviour (no soft-delete / no is_active):
        - User.org is set to None  (worker is detached, not deleted)
        - The open JobHistory record is closed  (left_at = now, is_current = False)
        - The worker account itself is preserved and can be re-hired by any org

    Org-Token required.
    """
    permission_classes = [IsOrgAdmin]

    def _get_worker(self, org_id, user_id, request):
        org = _get_org_from_request(request)
        if not org:
            return None
        try:
            return User.objects.get(
                user_id=user_id,
                role=User.Role.WORKER,
                org=org,
                org__org_id=org_id,
            )
        except User.DoesNotExist:
            return None

    def get(self, request, org_id, user_id):
        worker = self._get_worker(org_id, user_id, request)
        if not worker:
            return Response({'error': 'Worker not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'worker': WorkerListSerializer(worker).data})

    def patch(self, request, org_id, user_id):
        worker = self._get_worker(org_id, user_id, request)
        if not worker:
            return Response({'error': 'Worker not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = WorkerUpdateSerializer(worker, data=request.data, partial=True)
        if serializer.is_valid():
            updated_worker = serializer.save()

            # If work_type changed, update the open JobHistory snapshot too
            if 'work_type' in request.data:
                JobHistory.objects.filter(
                    user=updated_worker,
                    org=updated_worker.org,
                    is_current=True,
                ).update(work_type=updated_worker.work_type or '')

            return Response({
                'success': True,
                'message': f'Worker "{worker.full_name}" updated.',
                'worker':  WorkerListSerializer(updated_worker).data,
            })
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, org_id, user_id):
        worker = self._get_worker(org_id, user_id, request)
        if not worker:
            return Response({'error': 'Worker not found.'}, status=status.HTTP_404_NOT_FOUND)

        org         = _get_org_from_request(request)
        worker_name = worker.full_name

        # 1. Close the employment history record
        _close_job_history(worker, org)

        # 2. Detach the worker from the org (no is_active flag — worker is simply unassigned)
        worker.org = None
        worker.save(update_fields=['org'])

        return Response({
            'success': True,
            'message': (
                f'Worker "{worker_name}" has been removed from {org.name}. '
                'Their account and history are preserved.'
            ),
        }, status=status.HTTP_200_OK)


class WorkerResetPasswordView(APIView):
    """
    POST /api/org/<org_id>/workers/<user_id>/reset-password/

    Org admin generates a new random password for a worker.
    The new plain-text password is returned ONCE — never stored.
    """
    permission_classes = [IsOrgAdminOrEmployee]

    def post(self, request, org_id, user_id):
        try:
            worker = User.objects.get(
                user_id=user_id,
                org=_get_org_from_request(request),
                org__org_id=org_id,
                role=User.Role.WORKER,
            )
        except User.DoesNotExist:
            return Response({'error': 'Worker not found.'}, status=status.HTTP_404_NOT_FOUND)

        from timetable_app.models import generate_worker_password
        new_password = generate_worker_password(length=10)
        worker.set_password(new_password)
        worker.save()

        return Response({
            'success':      True,
            'message':      f'Password reset for "{worker.full_name}". Save it — shown once only.',
            'user_id':      worker.user_id,
            'new_password': new_password,
        })


# ===========================================================================
# AVAILABILITY VIEWS
# ===========================================================================

class AvailabilityView(APIView):
    """
    GET  /api/availability/  →  org admin: all submissions for their org
                                worker (JWT): only their own submissions
    POST /api/availability/  →  worker submits availability (CREATE ONLY)

    Workers cannot PUT / PATCH / DELETE their own submissions.
    Supports optional ?week_start=YYYY-MM-DD query filter.
    end_time is accepted on POST (worker's latest available time for the day).
    """
    permission_classes = [IsWorker]

    def get(self, request):
        if hasattr(request, 'org'):
            # Org-Token: admin sees all workers in their org
            qs = Availability.objects.filter(
                worker__org=request.org
            ).select_related('worker')
        else:
            # JWT Worker: own records only
            qs = Availability.objects.filter(
                worker=request.user
            ).select_related('worker')

        week_start = request.query_params.get('week_start')
        if week_start:
            qs = qs.filter(week_start=week_start)

        serializer = AvailabilitySerializer(qs, many=True)
        return Response({'success': True, 'count': qs.count(), 'availability': serializer.data})

    def post(self, request):
        # Only JWT workers can submit — org-token holders use worker accounts
        if hasattr(request, 'org'):
            return Response(
                {'error': 'Org admin cannot submit availability. Use a worker account.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = AvailabilitySerializer(
            data=request.data,
            context={'request': request},
        )
        if serializer.is_valid():
            availability = serializer.save()
            return Response({
                'success':      True,
                'message':      'Availability submitted.',
                'availability': AvailabilitySerializer(availability).data,
            }, status=status.HTTP_201_CREATED)
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class AvailabilityDetailView(APIView):
    """
    GET    /api/availability/<pk>/  →  view one record (owner worker only)
    PATCH  /api/availability/<pk>/  →  blocked for workers; org admin only
    DELETE /api/availability/<pk>/  →  blocked for workers; org admin only
    """
    permission_classes = [IsAuthenticated, IsOwnerWorkerOrOrgAdmin]

    def _get_object(self, pk, user):
        try:
            obj = Availability.objects.select_related('worker').get(pk=pk)
            if obj.worker != user:
                return None
            return obj
        except Availability.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get_object(pk, request.user)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'availability': AvailabilitySerializer(obj).data})

    def patch(self, request, pk):
        return Response(
            {'error': 'Workers cannot modify availability records.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    def delete(self, request, pk):
        return Response(
            {'error': 'Workers cannot delete availability records.'},
            status=status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TIMETABLE VIEWS
# ===========================================================================

class TimetableListView(APIView):
    """
    GET /api/timetable/

    Org-Token →  all timetables (DRAFT + PUBLISHED)
    JWT Worker → PUBLISHED timetables for their org only
    """
    permission_classes = [IsOrgAdminOrReadOnly]

    def get(self, request):
        if hasattr(request, 'org'):
            qs = Timetable.objects.filter(org=request.org).prefetch_related('shifts')
        else:
            qs = Timetable.objects.filter(
                org=request.user.org,
                status=Timetable.Status.PUBLISHED,
            ).prefetch_related('shifts')

        return Response({
            'success':    True,
            'timetables': TimetableSerializer(qs, many=True).data,
        })


class TimetableDetailView(APIView):
    """
    GET /api/timetable/<pk>/

    Org-Token →  any timetable status
    JWT Worker → PUBLISHED only
    """
    permission_classes = [IsOrgAdminOrReadOnly]

    def get(self, request, pk):
        try:
            timetable = Timetable.objects.prefetch_related('shifts__worker').get(
                pk=pk, org=_get_org_from_request(request)
            )
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not hasattr(request, 'org') and timetable.status != Timetable.Status.PUBLISHED:
            return Response(
                {'error': 'Timetable not yet published.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response({'success': True, 'timetable': TimetableSerializer(timetable).data})


class TimetableGenerateView(APIView):
    """
    POST /api/timetable/generate/
    Org-Token required.

    Body:
        {
            "week_start"  : "YYYY-MM-DD",   ← must be a Monday
            "regenerate"  : false            ← optional, default false
        }

    Scheduler constraints:
        - Respects per-worker weekly hour limits (WorkTypeLimit)
        - Respects org shop_open / shop_close
        - Max 8 hours per individual shift
        - Skips availability windows shorter than 30 minutes
    """
    permission_classes = [IsOrgAdmin]

    def post(self, request):
        import datetime
        from timetable_app.scheduler import generate_timetable

        org = _get_org_from_request(request)
        if not org:
            return Response(
                {'error': 'No organisation assigned to your account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        week_start_str = request.data.get('week_start')
        regenerate     = request.data.get('regenerate', False)

        if not week_start_str:
            return Response(
                {'error': 'week_start is required (YYYY-MM-DD, must be a Monday).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            week_start = datetime.date.fromisoformat(week_start_str)
        except ValueError:
            return Response(
                {'error': f'Invalid date format: {week_start_str!r}. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = generate_timetable(org=org, week_start=week_start, regenerate=regenerate)
        if result.errors:
            return Response({'success': False, 'errors': result.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success':   True,
            'message':   (
                f'Timetable generated for week {week_start}. '
                f'{len(result.shifts)} shift(s) scheduled.'
            ),
            'timetable': TimetableSerializer(result.timetable).data,
            'summary':   result.summary,
            'warnings':  result.warnings,
        }, status=status.HTTP_201_CREATED)


class TimetablePublishView(APIView):
    """
    POST /api/timetable/<pk>/publish/
    Org-Token required.

    Moves a DRAFT timetable to PUBLISHED, making it visible to workers.
    Idempotent — safe to call on an already-published timetable.
    """
    permission_classes = [IsOrgAdmin]

    def post(self, request, pk):
        try:
            timetable = Timetable.objects.get(pk=pk, org=_get_org_from_request(request))
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

        if timetable.status == Timetable.Status.PUBLISHED:
            return Response({
                'success':   True,
                'message':   'Timetable is already published.',
                'timetable': TimetableSerializer(timetable).data,
            })

        timetable.status = Timetable.Status.PUBLISHED
        timetable.save(update_fields=['status'])
        return Response({
            'success':   True,
            'message':   f'Timetable for week {timetable.week_start} is now PUBLISHED.',
            'timetable': TimetableSerializer(timetable).data,
        })


class TimetableShiftEditView(APIView):
    """
    PATCH /api/timetable/<pk>/shifts/<shift_pk>/
    Org-Token required.

    Manually adjust a shift's start / end time.

    Validates:
        - start_time >= org.shop_open
        - end_time   <= org.shop_close
        - end_time   >  start_time
        - duration   <= 8 hours
        - worker's weekly total stays within their hour budget
    """
    permission_classes = [IsOrgAdmin]

    def patch(self, request, pk, shift_pk):
        import datetime

        try:
            timetable = Timetable.objects.get(pk=pk, org=_get_org_from_request(request))
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            shift = Shift.objects.select_related('worker').get(pk=shift_pk, timetable=timetable)
        except Shift.DoesNotExist:
            return Response({'error': 'Shift not found.'}, status=status.HTTP_404_NOT_FOUND)

        org = _get_org_from_request(request)

        def parse_time(val):
            if not val:
                return None
            try:
                return datetime.time.fromisoformat(val)
            except ValueError:
                return None

        start_t = parse_time(request.data.get('start_time')) or shift.start_time
        end_t   = parse_time(request.data.get('end_time'))   or shift.end_time

        errors = []
        if start_t >= end_t:
            errors.append('start_time must be before end_time.')
        if start_t < org.shop_open:
            errors.append(f'start_time {start_t} is before shop open {org.shop_open}.')
        if end_t > org.shop_close:
            errors.append(f'end_time {end_t} is after shop close {org.shop_close}.')

        duration_h = (
            datetime.datetime.combine(datetime.date.today(), end_t) -
            datetime.datetime.combine(datetime.date.today(), start_t)
        ).seconds / 3600

        if duration_h > 8:
            errors.append(f'Shift duration {duration_h:.1f} h exceeds 8-hour maximum.')

        other_hours = sum(
            float(h) for h in
            Shift.objects.filter(timetable=timetable, worker=shift.worker)
            .exclude(pk=shift.pk)
            .values_list('hours', flat=True)
        )
        budget = shift.worker.get_weekly_hour_limit()
        if other_hours + duration_h > budget:
            errors.append(
                f'Edit would bring {shift.worker.full_name} to '
                f'{other_hours + duration_h:.1f} h, exceeding their '
                f'{budget} h weekly budget.'
            )

        if errors:
            return Response({'success': False, 'errors': errors},
                            status=status.HTTP_400_BAD_REQUEST)

        shift.start_time = start_t
        shift.end_time   = end_t
        shift.hours      = round(duration_h, 2)
        shift.save()
        return Response({'success': True, 'message': 'Shift updated.', 'shift': ShiftSerializer(shift).data})


class TimetableShiftDeleteView(APIView):
    """
    DELETE /api/timetable/<pk>/shifts/<shift_pk>/
    Org-Token required. Removes a single shift from a timetable.
    """
    permission_classes = [IsOrgAdmin]

    def delete(self, request, pk, shift_pk):
        try:
            timetable = Timetable.objects.get(pk=pk, org=_get_org_from_request(request))
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            shift = Shift.objects.get(pk=shift_pk, timetable=timetable)
        except Shift.DoesNotExist:
            return Response({'error': 'Shift not found.'}, status=status.HTTP_404_NOT_FOUND)

        worker_name = shift.worker.full_name
        day         = shift.get_day_display()
        shift.delete()
        return Response({
            'success': True,
            'message': f'Shift for {worker_name} on {day} removed.',
        })


class TimetableWorkerView(APIView):
    """
    GET /api/timetable/<pk>/worker/

    Returns shifts for the currently logged-in worker only.
    Workers see PUBLISHED timetables only.
    Org admin can pass ?worker_pk=<pk> to filter by a specific worker.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            timetable = Timetable.objects.prefetch_related('shifts__worker').get(
                pk=pk, org=request.user.org
            )
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.is_worker and timetable.status != Timetable.Status.PUBLISHED:
            return Response({'error': 'Timetable not yet published.'},
                            status=status.HTTP_403_FORBIDDEN)

        if request.user.is_worker:
            shifts = timetable.shifts.filter(worker=request.user)
        else:
            worker_pk = request.query_params.get('worker_pk')
            shifts    = timetable.shifts.filter(worker_id=worker_pk) if worker_pk else timetable.shifts.all()

        shift_data  = ShiftSerializer(shifts, many=True).data
        total_hours = round(sum(float(s['hours']) for s in shift_data), 2)

        return Response({
            'success':      True,
            'timetable_id': timetable.pk,
            'week_start':   timetable.week_start,
            'week_end':     timetable.week_end,
            'status':       timetable.status,
            'shifts':       shift_data,
            'total_hours':  total_hours,
        })


class TimetablePDFView(APIView):
    """
    GET /api/timetable/<pk>/pdf/
    Streams the timetable as a downloadable PDF.
    Workers: PUBLISHED only. Org admin: any status.
    """
    permission_classes = [IsOrgAdminOrReadOnly]

    def get(self, request, pk):
        from django.http import HttpResponse
        from timetable_app.pdf_export import generate_pdf_bytes

        try:
            timetable = Timetable.objects.prefetch_related('shifts__worker').get(
                pk=pk, org=_get_org_from_request(request)
            )
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not hasattr(request, 'org') and timetable.status != Timetable.Status.PUBLISHED:
            return Response({'error': 'Timetable not yet published.'},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            pdf_bytes = generate_pdf_bytes(timetable)
        except Exception as e:
            return Response({'error': f'PDF generation failed: {e}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        filename = (
            f'timetable_{timetable.org.name.replace(" ", "_")}'
            f'_week_{timetable.week_start}.pdf'
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class TimetableHTMLView(APIView):
    """
    GET /api/timetable/<pk>/html/
    Returns the timetable as a rendered HTML string for the AngularJS frontend.
    Workers: PUBLISHED only.
    """
    from rest_framework.renderers import StaticHTMLRenderer
    from rest_framework.response import Response

    permission_classes = [IsOrgAdminOrReadOnly]
    renderer_classes = [StaticHTMLRenderer]

    def get(self, request, pk):
        from django.http import HttpResponse
        from timetable_app.pdf_export import build_timetable_html

        try:
            timetable = Timetable.objects.prefetch_related('shifts__worker').get(
                pk=pk, 
                org=_get_org_from_request(request)
            )
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

        if (
            request.user.is_authenticated
            and hasattr(request.user, "is_worker")
            and request.user.is_worker
            and timetable.status != Timetable.Status.PUBLISHED
        ):
            return Response(
                {"error": "Timetable not yet published."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        html = build_timetable_html(timetable)

        return Response(html)

# ===========================================================================
# ORGANISATION — REGISTRATION, LOGIN, EMPLOYEE MANAGEMENT
# ===========================================================================

class OrgPublicView(APIView):
    """
    GET /api/org/<org_id>/public/   (no auth)
    Returns safe public info: name, shop hours, org_id.
    Used by login and join pages for org context display.
    """
    permission_classes = [AllowAny]

    def get(self, request, org_id):
        org = _get_org_or_404(org_id)
        if not org:
            return Response({'error': 'Organisation not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'success': True,
            'org': {
                'org_id':     org.org_id,
                'name':       org.name,
                'shop_open':  str(org.shop_open)[:5],
                'shop_close': str(org.shop_close)[:5],
            },
        })


class OrgJoinInfoView(APIView):
    """
    GET /api/org/<org_id>/join/   (no auth)

    Returns org info + all users (name, user_id, role) for the name-picker
    on the worker login screen.
    """
    permission_classes = [AllowAny]

    def get(self, request, org_id):
        org = _get_org_or_404(org_id)
        if not org:
            return Response({'error': 'Organisation not found.'}, status=status.HTTP_404_NOT_FOUND)

        users = (
            User.objects
            .filter(org=org)
            .order_by('full_name')
            .values('user_id', 'full_name', 'role')
        )
        return Response({
            'success': True,
            'org': {
                'org_id':     org.org_id,
                'name':       org.name,
                'shop_open':  str(org.shop_open)[:5],
                'shop_close': str(org.shop_close)[:5],
            },
            'users': list(users),
        })


class OrgRegisterView(APIView):
    """
    POST /api/org/register/   (no auth)

    Registers a new organisation. Returns:
        - org_id, login_url, join_url
        - Organisation detail
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from timetable_app.serializers import OrgRegisterSerializer, OrgDetailSerializer
        serializer = OrgRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        org  = serializer.save()
        host = request.build_absolute_uri('/').rstrip('/')
        return Response({
            'success':      True,
            'message':      f'Organisation "{org.name}" registered. Your org ID is {org.org_id}.',
            'organisation': OrgDetailSerializer(org, context={'request': request}).data,
            'org_id':       org.org_id,
            'login_url':    f'{host}/#/org/{org.org_id}/login',
            'join_url':     f'{host}/#/org/{org.org_id}/join',
        }, status=status.HTTP_201_CREATED)


class OrgLoginView(APIView):
    """
    POST /api/org/<org_id>/login/   (no auth)

    Body: { "identifier": "<email or org_id>", "password": "..." }

    The org_id in the URL scopes the UI route. If provided (not 'login'),
    it is validated against the credential match for security.
    Returns an Org-Token valid for 24 hours.
    """
    permission_classes = [AllowAny]

    def post(self, request, org_id):
        from timetable_app.serializers import OrgLoginSerializer, OrgDetailSerializer
        from timetable_app.models import OrgToken

        serializer = OrgLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        org = serializer.validated_data['org']

        if org_id and org_id != 'login' and org.org_id != org_id:
            return Response(
                {'success': False, 'errors': ['The credentials do not belong to this organisation.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        OrgToken.objects.filter(org=org).delete()
        token = OrgToken.create_for_org(org)
        return Response({
            'success':      True,
            'message':      f'Welcome, {org.name}!',
            'org_token':    token.token,
            'expires_at':   token.expires_at,
            'organisation': OrgDetailSerializer(org, context={'request': request}).data,
        })


class OrgLoginGlobalView(APIView):
    """
    POST /api/org/login/   (no org_id in URL)

    Same as OrgLoginView but used from the home/global login page.
    Returns org_id so the frontend can redirect to the correct org URL.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from timetable_app.serializers import OrgLoginSerializer, OrgDetailSerializer
        from timetable_app.models import OrgToken

        serializer = OrgLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        org = serializer.validated_data['org']
        OrgToken.objects.filter(org=org).delete()
        token = OrgToken.create_for_org(org)
        return Response({
            'success':      True,
            'message':      f'Welcome, {org.name}!',
            'org_token':    token.token,
            'expires_at':   token.expires_at,
            'organisation': OrgDetailSerializer(org, context={'request': request}).data,
        })


class OrgLogoutView(APIView):
    """POST /api/org/<org_id>/logout/  — deletes the Org-Token."""
    permission_classes = [AllowAny]

    def post(self, request, org_id):
        from timetable_app.models import OrgToken
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if auth.startswith('Org-Token '):
            OrgToken.objects.filter(token=auth.split(' ', 1)[1].strip()).delete()
        return Response({'success': True, 'message': 'Logged out.'})


class OrgMeView(APIView):
    """GET /api/org/<org_id>/me/  — Org-Token required."""
    permission_classes = [IsOrgAdmin]

    def get(self, request, org_id):
        from timetable_app.serializers import OrgDetailSerializer
        org = request.org
        if org.org_id != org_id:
            return Response(
                {'error': 'Token does not match this organisation.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        workers = User.objects.filter(org=org)
        return Response({
            'success':      True,
            'organisation': OrgDetailSerializer(org, context={'request': request}).data,
            'workers':      WorkerListSerializer(workers, many=True).data,
        })


class OrgListView(APIView):
    """GET /api/org/list/  — public, no auth. Returns org_id + name."""
    permission_classes = [AllowAny]

    def get(self, request):
        orgs = Organisation.objects.values('org_id', 'name')
        return Response({'success': True, 'organisations': list(orgs)})


# ===========================================================================
# ADD USER (with full details + JobHistory)
# ===========================================================================

class AddUserView(APIView):
    """
    POST /api/org/<org_id>/add-user/
    Org-Token required.

    Creates a User with full personal details and assigns them to the org.
    Opens a JobHistory record for this employment.
    Returns plain_password ONCE if a new password was generated.
    """
    permission_classes = [IsOrgAdmin]

    def post(self, request, org_id):
        from timetable_app.serializers import AddUserSerializer
        org = request.org
        if org.org_id != org_id:
            return Response({'error': 'Token mismatch.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = AddUserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, plain_pwd = serializer.save(org=org)

        # Open employment history
        _open_job_history(user, org, created_by=org)

        response_data = {
            'success': True,
            'message': f'User "{user.full_name}" added to {org.name}.',
            'user': {
                'id':        user.pk,
                'user_id':   user.user_id,
                'full_name': user.full_name,
                'email':     user.email,
                'phone':     user.phone,
                'role':      user.role,
                'work_type': user.work_type,
            },
        }
        if plain_pwd:
            response_data['plain_password'] = plain_pwd
            response_data['message'] += ' Save the password — shown once only.'
            User.objects.filter(pk=user.pk).update(plain_password=None)

        return Response(response_data, status=status.HTTP_201_CREATED)


# ===========================================================================
# GLOBAL USER SEARCH
# ===========================================================================

class GlobalUserSearchView(APIView):
    """
    GET /api/org/<org_id>/global-users/?q=<email_or_phone>
    Org-Token required. Exact match only — no partial / fuzzy search.

    Used by org admin to find an existing user by email or mobile number
    before adding them to the org (avoids duplicate account creation).
    """
    permission_classes = [IsOrgAdmin]

    def get(self, request, org_id):
        from timetable_app.serializers import GlobalUserSearchSerializer
        org = request.org
        if org.org_id != org_id:
            return Response({'error': 'Token mismatch.'}, status=status.HTTP_403_FORBIDDEN)

        q      = (request.query_params.get('q') or '').strip()
        digits = ''.join(c for c in q if c.isdigit())

        if not q:
            return Response({
                'success': True, 'user': None,
                'message': 'Enter a complete email or mobile number.',
            })

        user = None
        if '@' in q:
            user = User.objects.filter(email__iexact=q).first()
        elif digits:
            user = User.objects.filter(phone=digits).first()

        if not user:
            return Response({
                'success': True, 'user': None,
                'message': 'No user found with that email or mobile number.',
            })

        return Response({'success': True, 'user': GlobalUserSearchSerializer(user).data})


# ===========================================================================
# EMAIL CONFLICT DETECTION
# ===========================================================================

class EmailConflictView(APIView):
    """
    GET /api/org/<org_id>/email-conflicts/
    Org-Token required.

    Returns workers whose email address is also registered as an
    Organisation admin email — a conflict that could cause auth confusion.
    """
    permission_classes = [IsOrgAdmin]

    def get(self, request, org_id):
        org = request.org
        if org.org_id != org_id:
            return Response({'error': 'Token mismatch.'}, status=status.HTTP_403_FORBIDDEN)

        org_emails = {
            e.lower()
            for e in Organisation.objects.values_list('email', flat=True)
            if e
        }

        conflicts = []
        for worker in User.objects.filter(org=org, email__isnull=False).exclude(email=''):
            if worker.email and worker.email.lower() in org_emails:
                conflicts.append({
                    'user_id':   worker.user_id,
                    'full_name': worker.full_name,
                    'email':     worker.email,
                    'message':   (
                        f'Worker {worker.full_name} ({worker.user_id}) uses an email '
                        'already assigned to an Organisation account. '
                        "Please update the worker's email address."
                    ),
                })

        return Response({
            'success':   True,
            'conflicts': conflicts,
            'count':     len(conflicts),
        })
    
class WorkerJobHistoryView(APIView):
    """
    GET /api/org/<org_id>/workers/<user_id>/history/
    Org-Token required. Returns full job history for a worker.
    """
    permission_classes = [IsOrgAdmin]

    def get(self, request, org_id, user_id):
        org = request.org
        if org.org_id != org_id:
            return Response({'error': 'Token mismatch.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            worker = User.objects.get(user_id=user_id, org=org)
        except User.DoesNotExist:
            return Response({'error': 'Worker not found.'}, status=status.HTTP_404_NOT_FOUND)

        history = JobHistory.objects.filter(user=worker).order_by('-joined_at')

        data = []
        for h in history:
            data.append({
                'org_name':   h.org.name,
                'work_type':  h.work_type,
                'joined_at':  h.joined_at.strftime('%Y-%m-%d %H:%M'),
                'left_at':    h.left_at.strftime('%Y-%m-%d %H:%M') if h.left_at else None,
                'is_current': h.is_current,
            })

        return Response({'success': True, 'history': data})