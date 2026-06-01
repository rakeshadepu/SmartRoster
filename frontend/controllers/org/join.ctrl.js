"use strict";

angular.module("TimetableApp").controller("OrgJoinCtrl", [
  "$scope",
  "$location",
  "$routeParams",
  "AuthService",
  "ApiService",
  function ($scope, $location, $routeParams, AuthService, ApiService) {
    const orgId = $routeParams.orgId;

    $scope.org          = null;
    $scope.users        = [];
    $scope.loading      = true;
    $scope.error        = null;
    $scope.step         = "select";   // 'blocked' | 'select' | 'password'
    $scope.selectedUser = null;
    $scope.form         = { password: "" };
    $scope.signingIn    = false;
    $scope.search       = "";
    $scope.blockedSession = null;   // holds activeSession() result when blocked

    // ── Session conflict check ─────────────────────────────────────────────
    var existing = AuthService.activeSession();

    if (existing) {
      // Same worker for this org is already logged in — just redirect them
      if (existing.type === "worker" && existing.orgId === orgId) {
        var user = AuthService.getUser();
        $location.path("/org/" + orgId + "/u/" + user.user_id + "/dashboard");
        return;
      }
      // Any other active session (different worker, different org, org admin)
      // → show the blocked screen
      $scope.step           = "blocked";
      $scope.blockedSession = existing;
    }

    // Load org info + worker list (always load, even if blocked, for display)
    ApiService.orgJoinInfo(orgId)
      .then(function (res) {
        $scope.org   = res.data.org;
        $scope.users = res.data.users || [];
      })
      .catch(function () {
        $scope.org   = null;
        if ($scope.step !== "blocked") {
          $scope.error = "Could not load organisation. Check the link you were sent.";
        }
      })
      .finally(function () {
        $scope.loading = false;
      });

    // ── Blocked screen: logout the existing session ─────────────────────
    $scope.logoutExisting = function () {
      if ($scope.blockedSession) {
        $scope.blockedSession.logoutFn();
        // logoutFn calls location.reload() so the page resets automatically
      }
    };

    // ── Filtered user list ────────────────────────────────────────────────
    $scope.filteredUsers = function () {
      if (!$scope.search) return $scope.users;
      var q = $scope.search.toLowerCase();
      return $scope.users.filter(function (u) {
        return u.full_name.toLowerCase().indexOf(q) !== -1;
      });
    };

    // ── Step 1 — pick name ────────────────────────────────────────────────
    $scope.selectUser = function (user) {
      $scope.selectedUser  = user;
      $scope.step          = "password";
      $scope.error         = null;
      $scope.form.password = "";
      setTimeout(function () {
        var el = document.getElementById("passwordInput");
        if (el) el.focus();
      }, 100);
    };

    $scope.backToSelect = function () {
      $scope.step          = "select";
      $scope.selectedUser  = null;
      $scope.error         = null;
      $scope.form.password = "";
      $scope.search        = "";
    };

    // ── Step 2 — sign in ──────────────────────────────────────────────────
    $scope.signIn = function () {
      if (!$scope.form.password || $scope.signingIn) return;
      $scope.signingIn = true;
      $scope.error     = null;

      ApiService.login($scope.selectedUser.user_id, $scope.form.password)
        .then(function (res) {
          var user      = res.data.user;
          user.org_slug = orgId;

          AuthService.saveSession(res.data.tokens, user);

          if ($scope.org) {
            AuthService.saveOrgSession(null, $scope.org);
          }

          $location.path("/org/" + orgId + "/u/" + user.user_id + "/dashboard");
        })
        .catch(function (err) {
          var msg = "Incorrect password. Please try again.";
          if (err && err.data) {
            if (err.data.errors) {
              var e = err.data.errors;
              if (Array.isArray(e))        msg = e.join(" ");
              else if (typeof e === "string") msg = e;
              else if (typeof e === "object") msg = Object.values(e).flat().join(" ");
            } else if (err.data.detail) {
              msg = err.data.detail;
            }
          }
          $scope.error = msg;
        })
        .finally(function () {
          $scope.signingIn = false;
        });
    };
  },
]);
