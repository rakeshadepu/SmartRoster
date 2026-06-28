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

    // ── Org auth ──────────────────────────────────────────────────────────
    this.orgLogin = (orgId, identifier, pw) =>
      $http.post(`${B}/org/${orgId}/login/`, { identifier, password: pw });

    this.orgLoginGlobal = (identifier, pw) =>
      $http.post(`${B}/org/login/`, { identifier, password: pw });

    this.orgLogout = (orgId) => $http.post(`${B}/org/${orgId}/logout/`, {});

    // ── Org admin ─────────────────────────────────────────────────────────
    this.orgMe = (orgId) => $http.get(`${B}/org/${orgId}/me/`);

    this.orgSettings = (orgId) => $http.get(`${B}/org/${orgId}/settings/`);

    this.orgUpdate = (orgId, data) =>
      $http({
        method: "PATCH",
        url: `${B}/org/${orgId}/settings/`,
        data: data,
      });

    this.orgAddUser = (orgId, data) =>
      $http.post(`${B}/org/${orgId}/add-user/`, data);

    this.orgSearchUser = (orgId, q) =>
      $http.get(`${B}/org/${orgId}/global-users/`, { params: { q } });

    this.getEmailConflicts = (orgId) =>
      $http.get(`${B}/org/${orgId}/email-conflicts/`);

    this.getWorkerHistory = (orgId, userId) =>
      $http.get(`${B}/org/${orgId}/workers/${userId}/history/`);

    // ── Work type limits ──────────────────────────────────────────────────
    this.getLimits = () => $http.get(`${B}/work-limits/`);
    this.setLimit = (data) => $http.post(`${B}/work-limits/`, data);

    // ── Workers  →  /api/org/<orgId>/workers/  and  /workers/<userId>/ ───
    this.getPublicWorkers = (orgId) =>
      $http.get(`${B}/org/${orgId}/workers/public/`);

    this.listWorkers = (orgId, params) =>
      $http.get(`${B}/org/${orgId}/workers/`, { params });

    this.createWorker = (orgId, data) =>
      $http.post(`${B}/org/${orgId}/workers/`, data);

    this.getWorker = (orgId, userId) =>
      $http.get(`${B}/org/${orgId}/workers/${userId}/`);

    this.updateWorker = (orgId, userId, data) =>
      $http({
        method: "PATCH",
        url: `${B}/org/${orgId}/workers/${userId}/`,
        data: data,
      });


    this.deleteWorker = (orgId, userId) =>
      $http.delete(`${B}/org/${orgId}/workers/${userId}/`);

    this.resetPassword = (orgId, userId) =>
      $http.post(`${B}/org/${orgId}/workers/${userId}/reset-password/`, {});

    // email is sent as request body, not as the `email` config key
    this.updateWorkerEmail = (orgId, userId, email) =>
      $http({
        method: "PATCH",
        url: `${B}/org/${orgId}/workers/${userId}/`,
        data: { email },
      });


    this.changeWorkerPassword = (orgId, userId, data) =>
      $http.post(`${B}/org/${orgId}/workers/${userId}/reset-password/`, data);

    // ── Availability ──────────────────────────────────────────────────────
    this.getAvailability = (p) =>
      $http.get(`${B}/availability/`, { params: p });
    this.submitAvailability = (data) => $http.post(`${B}/availability/`, data);
    this.deleteAvailability = (pk) => $http.delete(`${B}/availability/${pk}/`);
    this.patchAvailability = (pk, data) =>
      $http({ method: "PATCH", url: `${B}/availability/${pk}/`, data: data });


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

    this.patchShift = (tp, sp, data) =>
      $http({
        method: "PATCH",
        url: `${B}/timetable/${tp}/shifts/${sp}/`,
        data: data,
      });
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
