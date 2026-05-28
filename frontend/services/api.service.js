"use strict";

angular.module("TimetableApp").service("ApiService", [
  "$http",
  function ($http) {
    const B = "http://127.0.0.1:8000/api";

    // ── Auth (JWT) ────────────────────────────────────────────────────────
    this.login = (userId, password) =>
      $http.post(`${B}/auth/login/`, { user_id: userId, password });
    this.me = () => $http.get(`${B}/auth/me/`);

    // ── Org public ────────────────────────────────────────────────────────
    this.orgRegister = (data) => $http.post(`${B}/org/register/`, data);
    this.orgPublic = (orgId) => $http.get(`${B}/org/${orgId}/public/`);
    this.orgJoinInfo = (orgId) => $http.get(`${B}/org/${orgId}/join/`);

    // ── Org auth ─────────────────────────────────────────────────────────
    this.orgLogin = (orgId, identifier, pw) =>
      $http.post(`${B}/org/${orgId}/login/`, { identifier, password: pw });

    this.orgLoginGlobal = (identifier, pw) =>
      $http.post(`${B}/org/login/`, { identifier, password: pw });
    this.orgLogout = (orgId) => $http.post(`${B}/org/${orgId}/logout/`, {});

    // ── Org admin (Org-Token) ─────────────────────────────────────────────
    this.orgMe = (orgId) => $http.get(`${B}/org/${orgId}/me/`);
    this.orgUpdate = (orgId, data) =>
      $http.patch(`${B}/org/${orgId}/update/`, data);

    this.orgListEmployees = (orgId) =>
      $http.get(`${B}/org/${orgId}/employees/`);
    this.orgCreateEmployee = (orgId, data) =>
      $http.post(`${B}/org/${orgId}/employees/`, data);
    this.orgUpdateEmployee = (orgId, pk, d) =>
      $http.patch(`${B}/org/${orgId}/employees/${pk}/`, d);
    this.orgDeleteEmployee = (orgId, pk) =>
      $http.delete(`${B}/org/${orgId}/employees/${pk}/`);
    this.orgResetEmpPw = (orgId, pk) =>
      $http.post(`${B}/org/${orgId}/employees/${pk}/reset-password/`, {});

    // Add user + global search (Org-Token)
    this.orgAddUser = (orgId, data) =>
      $http.post(`${B}/org/${orgId}/add-user/`, data);
    this.orgSearchUser = (orgId, q) =>
      $http.get(`${B}/org/${orgId}/global-users/`, { params: { q } });

    // ── Organisation settings (Employee JWT) ─────────────────────────────
    this.getOrg = (orgId) => $http.get(`${B}/org/${orgId}/settings/`);
    this.updateOrg = (orgId, data) =>
      $http.patch(`${B}/org/${orgId}/settings/`, data);

    // ── Work type limits ──────────────────────────────────────────────────
    this.getLimits = () => $http.get(`${B}/work-limits/`);
    this.setLimit = (data) => $http.post(`${B}/work-limits/`, data);

    // ── Workers — URL pattern: /api/org/<orgId>/workers/ and /api/org/<orgId>/<userId>/ ──
    // Public worker list for join screen
    this.getPublicWorkers = (orgId) =>
      $http.get(`${B}/org/${orgId}/workers/public/`);
    // List / create workers  →  /api/org/<orgId>/workers/
    this.listWorkers = (orgId, params) =>
      $http.get(`${B}/org/${orgId}/workers/`, { params });
    this.createWorker = (orgId, data) =>
      $http.post(`${B}/org/${orgId}/workers/`, data);
    // Single worker by user_id  →  /api/org/<orgId>/<userId>/
    this.getWorker = (orgId, userId) =>
      $http.get(`${B}/org/${orgId}/${userId}/`);
    this.updateWorker = (orgId, userId, d) =>
      $http.patch(`${B}/org/${orgId}/${userId}/`, d);
    this.deleteWorker = (orgId, userId) =>
      $http.delete(`${B}/org/${orgId}/${userId}/`);
    this.resetPassword = (orgId, userId) =>
      $http.post(`${B}/org/${orgId}/${userId}/reset-password/`, {});

    // ── Availability ──────────────────────────────────────────────────────
    this.getAvailability = (p) =>
      $http.get(`${B}/availability/`, { params: p });
    this.submitAvailability = (data) => $http.post(`${B}/availability/`, data);
    this.deleteAvailability = (pk) => $http.delete(`${B}/availability/${pk}/`);
    this.patchAvailability = (pk, d) =>
      $http.patch(`${B}/availability/${pk}/`, d);

    // ── Timetable ─────────────────────────────────────────────────────────
    this.listTimetables = () => $http.get(`${B}/timetable/`);
    this.getTimetable = (pk) => $http.get(`${B}/timetable/${pk}/`);
    this.generateTimetable = (ws, r) =>
      $http.post(`${B}/timetable/generate/`, {
        week_start: ws,
        regenerate: !!r,
      });
    this.publishTimetable = (pk) =>
      $http.post(`${B}/timetable/${pk}/publish/`, {});
    this.getWorkerView = (pk, wp) =>
      $http.get(`${B}/timetable/${pk}/worker/`, {
        params: wp ? { worker_pk: wp } : {},
      });
    this.patchShift = (tp, sp, d) =>
      $http.patch(`${B}/timetable/${tp}/shifts/${sp}/`, d);
    this.deleteShift = (tp, sp) =>
      $http.delete(`${B}/timetable/${tp}/shifts/${sp}/delete/`);
    this.getTimetableHTML = (pk) =>
      $http.get(`${B}/timetable/${pk}/html/`, {
        headers: { Accept: "text/html" },
        transformResponse: [(d) => d],
      });
    this.pdfUrl = (pk) => `${B}/timetable/${pk}/pdf/`;
  },
]);
