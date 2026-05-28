"""
permissions.py — Timetable Planner Phase 1

Custom DRF permission classes that enforce the role-based access matrix:

┌─────────────────────────────┬──────────┬────────┐
│ Action                      │ Employee │ Worker │
├─────────────────────────────┼──────────┼────────┤
│ Create/Delete workers       │    ✅    │   ❌   │
│ Set work type & limits      │    ✅    │   ❌   │
│ Set shop hours              │    ✅    │   ❌   │
│ View all availability       │    ✅    │   ❌   │
│ Submit own availability     │    ❌    │   ✅   │
│ Edit own availability       │    ❌    │   ❌   │
│ Generate / edit timetable   │    ✅    │   ❌   │
│ View timetable              │    ✅    │   ✅   │
│ Download PDF                │    ✅    │   ✅   │
│ Edit own profile            │    ✅    │   ❌   │
└─────────────────────────────┴──────────┴────────┘
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsEmployee(BasePermission):
    """
    Grants access only to authenticated users with role == EMPLOYEE.
    Used on endpoints that manage workers, settings, and timetable generation.
    """
    message = 'Access restricted to Employee (manager) accounts only.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_employee
        )


class IsWorker(BasePermission):
    """
    Grants access only to authenticated users with role == WORKER.
    Used on the availability submission endpoint.
    """
    message = 'Access restricted to Worker accounts only.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_worker
        )


class IsEmployeeOrReadOnly(BasePermission):
    """
    Employees have full access (read + write).
    Workers have read-only access (GET, HEAD, OPTIONS).

    Used for timetable endpoints where both roles can view,
    but only employees can create/edit/delete.
    """
    message = 'Workers have read-only access. Modifications require an Employee account.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True                    # both roles can read
        return request.user.is_employee    # only employees can write


class IsOwnerWorkerOrEmployee(BasePermission):
    """
    Object-level permission used on Availability records.

    - Employee: can read/write any availability record.
    - Worker:   can only read their own records (POST is allowed by IsWorker separately).

    Workers can NEVER update or delete — that restriction is enforced
    by checking the HTTP method in the view.
    """
    message = 'Workers can only access their own availability records.'

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_employee:
            return True
        # Worker can read their own record only
        return obj.worker == request.user


class IsSameOrgEmployee(BasePermission):
    """
    Ensures an Employee can only manage workers within their own organisation.
    Prevents cross-org data access.
    """
    message = 'You can only manage workers within your own organisation.'

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if not request.user.is_employee:
            return False
        # Employee must be in the same org as the worker/object
        if hasattr(obj, 'org'):
            return obj.org == request.user.org
        if hasattr(obj, 'worker'):
            return obj.worker.org == request.user.org
        return False


class IsOrgAdmin(BasePermission):
    """
    Grants access to requests authenticated with a valid Org-Token header.
    Used exclusively on organisation-admin endpoints (register employee, view org).

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
            request.org = tok.org        # attach org to request
            return True
        except OrgToken.DoesNotExist:
            return False
