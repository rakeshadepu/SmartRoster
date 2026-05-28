"""
timetable_app/urls.py
All routes prefixed with /api/ from config/urls.py

URL DESIGN
  Public (no auth):
    POST /api/org/register/

  Org-scoped public:
    POST /api/org/<org_id>/login/
    POST /api/org/<org_id>/logout/
    GET  /api/org/<org_id>/join/         ← worker join info page data
    GET  /api/org/<org_id>/public/       ← org name/hours for join/login page

  Org-admin (Org-Token):
    GET    /api/org/<org_id>/me/
    PATCH  /api/org/<org_id>/update/
    GET    /api/org/<org_id>/workers/
    POST   /api/org/<org_id>/workers/
    GET    /api/org/<org_id>/<user_id>/
    PATCH  /api/org/<org_id>/<user_id>/
    DELETE /api/org/<org_id>/<user_id>/
    POST   /api/org/<org_id>/<user_id>/reset-password/

  Worker/Employee JWT (scoped to org via user.org):
    POST /api/auth/login/
    POST /api/auth/logout/
    POST /api/auth/refresh/
    GET  /api/auth/me/
    GET  /api/org/<org_id>/settings/
    PATCH /api/org/<org_id>/settings/
    ...availability/timetable routes unchanged
"""

from django.urls import path
from timetable_app import views

urlpatterns = [
    # ── Auth (JWT — employee/worker) ──────────────────────────────────────
    path('auth/login/',   views.LoginView.as_view(),        name='auth-login'),
    path('auth/logout/',  views.LogoutView.as_view(),       name='auth-logout'),
    path('auth/refresh/', views.RefreshTokenView.as_view(), name='auth-refresh'),
    path('auth/me/',      views.MeView.as_view(),           name='auth-me'),

    # ── Organisation — global public ──────────────────────────────────────
    path('org/register/', views.OrgRegisterView.as_view(), name='org-register'),

    # ── Organisation — scoped by org_id ──────────────────────────────────
    path('org/login/',
         views.OrgLoginGlobalView.as_view(), name='org-login-global'),
    path('org/<str:org_id>/public/',
         views.OrgPublicView.as_view(),          name='org-public'),
    path('org/<str:org_id>/join/',
         views.OrgJoinInfoView.as_view(),         name='org-join'),
    path('org/<str:org_id>/login/',
         views.OrgLoginView.as_view(),            name='org-login'),
    path('org/<str:org_id>/logout/',
         views.OrgLogoutView.as_view(),           name='org-logout'),
    path('org/<str:org_id>/me/',
         views.OrgMeView.as_view(),               name='org-me'),
    path('org/<str:org_id>/update/',
         views.OrgUpdateView.as_view(),           name='org-update'),

    # Org settings (used by employee after JWT login)
    path('org/<str:org_id>/settings/',
         views.OrganisationView.as_view(),        name='org-settings'),

    # Add user and global search (Org-Token)
    path('org/<str:org_id>/add-user/',
         views.AddUserView.as_view(),             name='org-add-user'),
    path('org/<str:org_id>/global-users/',
         views.GlobalUserSearchView.as_view(),    name='org-global-search'),

    # ── Worker management (Org-Token) — URLs: org_id/user_id ─────────────
    # List/create workers for an org
    path('org/<str:org_id>/workers/',
         views.WorkerListCreateView.as_view(),    name='org-worker-list-create'),
    # Worker public list (unauthenticated — for join/login screen)
    path('org/<str:org_id>/workers/public/',
         views.WorkerPublicListView.as_view(),    name='workers-public'),
    # Single worker detail: GET/PATCH/DELETE  →  /api/org/<org_id>/<user_id>/
    path('org/<str:org_id>/<str:user_id>/',
         views.WorkerDetailView.as_view(),        name='org-worker-detail'),
    # Reset password        →  /api/org/<org_id>/<user_id>/reset-password/
    path('org/<str:org_id>/<str:user_id>/reset-password/',
         views.WorkerResetPasswordView.as_view(), name='org-worker-reset-pw'),

    # ── Work Type Limits (Employee JWT) ───────────────────────────────────
    path('work-limits/', views.WorkTypeLimitListView.as_view(), name='work-limits'),

    # ── Availability ──────────────────────────────────────────────────────
    path('availability/',          views.AvailabilityView.as_view(),       name='availability-list'),
    path('availability/<int:pk>/', views.AvailabilityDetailView.as_view(), name='availability-detail'),

    # ── Timetable ─────────────────────────────────────────────────────────
    path('timetable/',
         views.TimetableListView.as_view(),     name='timetable-list'),
    path('timetable/generate/',
         views.TimetableGenerateView.as_view(), name='timetable-generate'),
    path('timetable/<int:pk>/',
         views.TimetableDetailView.as_view(),   name='timetable-detail'),
    path('timetable/<int:pk>/publish/',
         views.TimetablePublishView.as_view(),  name='timetable-publish'),
    path('timetable/<int:pk>/worker/',
         views.TimetableWorkerView.as_view(),   name='timetable-worker-view'),
    path('timetable/<int:pk>/shifts/<int:shift_pk>/',
         views.TimetableShiftEditView.as_view(),   name='timetable-shift-edit'),
    path('timetable/<int:pk>/shifts/<int:shift_pk>/delete/',
         views.TimetableShiftDeleteView.as_view(), name='timetable-shift-delete'),
    path('timetable/<int:pk>/pdf/',
         views.TimetablePDFView.as_view(),      name='timetable-pdf'),
    path('timetable/<int:pk>/html/',
         views.TimetableHTMLView.as_view(),     name='timetable-html'),
]
