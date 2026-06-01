"use strict";

angular.module("TimetableApp").controller("OrgLoginCtrl", [
  "$scope",
  "$location",
  "$routeParams",
  "AuthService",
  "ApiService",
  function ($scope, $location, $routeParams, AuthService, ApiService) {
    const orgId = $routeParams.orgId;

    $scope.orgId          = orgId;
    $scope.org            = null;
    $scope.loading        = false;
    $scope.error          = null;
    $scope.blocked        = false;
    $scope.blockedSession = null;
    $scope.form           = { identifier: "", password: "" };

    // Pre-fill identifier with orgId if it looks like a real org_id (8 chars)
    if (orgId && orgId.length === 8) {
      $scope.form.identifier = orgId;
    }

    // ── Session conflict check ──────────────────────────────────────────
    var existing = AuthService.activeSession();

    if (existing) {
      // Same org admin already logged in — redirect straight to dashboard
      if (existing.type === "org" && existing.orgId === orgId) {
        $location.path("/org/" + orgId + "/dashboard");
        return;
      }
      // Any other active session → block
      $scope.blocked        = true;
      $scope.blockedSession = existing;
    }

    // Load org public info (show name on the form)
    if (orgId) {
      ApiService.orgPublic(orgId)
        .then(function (res) { $scope.org = res.data.org; })
        .catch(function ()   { $scope.org = null; });
    }

    // ── Blocked screen: logout existing session ─────────────────────────
    $scope.logoutExisting = function () {
      if ($scope.blockedSession) {
        $scope.blockedSession.logoutFn();
        // logoutFn calls location.reload() — page resets automatically
      }
    };

    // ── Login ────────────────────────────────────────────────────────────
    $scope.identifierType = function () {
      var v = ($scope.form.identifier || "").trim();
      if (!v)              return null;
      if (v.indexOf("@") !== -1) return "email";
      if (v.length === 8)  return "orgid";
      if (v.length > 0 && v.length < 8) return "typing";
      return null;
    };

    $scope.login = function () {
      // Double-check at submit time — another tab might have created a session
      var session = AuthService.activeSession();
      if (session && !(session.type === "org" && session.orgId === orgId)) {
        $scope.blocked        = true;
        $scope.blockedSession = session;
        return;
      }

      $scope.error   = null;
      $scope.loading = true;

      var loginPromise = orgId
        ? ApiService.orgLogin(orgId, $scope.form.identifier, $scope.form.password)
        : ApiService.orgLoginGlobal($scope.form.identifier, $scope.form.password);

      loginPromise
        .then(function (res) {
          var org = res.data.organisation;
          AuthService.saveOrgSession(res.data.org_token, org);
          $location.path("/org/" + org.org_id + "/dashboard");
        })
        .catch(function (err) {
          var e = err.data && (err.data.errors || err.data.error);
          if (Array.isArray(e))          $scope.error = e.join(" ");
          else if (typeof e === "string") $scope.error = e;
          else if (e && typeof e === "object") $scope.error = Object.values(e).flat().join(" ");
          else                            $scope.error = "Invalid credentials. Try again.";
        })
        .finally(function () {
          $scope.loading = false;
        });
    };
  },
]);
