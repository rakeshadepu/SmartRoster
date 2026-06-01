"""
views.py — Timetable Planner

API Views:
  Auth:         LoginView, LogoutView, RefreshView, MeView (JWT — workers only)
  Organisation: OrganisationView (GET + PATCH, Org-Token only)
  WorkLimits:   WorkTypeLimitView (GET + PATCH, Org-Token only)
  Workers:      WorkerListCreateView, WorkerDetailView (Org-Token only)
  Workers(pub): WorkerPublicListView (unauthenticated — for login screen)
  Availability: AvailabilityView (POST/GET for workers via JWT; GET all via Org-Token)
  Timetable:    TimetableListView, TimetableDetailView, Generate, Publish, PDF, HTML
"""

from django.contrib.auth import logout
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from timetable_app.models import Organisation, WorkTypeLimit, User, Availability, Timetable, Shift
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
    IsWorker,
    IsOrgAdminOrWorker,
    IsOrgAdminOrEmployee,
    IsOrgAdminOrReadOnly,
)


def _get_tokens(user):
    """Helper: generate JWT access + refresh tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
    }


def _get_org_from_request(request):
    """Return the Organisation for the current request.

    Works for both authentication paths:
    - Org-Token: IsOrgAdminOrWorker sets request.org
    - JWT Worker: user.org
    """
    if hasattr(request, 'org') and request.org:
        return request.org
    if request.user and request.user.is_authenticated:
        return request.user.org
    return None


# ===========================================================================
# AUTH VIEWS
# ===========================================================================

class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: { "user_id": "...", "password": "..." }

    Worker login flow:
      1. GET /api/workers/public/ → list of names + user_ids (no auth required)
      2. Worker selects their name → user_id is auto-filled
      3. Worker types their password → POST here

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

        user   = serializer.validated_data['user']
        tokens = _get_tokens(user)
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
    Blacklists the refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except TokenError:
            pass  # already invalid — that's fine
        except Exception:
            pass

        logout(request)
        return Response({'success': True, 'message': 'Logged out successfully.'},
                        status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
    """
    POST /api/auth/refresh/
    Body: { "refresh": "<refresh_token>" }
    Returns a new access token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'refresh token required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            token  = RefreshToken(refresh_token)
            return Response({
                'access':  str(token.access_token),
                'refresh': str(token),
            })
        except TokenError as e:
            return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class MeView(APIView):
    """
    GET /api/auth/me/
    Returns the logged-in user's profile (works for both roles).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return Response({'success': True, 'user': serializer.data})


# ===========================================================================
# ORGANISATION VIEWS
# ===========================================================================

class OrganisationView(APIView):
    """
    GET  /api/org/<org_id>/settings/  → Org admin / Employee sees their organisation's details
    PATCH /api/org/<org_id>/settings/ → Org admin / Employee updates shop open/close times
    org_id URL kwarg is used to verify the token belongs to this org.
    """
    permission_classes = [IsOrgAdminOrEmployee]

    def _get_org(self, request, org_id):
        org = _get_org_from_request(request)
        if not org:
            return None, Response({'error': 'No organisation assigned to your account.'},
                                  status=status.HTTP_404_NOT_FOUND)
        if org.org_id != org_id:
            return None, Response({'error': 'Organisation mismatch.'},
                                  status=status.HTTP_403_FORBIDDEN)
        return org, None

    def get(self, request, org_id):
        org, err = self._get_org(request, org_id)
        if err:
            return err
        serializer = OrganisationSerializer(org)
        return Response({'success': True, 'organisation': serializer.data})

    def patch(self, request, org_id):
        org, err = self._get_org(request, org_id)
        if err:
            return err
        serializer = OrganisationUpdateSerializer(org, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Organisation settings updated.',
                'organisation': OrganisationSerializer(org).data,
            })
        return Response({'success': False, 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)


# ===========================================================================
# WORK TYPE LIMIT VIEWS
# ===========================================================================

class WorkTypeLimitListView(APIView):
    """
    GET  /api/work-limits/  → list all hour limits for this org
    POST /api/work-limits/  → create/override a limit for a work type
    """
    permission_classes = [IsOrgAdminOrEmployee]

    def get(self, request):
        org = request.user.org
        if not org:
            return Response({'error': 'No organisation assigned.'},
                            status=status.HTTP_404_NOT_FOUND)
        limits = WorkTypeLimit.objects.filter(org=org)
        serializer = WorkTypeLimitSerializer(limits, many=True)
        return Response({'success': True, 'limits': serializer.data})

    def post(self, request):
        org = request.user.org
        data = {**request.data, 'org': org.id}
        # Upsert: update if exists, create if not
        work_type = data.get('work_type')
        instance = WorkTypeLimit.objects.filter(org=org, work_type=work_type).first()
        serializer = WorkTypeLimitSerializer(instance, data=data) if instance \
                     else WorkTypeLimitSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': f'{work_type} limit saved.',
                'limit': serializer.data,
            }, status=status.HTTP_200_OK)
        return Response({'success': False, 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)


# ===========================================================================
# WORKER VIEWS (Employee-managed)
# ===========================================================================

class WorkerPublicListView(APIView):
    """
    GET /api/org/<org_id>/workers/public/

    Unauthenticated endpoint used on the JOIN/LOGIN SCREEN.
    Returns worker names + user_ids only (no sensitive data).
    The worker selects their name → user_id is auto-filled → they type password.
    """
    permission_classes = [AllowAny]

    def get(self, request, org_id=None):
        qs = User.objects.filter(role=User.Role.WORKER, is_active=True)
        if org_id:
            qs = qs.filter(org__org_id=org_id)
        serializer = WorkerPublicSerializer(qs, many=True)
        return Response({'success': True, 'workers': serializer.data})


class WorkerListCreateView(APIView):
    """
    GET  /api/org/<org_id>/workers/  → Employee lists all workers in the org
    POST /api/org/<org_id>/workers/  → Employee creates a new worker

    On POST success, the response includes `plain_password` ONCE.
    The employee must copy this and hand it to the worker.
    After this response, plain_password is cleared from the DB.
    """
    permission_classes = [IsOrgAdminOrEmployee]

    def get(self, request, org_id):
        org = request.user.org
        # Verify the URL org_id matches the authenticated employee's org
        if not org or org.org_id != org_id:
            return Response({'error': 'Organisation mismatch or not found.'},
                            status=status.HTTP_403_FORBIDDEN)

        qs = User.objects.filter(org=org, role=User.Role.WORKER)

        # Optional filters
        work_type = request.query_params.get('work_type')
        is_active = request.query_params.get('is_active')
        if work_type:
            qs = qs.filter(work_type=work_type)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')

        serializer = WorkerListSerializer(qs, many=True)
        return Response({
            'success': True,
            'count':   qs.count(),
            'workers': serializer.data,
        })

    def post(self, request, org_id):
        org = request.user.org
        if not org or org.org_id != org_id:
            return Response({'error': 'Organisation mismatch or not found.'},
                            status=status.HTTP_403_FORBIDDEN)

        data = {**request.data, 'org': org.id}
        serializer = WorkerCreateSerializer(data=data)

        if serializer.is_valid():
            worker = serializer.save()

            # Capture plain_password BEFORE clearing it
            plain_pwd = worker.plain_password

            # Clear plain_password from DB after reading
            User.objects.filter(pk=worker.pk).update(plain_password=None)

            response_data = WorkerCreateSerializer(worker).data
            response_data['plain_password'] = plain_pwd  # inject for this response only

            return Response({
                'success':  True,
                'message':  (
                    f'Worker "{worker.full_name}" created. '
                    f'Save the password below — it will NOT be shown again.'
                ),
                'worker':   response_data,
            }, status=status.HTTP_201_CREATED)

        return Response({'success': False, 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)


class WorkerDetailView(APIView):
    """
    GET    /api/org/<org_id>/<user_id>/  → get worker details
    PATCH  /api/org/<org_id>/<user_id>/  → update worker (work_type, is_active, full_name)
    DELETE /api/org/<org_id>/<user_id>/  → deactivate (soft delete) worker
    """
    permission_classes = [IsOrgAdminOrEmployee]

    def _get_worker(self, org_id, user_id, employee):
        try:
            return User.objects.get(
                user_id=user_id,
                role=User.Role.WORKER,
                org=employee.org,
                org__org_id=org_id,
            )
        except User.DoesNotExist:
            return None

    def get(self, request, org_id, user_id):
        worker = self._get_worker(org_id, user_id, request)
        if not worker:
            return Response({'error': 'Worker not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = WorkerListSerializer(worker)
        return Response({'success': True, 'worker': serializer.data})

    def patch(self, request, org_id, user_id):
        worker = self._get_worker(org_id, user_id, request)
        if not worker:
            return Response({'error': 'Worker not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = WorkerUpdateSerializer(worker, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': f'Worker "{worker.full_name}" updated.',
                'worker':  WorkerListSerializer(worker).data,
            })
        return Response({'success': False, 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, org_id, user_id):
        worker = self._get_worker(org_id, user_id, request)
        if not worker:
            return Response({'error': 'Worker not found.'}, status=status.HTTP_404_NOT_FOUND)

        worker.is_active = False
        worker.save(update_fields=['is_active'])
        return Response({
            'success': True,
            'message': f'Worker "{worker.full_name}" has been deactivated.',
        }, status=status.HTTP_200_OK)


class WorkerResetPasswordView(APIView):
    """
    POST /api/org/<org_id>/<user_id>/reset-password/

    Employee can reset a worker's password.
    A new random password is generated and returned ONCE.
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
    GET  /api/availability/  → Org admin sees ALL submissions for their org
                               Worker (JWT) sees only their OWN submissions
    POST /api/availability/  → Worker submits availability (CREATE ONLY)

    Workers CANNOT PUT/PATCH/DELETE their submissions.
    """
    permission_classes = [IsWorker]

    def get(self, request):
        if hasattr(request, 'org'):
            # Org-Token: admin sees all workers in their org
            org = request.org
            qs = Availability.objects.filter(
                worker__org=org
            ).select_related('worker')
        else:
            # JWT Worker: sees only their own records
            qs = Availability.objects.filter(
                worker=request.user
            ).select_related('worker')

        # Optional filter by week_start
        week_start = request.query_params.get('week_start')
        if week_start:
            qs = qs.filter(week_start=week_start)

        serializer = AvailabilitySerializer(qs, many=True)
        return Response({'success': True, 'count': qs.count(), 'availability': serializer.data})

    def post(self, request):
        # Only JWT-authenticated workers can submit availability (not org-token)
        if hasattr(request, 'org'):
            return Response(
                {'error': 'Org admin cannot submit availability directly. Use the worker accounts.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = AvailabilitySerializer(
            data=request.data,
            context={'request': request},
        )
        if serializer.is_valid():
            availability = serializer.save()
            return Response({
                'success': True,
                'message': 'Availability submitted.',
                'availability': AvailabilitySerializer(availability).data,
            }, status=status.HTTP_201_CREATED)
        return Response({'success': False, 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)


class AvailabilityDetailView(APIView):
    """
    GET    /api/availability/<pk>/  → view one record
    PATCH  /api/availability/<pk>/  → employee only: modify a record
    DELETE /api/availability/<pk>/  → employee only: remove a record
    """
    permission_classes = [IsAuthenticated, IsOwnerWorkerOrOrgAdmin]

    def _get_object(self, pk, user):
        try:
            obj = Availability.objects.select_related('worker').get(pk=pk)
            # Workers can only access their own availability
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
        # Workers can only view their own availability, not modify it.
        return Response(
            {'error': 'Workers cannot modify availability records.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    def delete(self, request, pk):
        # Workers cannot delete availability records.
        return Response(
            {'error': 'Workers cannot delete availability records.'},
            status=status.HTTP_403_FORBIDDEN,
        )
        obj = self._get_object(pk, request.user)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response({'success': True, 'message': 'Availability record deleted.'})


# ===========================================================================
# TIMETABLE VIEWS (stubbed — Phase 2 will complete these)
# ===========================================================================

class TimetableListView(APIView):
    """
    GET  /api/timetable/           → list timetables (both roles)
    POST /api/timetable/generate/  → generate timetable (employee only) — Phase 2
    """
    permission_classes = [IsOrgAdminOrReadOnly]

    def get(self, request):
        if hasattr(request, 'org'):
            # Org-Token: see all timetables (draft + published)
            qs = Timetable.objects.filter(org=request.org).prefetch_related('shifts')
        else:
            # JWT Worker: only see PUBLISHED timetables for their org
            qs = Timetable.objects.filter(
                org=request.user.org,
                status=Timetable.Status.PUBLISHED,
            ).prefetch_related('shifts')

        serializer = TimetableSerializer(qs, many=True)
        return Response({'success': True, 'timetables': serializer.data})


class TimetableDetailView(APIView):
    """
    GET   /api/timetable/<pk>/  → view timetable (both roles)
    PATCH /api/timetable/<pk>/  → employee edits (Phase 2)
    """
    permission_classes = [IsOrgAdminOrReadOnly]

    def get(self, request, pk):
        try:
            timetable = Timetable.objects.prefetch_related('shifts__worker').get(
                pk=pk, org=_get_org_from_request(request)
            )
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

        # JWT workers can only view PUBLISHED timetables
        if not hasattr(request, 'org') and timetable.status != Timetable.Status.PUBLISHED:
            return Response({'error': 'Timetable not yet published.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = TimetableSerializer(timetable)
        return Response({'success': True, 'timetable': serializer.data})


# ===========================================================================
# PHASE 2 — TIMETABLE GENERATION, EDITING, PUBLISHING, PDF EXPORT
# ===========================================================================

class TimetableGenerateView(APIView):
    """
    POST /api/timetable/generate/

    Employee triggers timetable generation for a given week.

    Body:
      {
        "week_start"  : "YYYY-MM-DD",    ← must be a Monday
        "regenerate"  : false            ← optional, default false
      }

    The scheduler:
      1. Loads all worker availability for that week
      2. Respects per-worker weekly hour limits (from work_type)
      3. Respects shop open/close times
      4. Caps individual shifts at 8 hours
      5. Skips shifts shorter than 30 minutes

    Returns the generated timetable with all shifts and a summary.
    """
    permission_classes = [IsOrgAdminOrEmployee]

    def post(self, request):
        from timetable_app.scheduler import generate_timetable
        import datetime

        org = _get_org_from_request(request)
        if not org:
            return Response({'error': 'No organisation assigned to your account.'},
                            status=status.HTTP_400_BAD_REQUEST)

        week_start_str = request.data.get('week_start')
        regenerate     = request.data.get('regenerate', False)

        if not week_start_str:
            return Response({'error': 'week_start is required (YYYY-MM-DD, must be a Monday).'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            week_start = datetime.date.fromisoformat(week_start_str)
        except ValueError:
            return Response({'error': f'Invalid date format: {week_start_str!r}. Use YYYY-MM-DD.'},
                            status=status.HTTP_400_BAD_REQUEST)

        result = generate_timetable(org=org, week_start=week_start, regenerate=regenerate)

        if result.errors:
            return Response({'success': False, 'errors': result.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = TimetableSerializer(result.timetable)
        return Response({
            'success'  : True,
            'message'  : (
                f'Timetable generated for week {week_start}. '
                f'{len(result.shifts)} shift(s) scheduled.'
            ),
            'timetable': serializer.data,
            'summary'  : result.summary,
            'warnings' : result.warnings,
        }, status=status.HTTP_201_CREATED)


class TimetablePublishView(APIView):
    """
    POST /api/timetable/<pk>/publish/

    Employee publishes a DRAFT timetable, making it visible to workers.
    Cannot un-publish — contact admin to revert.
    """
    permission_classes = [IsOrgAdminOrEmployee]

    def post(self, request, pk):
        try:
            timetable = Timetable.objects.get(pk=pk, org=_get_org_from_request(request))
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

        if timetable.status == Timetable.Status.PUBLISHED:
            return Response({'success': True,
                             'message': 'Timetable is already published.',
                             'timetable': TimetableSerializer(timetable).data})

        timetable.status = Timetable.Status.PUBLISHED
        timetable.save(update_fields=['status'])

        return Response({
            'success'  : True,
            'message'  : f'Timetable for week {timetable.week_start} is now PUBLISHED.',
            'timetable': TimetableSerializer(timetable).data,
        })


class TimetableShiftEditView(APIView):
    """
    PATCH /api/timetable/<pk>/shifts/<shift_pk>/

    Employee can manually adjust an individual shift's start/end time.
    Validates:
      - start_time >= shop_open
      - end_time   <= shop_close
      - end_time   >  start_time
      - shift duration <= 8 hours
      - worker weekly total still within budget after edit
    """
    permission_classes = [IsOrgAdminOrEmployee]

    def patch(self, request, pk, shift_pk):
        import datetime

        try:
            timetable = Timetable.objects.get(pk=pk, org=_get_org_from_request(request))
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            shift = Shift.objects.select_related('worker').get(
                pk=shift_pk, timetable=timetable
            )
        except Shift.DoesNotExist:
            return Response({'error': 'Shift not found.'}, status=status.HTTP_404_NOT_FOUND)

        org = _get_org_from_request(request)

        # Parse incoming times
        def parse_time(val):
            if not val:
                return None
            try:
                return datetime.time.fromisoformat(val)
            except ValueError:
                return None

        new_start = parse_time(request.data.get('start_time'))
        new_end   = parse_time(request.data.get('end_time'))

        start_t = new_start or shift.start_time
        end_t   = new_end   or shift.end_time

        errors = []

        if start_t >= end_t:
            errors.append('start_time must be before end_time.')
        if start_t < org.shop_open:
            errors.append(f'start_time {start_t} is before shop open {org.shop_open}.')
        if end_t > org.shop_close:
            errors.append(f'end_time {end_t} is after shop close {org.shop_close}.')

        duration_h = (
            (datetime.datetime.combine(datetime.date.today(), end_t) -
             datetime.datetime.combine(datetime.date.today(), start_t)).seconds / 3600
        )
        if duration_h > 8:
            errors.append(f'Shift duration {duration_h:.1f}h exceeds 8-hour maximum.')

        # Check weekly budget
        old_hours   = float(shift.hours)
        budget      = shift.worker.get_weekly_hour_limit()
        week_total  = (
            Shift.objects.filter(
                timetable=timetable, worker=shift.worker
            ).exclude(pk=shift.pk)
            .values_list('hours', flat=True)
        )
        other_hours = sum(float(h) for h in week_total)
        if other_hours + duration_h > budget:
            errors.append(
                f'Edit would bring {shift.worker.full_name} to '
                f'{other_hours + duration_h:.1f}h, exceeding their '
                f'{budget}h weekly budget.'
            )

        if errors:
            return Response({'success': False, 'errors': errors},
                            status=status.HTTP_400_BAD_REQUEST)

        shift.start_time = start_t
        shift.end_time   = end_t
        shift.hours      = round(duration_h, 2)
        shift.save()

        return Response({
            'success': True,
            'message': 'Shift updated.',
            'shift'  : ShiftSerializer(shift).data,
        })


class TimetableShiftDeleteView(APIView):
    """
    DELETE /api/timetable/<pk>/shifts/<shift_pk>/

    Employee removes an individual shift from a timetable.
    """
    permission_classes = [IsOrgAdminOrEmployee]

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

    Returns only the shifts belonging to the currently logged-in worker.
    Used on the worker's personal timetable view.
    Workers can only see PUBLISHED timetables.
    Employees see all timetables for their org.
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
            # Employee: optionally filter by worker_id param
            worker_pk = request.query_params.get('worker_pk')
            shifts = timetable.shifts.all()
            if worker_pk:
                shifts = shifts.filter(worker_id=worker_pk)

        shift_data  = ShiftSerializer(shifts, many=True).data
        total_hours = sum(float(s['hours']) for s in shift_data)

        return Response({
            'success'    : True,
            'timetable_id': timetable.pk,
            'week_start' : timetable.week_start,
            'week_end'   : timetable.week_end,
            'status'     : timetable.status,
            'shifts'     : shift_data,
            'total_hours': round(total_hours, 2),
        })


class TimetablePDFView(APIView):
    """
    GET /api/timetable/<pk>/pdf/

    Streams the timetable as a downloadable PDF.
    Available to both employees and workers (workers: published only).
    """
    permission_classes = [IsOrgAdminOrReadOnly]

    def get(self, request, pk):
        from django.http import HttpResponse
        from timetable_app.pdf_export import generate_pdf_bytes

        try:
            timetable = Timetable.objects.prefetch_related(
                'shifts__worker'
            ).get(pk=pk, org=_get_org_from_request(request))
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not hasattr(request, 'org') and timetable.status != Timetable.Status.PUBLISHED:
            return Response({'error': 'Timetable not yet published.'},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            pdf_bytes = generate_pdf_bytes(timetable)
        except Exception as e:
            return Response({'error': f'PDF generation failed: {str(e)}'},
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

    Returns the timetable as a rendered HTML string.
    Used for the digital (screen) timetable view in the AngularJS frontend.
    Both roles, published-only for workers.
    """
    permission_classes = [IsOrgAdminOrReadOnly]

    def get(self, request, pk):
        from django.http import HttpResponse
        from timetable_app.pdf_export import build_timetable_html

        try:
            timetable = Timetable.objects.prefetch_related(
                'shifts__worker'
            ).get(pk=pk, org=request.user.org)
        except Timetable.DoesNotExist:
            return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.is_worker and timetable.status != Timetable.Status.PUBLISHED:
            return Response({'error': 'Timetable not yet published.'},
                            status=status.HTTP_403_FORBIDDEN)

        html = build_timetable_html(timetable)
        return HttpResponse(html, content_type='text/html')



# ===========================================================================
# ORGANISATION — REGISTRATION, LOGIN, EMPLOYEE MANAGEMENT
# All org-scoped endpoints receive org_id as a URL kwarg.
# The org_id is the 8-char Base64url identifier on every org-scoped URL.
# ===========================================================================

def _get_org_or_404(org_id):
    """Shared helper — look up an active org by its public org_id."""
    try:
        return Organisation.objects.get(org_id=org_id, is_active=True)
    except Organisation.DoesNotExist:
        return None


class OrgPublicView(APIView):
    """
    GET /api/org/<org_id>/public/   (no auth)
    Returns safe public info about an org — name, shop hours, org_id.
    Used by the login and join pages to display org context.
    """
    permission_classes = [AllowAny]

    def get(self, request, org_id):
        org = _get_org_or_404(org_id)
        if not org:
            return Response({'error': 'Organisation not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'success': True,
            'org': {
                'org_id'    : org.org_id,
                'name'      : org.name,
                'shop_open' : str(org.shop_open)[:5],
                'shop_close': str(org.shop_close)[:5],
            }
        })


class OrgJoinInfoView(APIView):
    """
    GET /api/org/<org_id>/join/   (no auth)

    Returns org info + ALL active users (employees + workers) as one
    unified list for the name-picker login page.
    The role is included so the frontend can route correctly after login.
    """
    permission_classes = [AllowAny]

    def get(self, request, org_id):
        org = _get_org_or_404(org_id)
        if not org:
            return Response({'error': 'Organisation not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Return all active users (no ADMIN role exists — org owner is on Organisation)
        users = (
            User.objects
            .filter(org=org, is_active=True)
            .order_by('full_name')
            .values('user_id', 'full_name', 'role')
        )

        return Response({
            'success': True,
            'org': {
                'org_id'    : org.org_id,
                'name'      : org.name,
                'shop_open' : str(org.shop_open)[:5],
                'shop_close': str(org.shop_close)[:5],
            },
            'users': list(users),
        })


class OrgRegisterView(APIView):
    """
    POST /api/org/register/   (no auth)

    Registers a new organisation. On success returns:
      - org_id  (8-char Base64url — used in all org URLs)
      - login_url  (/#/org/<org_id>/login)
      - join_url   (/#/org/<org_id>/join — send to workers)
      - first employee credentials (shown once)
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
        org = serializer.save()

        host = request.build_absolute_uri('/').rstrip('/')
        return Response({
            'success'     : True,
            'message'     : f'Organisation "{org.name}" registered. Your org ID is {org.org_id}.',
            'organisation': OrgDetailSerializer(org, context={'request': request}).data,
            'org_id'      : org.org_id,
            'login_url'   : f'{host}/#/org/{org.org_id}/login',
            'join_url'    : f'{host}/#/org/{org.org_id}/join',
        }, status=status.HTTP_201_CREATED)

class OrgLoginView(APIView):
    """
    POST /api/org/<org_id>/login/   (no auth)

    Accepts either:
      { "identifier": "admin@acme.com",  "password": "..." }
      { "identifier": "aB3-xY7_",        "password": "..." }

    The org_id in the URL is used ONLY to scope the URL for UI purposes.
    If logging in by email, the org_id in the URL is ignored for lookup
    but we still validate it matches after login for security.
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

        # If a real org_id was in the URL (not a placeholder), verify it matches
        if org_id and org_id != 'login' and org.org_id != org_id:
            return Response(
                {'success': False,
                 'errors': ['The credentials do not belong to this organisation.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        OrgToken.objects.filter(org=org).delete()
        token = OrgToken.create_for_org(org)

        return Response({
            'success'     : True,
            'message'     : f'Welcome, {org.name}!',
            'org_token'   : token.token,
            'expires_at'  : token.expires_at,
            'organisation': OrgDetailSerializer(org, context={'request': request}).data,
        })


class OrgLoginGlobalView(APIView):
    """
    POST /api/org/login/   (no org_id in URL — used from home page)

    Same logic as OrgLoginView but without URL-scoped org_id.
    Used when the user logs in from the home page without knowing their org_id.
    Returns the org_id so the frontend can redirect to the correct org URL.
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
            'success'     : True,
            'message'     : f'Welcome, {org.name}!',
            'org_token'   : token.token,
            'expires_at'  : token.expires_at,
            'organisation': OrgDetailSerializer(org, context={'request': request}).data,
        })


class OrgLogoutView(APIView):
    """POST /api/org/<org_id>/logout/"""
    permission_classes = [AllowAny]

    def post(self, request, org_id):
        from timetable_app.models import OrgToken
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if auth.startswith('Org-Token '):
            token_str = auth.split(' ', 1)[1].strip()
            OrgToken.objects.filter(token=token_str).delete()
        return Response({'success': True, 'message': 'Logged out.'})


class OrgMeView(APIView):
    """GET /api/org/<org_id>/me/  — Org-Token required"""
    from timetable_app.permissions import IsOrgAdmin
    permission_classes = [IsOrgAdmin]

    def get(self, request, org_id):
        from timetable_app.serializers import OrgDetailSerializer, WorkerListSerializer
        org = request.org
        if org.org_id != org_id:
            return Response({'error': 'Token does not match this organisation.'},
                            status=status.HTTP_403_FORBIDDEN)
        # Org owner details come from the Organisation itself — no ADMIN User row
        employees = User.objects.filter(org=org, is_active=True)
        return Response({
            'success'      : True,
            'organisation' : OrgDetailSerializer(org, context={'request': request}).data,
            'employees'    : WorkerListSerializer(employees, many=True).data,
        })


class OrgUpdateView(APIView):
    """PATCH /api/org/<org_id>/update/  — Org-Token required"""
    from timetable_app.permissions import IsOrgAdmin
    permission_classes = [IsOrgAdmin]

    def patch(self, request, org_id):
        from timetable_app.serializers import OrgDetailSerializer
        org  = request.org
        if org.org_id != org_id:
            return Response({'error': 'Token does not match this organisation.'},
                            status=status.HTTP_403_FORBIDDEN)
        data = request.data

        if 'name' in data:
            name = data['name'].strip()
            if Organisation.objects.filter(name__iexact=name).exclude(pk=org.pk).exists():
                return Response({'error': 'Organisation name already taken.'},
                                status=status.HTTP_400_BAD_REQUEST)
            org.name = name
        if 'shop_open'  in data: org.shop_open  = data['shop_open']
        if 'shop_close' in data: org.shop_close = data['shop_close']
        if str(org.shop_open) >= str(org.shop_close):
            return Response({'error': 'shop_open must be earlier than shop_close.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if 'email' in data:
            email = data['email'].lower()
            if Organisation.objects.filter(email=email).exclude(pk=org.pk).exists():
                return Response({'error': 'Email already in use.'}, status=status.HTTP_400_BAD_REQUEST)
            org.email = email
        if 'password' in data:
            if len(data['password']) < 8:
                return Response({'error': 'Password must be at least 8 characters.'},
                                status=status.HTTP_400_BAD_REQUEST)
            org.set_password(data['password'])

        org.save()
        return Response({
            'success'      : True,
            'message'      : 'Organisation updated.',
            'organisation' : OrgDetailSerializer(org, context={'request': request}).data,
        })


class OrgEmployeeListCreateView(APIView):
    """
    GET  /api/org/<org_id>/employees/  — list workers
    POST /api/org/<org_id>/employees/  — create worker (returns plain_password once)
    Org-Token required. URL kept as /employees/ for backward compatibility with frontend.
    """
    from timetable_app.permissions import IsOrgAdmin
    permission_classes = [IsOrgAdmin]

    def get(self, request, org_id):
        org = request.org
        if org.org_id != org_id:
            return Response({'error': 'Token mismatch.'}, status=status.HTTP_403_FORBIDDEN)
        employees = User.objects.filter(org=org, role=User.Role.WORKER)
        return Response({
            'success'  : True,
            'count'    : employees.count(),
            'employees': WorkerListSerializer(employees, many=True).data,
        })

    def post(self, request, org_id):
        from timetable_app.models import generate_user_id, generate_worker_password
        org = request.org
        if org.org_id != org_id:
            return Response({'error': 'Token mismatch.'}, status=status.HTTP_403_FORBIDDEN)

        full_name = request.data.get('full_name', '').strip()
        if not full_name:
            return Response({'error': 'full_name is required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        plain_pwd = generate_worker_password(length=12)
        worker = User(
            full_name      = full_name,
            role           = User.Role.WORKER,
            org            = org,
            plain_password = plain_pwd,
        )
        worker.user_id = generate_user_id()
        worker.set_password(plain_pwd)
        worker.save()
        User.objects.filter(pk=worker.pk).update(plain_password=None)

        return Response({
            'success': True,
            'message': f'Worker "{worker.full_name}" created. Save credentials — shown once.',
            'employee': {
                'id'            : worker.pk,
                'full_name'     : worker.full_name,
                'user_id'       : worker.user_id,
                'plain_password': plain_pwd,
                'role'          : 'WORKER',
                'org'           : org.pk,
                'login_url'     : request.build_absolute_uri(f'/#/org/{org_id}/join'),
            },
        }, status=status.HTTP_201_CREATED)


class OrgEmployeeDetailView(APIView):
    """
    PATCH  /api/org/<org_id>/employees/<pk>/  — update worker
    DELETE /api/org/<org_id>/employees/<pk>/  — deactivate worker
    Org-Token required.
    """
    from timetable_app.permissions import IsOrgAdmin
    permission_classes = [IsOrgAdmin]

    def _get_emp(self, pk, org):
        try:
            return User.objects.get(pk=pk, org=org, role=User.Role.WORKER)
        except User.DoesNotExist:
            return None

    def patch(self, request, org_id, pk):
        org = request.org
        if org.org_id != org_id:
            return Response({'error': 'Token mismatch.'}, status=status.HTTP_403_FORBIDDEN)
        emp = self._get_emp(pk, org)
        if not emp:
            return Response({'error': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)
        if 'full_name' in request.data:
            emp.full_name = request.data['full_name'].strip()
        if 'is_active' in request.data:
            emp.is_active = bool(request.data['is_active'])
        emp.save()
        return Response({'success': True, 'employee': WorkerListSerializer(emp).data})

    def delete(self, request, org_id, pk):
        org = request.org
        if org.org_id != org_id:
            return Response({'error': 'Token mismatch.'}, status=status.HTTP_403_FORBIDDEN)
        emp = self._get_emp(pk, org)
        if not emp:
            return Response({'error': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)
        emp.is_active = False
        emp.save(update_fields=['is_active'])
        return Response({'success': True, 'message': f'Employee "{emp.full_name}" deactivated.'})


class OrgEmployeeResetPasswordView(APIView):
    """POST /api/org/<org_id>/employees/<pk>/reset-password/  — Org-Token required"""
    from timetable_app.permissions import IsOrgAdmin
    permission_classes = [IsOrgAdmin]

    def post(self, request, org_id, pk):
        from timetable_app.models import generate_worker_password
        org = request.org
        if org.org_id != org_id:
            return Response({'error': 'Token mismatch.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            emp = User.objects.get(pk=pk, org=org, role=User.Role.WORKER)
        except User.DoesNotExist:
            return Response({'error': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)
        new_pw = generate_worker_password(length=12)
        emp.set_password(new_pw)
        emp.save()
        return Response({
            'success'     : True,
            'message'     : f'Password reset for "{emp.full_name}".',
            'user_id'     : emp.user_id,
            'new_password': new_pw,
        })


class OrgListView(APIView):
    """GET /api/org/list/  — public, no auth. Returns org_id + name."""
    permission_classes = [AllowAny]

    def get(self, request):
        orgs = Organisation.objects.filter(is_active=True).values('org_id', 'name')
        return Response({'success': True, 'organisations': list(orgs)})


# ===========================================================================
# ADD USER VIEW
# ===========================================================================
class AddUserView(APIView):
    """
    POST /api/org/<org_id>/add-user/
    Org-Token required. Creates full user with personal details.
    """
    from timetable_app.permissions import IsOrgAdmin
    permission_classes = [IsOrgAdmin]

    def post(self, request, org_id):
        from timetable_app.serializers import AddUserSerializer
        org = request.org
        if org.org_id != org_id:
            return Response({'error': 'Token mismatch.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = AddUserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        user, plain_pwd = serializer.save(org=org)

        response_data = {
            'success'  : True,
            'message'  : f'User "{user.full_name}" added to {org.name}.',
            'user': {
                'id'        : user.pk,
                'user_id'   : user.user_id,
                'full_name' : user.full_name,
                'email'     : user.email,
                'phone'     : user.phone,
                'role'      : user.role,
                'work_type' : user.work_type,
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
    Org-Token required. Exact match only — no partial search.
    """
    from timetable_app.permissions import IsOrgAdmin
    permission_classes = [IsOrgAdmin]

    def get(self, request, org_id):
        from timetable_app.serializers import GlobalUserSearchSerializer
        org = request.org
        if org.org_id != org_id:
            return Response({'error': 'Token mismatch.'}, status=status.HTTP_403_FORBIDDEN)

        q      = (request.query_params.get('q') or '').strip()
        digits = ''.join(c for c in q if c.isdigit())

        if not q:
            return Response({'success': True, 'user': None,
                             'message': 'Enter a complete email or mobile number.'})

        user = None
        if '@' in q:
            user = User.objects.filter(email__iexact=q).first()
        elif digits:
            user = User.objects.filter(phone=digits).first()

        if not user:
            return Response({'success': True, 'user': None,
                             'message': 'No user found with that email or mobile number.'})

        return Response({'success': True, 'user': GlobalUserSearchSerializer(user).data})
