from django.urls import path
from timetable_app import views

urlpatterns = [

    # =========================================================
    # AUTH (JWT - Workers)
    # =========================================================
    path('auth/login/', views.LoginView.as_view(), name='auth-login'),
    path('auth/logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('auth/refresh/', views.RefreshTokenView.as_view(), name='auth-refresh'),
    path('auth/me/', views.MeView.as_view(), name='auth-me'),

    # =========================================================
    # ORGANISATION PUBLIC
    # =========================================================
    path('org/register/', views.OrgRegisterView.as_view(), name='org-register'),

    path('org/login/',
         views.OrgLoginGlobalView.as_view(),
         name='org-login-global'),

    path('org/<str:org_id>/public/',
         views.OrgPublicView.as_view(),
         name='org-public'),

    path('org/<str:org_id>/join/',
         views.OrgJoinInfoView.as_view(),
         name='org-join'),

    path('org/<str:org_id>/login/',
         views.OrgLoginView.as_view(),
         name='org-login'),

    path('org/<str:org_id>/logout/',
         views.OrgLogoutView.as_view(),
         name='org-logout'),

    # =========================================================
    # ORGANISATION ADMIN
    # =========================================================
    path('org/<str:org_id>/me/',
         views.OrgMeView.as_view(),
         name='org-me'),

    path('org/<str:org_id>/settings/',
         views.OrganisationView.as_view(),
         name='org-settings'),

    path('org/<str:org_id>/add-user/',
         views.AddUserView.as_view(),
         name='org-add-user'),

    path('org/<str:org_id>/email-conflicts/',
         views.EmailConflictView.as_view(),
         name='org-email-conflicts'),

    path('org/<str:org_id>/global-users/',
         views.GlobalUserSearchView.as_view(),
         name='org-global-users'),

    # =========================================================
    # WORKERS
    # =========================================================

    # list + create
    path('org/<str:org_id>/workers/',
         views.WorkerListCreateView.as_view(),
         name='worker-list-create'),

    # public worker list
    path('org/<str:org_id>/workers/public/',
         views.WorkerPublicListView.as_view(),
         name='worker-public-list'),

    # worker details
    path('org/<str:org_id>/workers/<str:user_id>/',
         views.WorkerDetailView.as_view(),
         name='worker-detail'),

    # password reset
    path('org/<str:org_id>/workers/<str:user_id>/reset-password/',
         views.WorkerResetPasswordView.as_view(),
         name='worker-reset-password'),

    # =========================================================
    # WORK TYPE LIMITS
    # =========================================================
    path('work-limits/',
         views.WorkTypeLimitListView.as_view(),
         name='work-limits'),

    # =========================================================
    # AVAILABILITY
    # =========================================================
    path('availability/',
         views.AvailabilityView.as_view(),
         name='availability-list'),

    path('availability/<int:pk>/',
         views.AvailabilityDetailView.as_view(),
         name='availability-detail'),

    # =========================================================
    # TIMETABLE
    # =========================================================
    path('timetable/',
         views.TimetableListView.as_view(),
         name='timetable-list'),

    path('timetable/generate/',
         views.TimetableGenerateView.as_view(),
         name='timetable-generate'),

    path('timetable/<int:pk>/',
         views.TimetableDetailView.as_view(),
         name='timetable-detail'),

    path('timetable/<int:pk>/publish/',
         views.TimetablePublishView.as_view(),
         name='timetable-publish'),

    path('timetable/<int:pk>/worker/',
         views.TimetableWorkerView.as_view(),
         name='timetable-worker-view'),

    path('timetable/<int:pk>/shifts/<int:shift_pk>/',
         views.TimetableShiftEditView.as_view(),
         name='timetable-shift-edit'),

    path('timetable/<int:pk>/shifts/<int:shift_pk>/delete/',
         views.TimetableShiftDeleteView.as_view(),
         name='timetable-shift-delete'),

    path('timetable/<int:pk>/pdf/',
         views.TimetablePDFView.as_view(),
         name='timetable-pdf'),

    path('timetable/<int:pk>/html/',
         views.TimetableHTMLView.as_view(),
         name='timetable-html'),
]