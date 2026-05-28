"use strict";

angular.module("TimetableApp").controller("OrgLoginCtrl", [
  "$scope",
  "$location",
  "$routeParams",
  "AuthService",
  "ApiService",
  function ($scope, $location, $routeParams, AuthService, ApiService) {
    const orgId = $routeParams.orgId;
    $scope.orgId = orgId;
    $scope.org = null;
    $scope.loading = false;
    $scope.error = null;

    // identifier accepts email OR org_id
    $scope.form = { identifier: "", password: "" };

    // Pre-fill identifier with orgId if it looks like a real org_id (8 chars)
    if (orgId && orgId.length === 8) {
      $scope.form.identifier = orgId;
    }

    // Redirect if already logged in as org admin for this org
    if (AuthService.isOrgAdmin()) {
      const existing = AuthService.getOrg();
      if (existing && existing.org_id === orgId) {
        $location.path("/org/" + orgId + "/dashboard");
        return;
      }
    }

    // Load org public info (show name on the form)
    if (orgId) {
      ApiService.orgPublic(orgId)
        .then(function (res) {
          $scope.org = res.data.org;
        })
        .catch(function () {
          // Org not found by URL — still allow login by email
          $scope.org = null;
        });
    }

    // Detect what the user typed so we can show a contextual label
    $scope.identifierType = function () {
      const v = ($scope.form.identifier || "").trim();
      if (!v) return null;
      if (v.indexOf("@") !== -1) return "email";
      if (v.length === 8) return "orgid";
      if (v.length > 0 && v.length < 8) return "typing";
      return null;
    };

    $scope.login = function () {
      $scope.error = null;
      $scope.loading = true;

      // Use scoped login if we have an orgId, else global login
      var loginPromise = orgId
        ? ApiService.orgLogin(
            orgId,
            $scope.form.identifier,
            $scope.form.password,
          )
        : ApiService.orgLoginGlobal(
            $scope.form.identifier,
            $scope.form.password,
          );

      loginPromise
        .then(function (res) {
          var org = res.data.organisation;
          AuthService.saveOrgSession(res.data.org_token, org);
          $location.path("/org/" + org.org_id + "/dashboard");
        })
        .catch(function (err) {
          var e = err.data && (err.data.errors || err.data.error);
          if (Array.isArray(e)) $scope.error = e.join(" ");
          else if (typeof e === "string") $scope.error = e;
          else if (e && typeof e === "object")
            $scope.error = Object.values(e).flat().join(" ");
          else $scope.error = "Invalid credentials. Try again.";
        })
        .finally(function () {
          $scope.loading = false;
        });
    };
  },
]);
