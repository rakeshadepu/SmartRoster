"use strict";

angular.module("TimetableApp").controller("OrgJoinCtrl", [
  "$scope",
  "$location",
  "$routeParams",
  "AuthService",
  "ApiService",
  function ($scope, $location, $routeParams, AuthService, ApiService) {
    const orgId = $routeParams.orgId;

    $scope.org       = null;
    $scope.users     = [];   // all active users — employees + workers combined
    $scope.loading   = true;
    $scope.error     = null;
    $scope.step      = "select";  // 'select' | 'password'
    $scope.selectedUser = null;
    $scope.form = {
      password: "",
    };
    $scope.signingIn = false;
    $scope.search    = "";

    // Load org info + user list
    // Backend: GET /api/org/<org_id>/join/  (no auth required — AllowAny)
    ApiService.orgJoinInfo(orgId)
      .then(function (res) {
        $scope.org   = res.data.org;
        $scope.users = res.data.users || [];
      })
      .catch(function (err) {
        $scope.org   = null;
        $scope.error = "Could not load organisation. Check the link you were sent.";
      })
      .finally(function () {
        $scope.loading = false;
      });

    // Filtered user list based on search input
    $scope.filteredUsers = function () {
      if (!$scope.search) return $scope.users;
      var q = $scope.search.toLowerCase();
      return $scope.users.filter(function (u) {
        return u.full_name.toLowerCase().indexOf(q) !== -1;
      });
    };

    // Step 1 — user picks their name from the list
    $scope.selectUser = function (user) {
      $scope.selectedUser = user;
      $scope.step         = "password";
      $scope.error        = null;
      $scope.form.password     = "";
      setTimeout(function () {
        var el = document.getElementById("passwordInput");
        console.log(el)
        if (el) el.focus();
      }, 100);
    };

    $scope.backToSelect = function () {
      $scope.step         = "select";
      $scope.selectedUser = null;
      $scope.error        = null;
      $scope.form.password     = "";
      $scope.search       = "";
    };

    // Step 2 — POST /api/auth/login/ with { user_id, password }
    // This endpoint is AllowAny — interceptor sends NO Authorization header.
    $scope.signIn = function () {

      console.log("password:", $scope.form.password);
      console.log("signingIn:", $scope.signingIn);

      if (!$scope.form.password || $scope.signingIn) {
        console.log("Blocked by condition");
        return;
      }

      console.log("Proceeding with login");
      // if (!$scope.password || $scope.signingIn) return;
      // console.log("clicked")
      // $scope.signingIn = true;
      // $scope.error     = null;

      ApiService.login($scope.selectedUser.user_id, $scope.form.password)
        .then(function (res) {
          var user = res.data.user;
          console.log(user)
          user.org_slug = orgId;   // stash org_id on the user for later path-building

          // Save JWT tokens + user profile
          AuthService.saveSession(res.data.tokens, user);

          // Save org context (for sidebar display) WITHOUT storing an org_token.
          // Passing null here is safe: saveOrgSession now guards against storing "null".
          if ($scope.org) {
            AuthService.saveOrgSession(null, $scope.org);
          }

          // Redirect to dashboard — route guard handles role-based sub-routing
          var userId = user.user_id;
          $location.path("/org/" + orgId + "/u/" + userId + "/dashboard");
        })
        .catch(function (err) {
          // Surface the actual error from the backend if available
          var msg = "Incorrect password. Please try again.";
          if (err && err.data) {
            if (err.data.errors) {
              var e = err.data.errors;
              if (Array.isArray(e)) msg = e.join(" ");
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
