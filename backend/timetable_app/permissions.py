"""
permissions.py — Timetable Planner

Custom DRF permission classes.

Authentication model:
  - Workers log in with JWT (POST /api/auth/login/).
    All JWT-authenticated users are workers — there is no EMPLOYEE role.
  - Organisation admins authenticate with Org-Token (POST /api/org/<id>/login/).
    Org-Token is issued to the Organisation itself, not to a User row.

┌─────────────────────────────┬───────────┬────────┐
│ Action                      │ Org Admin │ Worker │
├─────────────────────────────┼───────────┼────────┤
│ Create/Delete workers       │    ✅     │   ❌   │
│ Set work type & limits      │    ✅     │   ❌   │
│ Set shop hours              │    ✅     │   ❌   │
│ View all availability       │    ✅     │   ❌   │
│ Submit own availability     │    ❌     │   ✅   │
│ Generate / edit timetable   │    ✅     │   ❌   │
│ View timetable              │    ✅     │   ✅   │
│ Download PDF                │    ✅     │   ✅   │
└─────────────────────────────┴───────────┴────────┘
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsWorker(BasePermission):
    """
    Grants access only to authenticated JWT users (all JWT users are workers).
    Used on endpoints that workers interact with: availability submission,
    timetable viewing, profile reading.
    """
    message = 'Access restricted to authenticated Worker accounts.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
        )


class IsOwnerWorkerOrOrgAdmin(BasePermission):
    """
    Object-level permission for Availability records.

    - Org admin (Org-Token): full read/write on any record.
    - Worker (JWT): can only read their own records (POST handled separately).
      Workers can NEVER update or delete — enforced by the view.
    """
    message = 'Workers can only access their own availability records.'

    def has_object_permission(self, request, view, obj):
        # Org-Token path
        if hasattr(request, 'org') and request.org:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        # Worker can read their own record only
        return obj.worker == request.user


class IsSameOrgWorker(BasePermission):
    """
    Ensures a Worker can only access objects within their own organisation.
    """
    message = 'You can only access resources within your own organisation.'

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if hasattr(obj, 'org'):
            return obj.org == request.user.org
        if hasattr(obj, 'worker'):
            return obj.worker.org == request.user.org
        return False


class IsOrgAdmin(BasePermission):
    """
    Grants access to requests authenticated with a valid Org-Token header.
    Used exclusively on organisation-admin endpoints.

    Header format:  Authorization: Org-Token <token>
    """
    message = 'Valid Org-Token required. Log in at /api/org/login/.'

    def has_permission(self, request, view):
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth.startswith('Org-Token '):
            return False
        token_str = auth.split(' ', 1)[1].strip()
        from timetable_app.models import OrgToken
        try:
            tok = OrgToken.objects.select_related('org').get(token=token_str)
            if tok.is_expired:
                tok.delete()
                return False
            request.org = tok.org
            return True
        except OrgToken.DoesNotExist:
            return False


class IsOrgAdminOrWorker(BasePermission):
    """
    Grants access to either:
    - A request authenticated with a valid Org-Token (org admin), or
    - An authenticated JWT worker.

    Used on endpoints accessible from the org admin panel that were
    previously restricted to an EMPLOYEE role (manage workers, timetable
    generation, shop settings, work-type limits).

    When authenticated via Org-Token, request.org is set.
    When authenticated via JWT, request.user.org is used.
    """
    message = 'Access requires a valid Org-Token or an authenticated Worker JWT.'

    def has_permission(self, request, view):
        # Path 1: Org-Token
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if auth.startswith('Org-Token '):
            token_str = auth.split(' ', 1)[1].strip()
            from timetable_app.models import OrgToken
            try:
                tok = OrgToken.objects.select_related('org').get(token=token_str)
                if tok.is_expired:
                    tok.delete()
                    return False
                request.org = tok.org
                return True
            except OrgToken.DoesNotExist:
                return False
        # Path 2: JWT worker — only Org-Token callers get write access
        # (views restrict further as needed)
        return False


class IsOrgAdminOrReadOnly(BasePermission):
    """
    Org-Token admins have full access (read + write).
    JWT Workers have read-only access (GET, HEAD, OPTIONS).

    Used for timetable endpoints where both can view,
    but only the org admin can create/edit/delete/publish.
    """
    message = 'Workers have read-only access. Modifications require an Org-Token.'

    def has_permission(self, request, view):
        # Org-Token path (always full access)
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if auth.startswith('Org-Token '):
            token_str = auth.split(' ', 1)[1].strip()
            from timetable_app.models import OrgToken
            try:
                tok = OrgToken.objects.select_related('org').get(token=token_str)
                if tok.is_expired:
                    tok.delete()
                    return False
                request.org = tok.org
                return True
            except OrgToken.DoesNotExist:
                return False

        # JWT worker path — read-only
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return False


# ---------------------------------------------------------------------------
# Backward-compat aliases (used in views.py) — point to the new classes
# ---------------------------------------------------------------------------
IsOrgAdminOrEmployee   = IsOrgAdminOrWorker    # org-admin-only write, no JWT writes
IsOrgAdminOrReadOnly   = IsOrgAdminOrReadOnly  # already the same name
