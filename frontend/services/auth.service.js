"use strict";

angular.module("TimetableApp").service("AuthService", [
  "$window",
  "$rootScope",
  "$http",
  function ($window, $rootScope, $http) {
    const B = "http://127.0.0.1:8000/api";

    // ── JWT session (worker) ──────────────────────────────────────────────
    this.saveSession = function (tokens, user) {
      $window.localStorage.setItem("access_token", tokens.access);
      $window.localStorage.setItem("refresh_token", tokens.refresh);
      $window.localStorage.setItem("user", JSON.stringify(user));
      $rootScope.$emit("userChanged");
    };

    this.getUser = function () {
      try {
        return JSON.parse($window.localStorage.getItem("user"));
      } catch (e) {
        return null;
      }
    };

    this.getToken = function () {
      return $window.localStorage.getItem("access_token");
    };

    this.isAuthenticated = function () {
      return !!this.getToken();
    };

    this.logout = function () {
      var refresh = $window.localStorage.getItem("refresh_token");
      var org = this.getOrg();
      $http
        .post(B + "/auth/logout/", { refresh: refresh })
        .finally(function () {
          $window.localStorage.removeItem("access_token");
          $window.localStorage.removeItem("refresh_token");
          $window.localStorage.removeItem("user");
          $rootScope.$emit("userChanged");
          $window.location.href = org ? "#/org/" + org.org_id + "/join" : "#/";
          $window.location.reload();
        });
    };

    // ── Org-Token session (org admin) ─────────────────────────────────────
    this.saveOrgSession = function (org_token, org) {
      if (org_token && org_token !== "null") {
        $window.localStorage.setItem("org_token", org_token);
      }
      if (org) {
        $window.localStorage.setItem("org", JSON.stringify(org));
      }
      $rootScope.$emit("orgChanged");
    };

    this.getOrg = function () {
      try {
        return JSON.parse($window.localStorage.getItem("org"));
      } catch (e) {
        return null;
      }
    };

    this.getOrgToken = function () {
      var t = $window.localStorage.getItem("org_token");
      return t && t !== "null" ? t : null;
    };

    this.isOrgAdmin = function () {
      return !!this.getOrgToken();
    };

    this.orgLogout = function (orgId) {
      $window.localStorage.removeItem("org_token");
      $window.localStorage.removeItem("org");
      $rootScope.$emit("orgChanged");
      $window.location.href = "#/org/" + orgId + "/login";
      $window.location.reload();
    };

    // ── Session conflict detection ────────────────────────────────────────

    /**
     * Returns a description of the currently active session, or null if none.
     * Used by login controllers to block a second login in the same browser.
     *
     * Return shape:
     *   null                        — no active session
     *   { type: 'worker', name, orgId, logoutFn }
     *   { type: 'org',    name, orgId, logoutFn }
     */
    var self = this;

    this.activeSession = function () {
      // Worker JWT session
      if (this.isAuthenticated()) {
        var user = this.getUser();
        var org  = this.getOrg();
        return {
          type    : "worker",
          name    : user ? user.full_name : "a worker",
          orgId   : org  ? org.org_id    : (user && user.org_slug),
          logoutFn: function () { self.logout(); },
        };
      }
      // Org-Token session
      if (this.isOrgAdmin()) {
        var org = this.getOrg();
        return {
          type    : "org",
          name    : org ? org.name : "an organisation",
          orgId   : org ? org.org_id : null,
          logoutFn: function () {
            var id = org ? org.org_id : "";
            self.orgLogout(id);
          },
        };
      }
      return null;
    };

    // ── Helpers ───────────────────────────────────────────────────────────
    this.getOrgId = function () {
      var org  = this.getOrg();
      var user = this.getUser();
      if (org  && org.org_id)   return org.org_id;
      if (user && user.org_slug) return user.org_slug;
      return null;
    };
  },
]);
