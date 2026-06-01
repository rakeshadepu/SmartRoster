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

    this.orgMe = (orgId) =>
      $http.get(`${B}/org/${orgId}/me/`);

    this.orgUpdate = function (orgId, data) {
      return $http({
        method: "PATCH",
        url: `${B}/org/${orgId}/settings/`,
        data: data,
      });
    };

    // Add user + global search
    this.orgAddUser = (orgId, data) =>
      $http.post(`${B}/org/${orgId}/add-user/`, data);

    this.orgSearchUser = (orgId, q) =>
      $http.get(`${B}/org/${orgId}/global-users/`, {
        params: { q },
      });

    // ── Organisation settings ─────────────────────────────────────────────

    this.getOrg = (orgId) =>
      $http.get(`${B}/org/${orgId}/settings/`);

    this.updateOrg = function (orgId, data) {
      return $http({
        method: "PATCH",
        url: `${B}/org/${orgId}/settings/`,
        data: data,
      });
    };

    // ── Workers ────────────────────────────────────────────────────────────

    // Public worker list
    this.getPublicWorkers = (orgId) =>
      $http.get(`${B}/org/${orgId}/workers/public/`);

    // List workers
    this.listWorkers = (orgId, params) =>
      $http.get(`${B}/org/${orgId}/C/`, { params });

    // Create worker
    this.createWorker = (orgId, data) =>
      $http.post(`${B}/org/${orgId}/workers/`, data);

    // Get worker
    this.getWorker = (orgId, userId) =>
      $http.get(`${B}/org/${orgId}/workers/${userId}/`);

    // Update worker
    this.updateWorker = function (orgId, userId, data) {
      return $http({
        method: "PATCH",
        url: `${B}/org/${orgId}/workers/${userId}/`,
        data: data,
      });
    };

    // Delete worker
    this.deleteWorker = (orgId, userId) =>
      $http.delete(`${B}/org/${orgId}/workers/${userId}/`);

    // Reset password
    this.resetPassword = (orgId, userId) =>
      $http.post(
        `${B}/org/${orgId}/workers/${userId}/reset-password/`,
        {}
      );

    // Add user + global search (Org-Token)
    this.orgAddUser = (orgId, data) =>
      $http.post(`${B}/org/${orgId}/add-user/`, data);
    this.orgSearchUser = (orgId, q) =>
      $http.get(`${B}/org/${orgId}/global-users/`, { params: { q } });

    // ── Organisation settings (Employee JWT) ─────────────────────────────
    this.getOrg = (orgId) => $http.get(`${B}/org/${orgId}/settings/`);
    this.updateOrg = function (orgId, data) {
      return $http({
        method: "PATCH",
        url: `${B}/org/${orgId}/settings/`,
        data: data,
      });
    };

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
    this.updateWorker = function (orgId, userId, data) {
      return $http({
        method: "PATCH",
        url: `${B}/org/${orgId}/${userId}/`,
        data: data,
      });
    };
    this.deleteWorker = (orgId, userId) =>
      $http.delete(`${B}/org/${orgId}/${userId}/`);
    this.resetPassword = (orgId, userId) =>
      $http.post(`${B}/org/${orgId}/${userId}/reset-password/`, {});

    // ── Availability ──────────────────────────────────────────────────────
    this.getAvailability = (p) =>
      $http.get(`${B}/availability/`, { params: p });
    this.submitAvailability = (data) => $http.post(`${B}/availability/`, data);
    this.deleteAvailability = (pk) => $http.delete(`${B}/availability/${pk}/`);
    this.patchAvailability = function (pk, data) {
      return $http({
        method: "PATCH",
        url: `${B}/availability/${pk}/`,
        data: data,
      });
    };

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
    this.patchShift = function (tp, sp, data) {
      return $http({
        method: "PATCH",
        url: `${B}/timetable/${tp}/shifts/${sp}/`,
        data: data,
      });
    };
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
