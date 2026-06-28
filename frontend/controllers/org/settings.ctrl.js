"use strict";

/**
 * OrgSettingsCtrl
 * Route: /org/:orgId/settings   (access: org)
 * Manages org info, shop hours and work type weekly hour limits.
 * Authenticated via Org-Token (org admin).
 * Backend URLs: /api/org/<orgId>/settings/  and  /api/work-limits/
 */
angular.module("TimetableApp").controller("OrgSettingsCtrl", [
  "$scope",
  "$rootScope",
  "$routeParams",
  "AuthService",
  "ApiService",
  function ($scope, $rootScope, $routeParams, AuthService, ApiService) {
    const orgId = $routeParams.orgId;

    $scope.orgId = orgId;
    $scope.org = AuthService.getOrg();
    $scope.limits = [];
    $scope.loading = true;
    $scope.saving = false;
    $scope.error = null;
    $scope.shopForm = { shop_open: "", shop_close: "" };
    $scope.limitsForm = { FULL_TIME: 40, PART_TIME: 20, MINIJOB: 10 };
    $scope.settingsForm = {
      name: "",
      email: "",
      password: "",
      confirm_pw: "",
    };

    // ── Toast ─────────────────────────────────────────────────────────────────

    function showToast(message) {
      $scope.settingsToastMsg  = message;
      $scope.showSettingsToast = true;

      setTimeout(function() {
        $scope.$apply(function() {
          $scope.showSettingsToast = false;
          $scope.settingsToastMsg  = '';
        });
      }, 2500);
    }

    function showErrorToast(message) {
      $scope.errorToastMsg  = message;
      $scope.showErrorToast = true;

      setTimeout(function() {
        $scope.$apply(function() {
          $scope.showErrorToast = false;
          $scope.errorToastMsg  = '';
        });
      }, 3000);
    }

    function load() {
      ApiService.orgSettings(orgId).then(function (res) {
        // ← was getOrg
        $scope.org = res.data.organisation;
        $scope.shopForm.shop_open = ($scope.org.shop_open || "").slice(0, 5);
        $scope.shopForm.shop_close = ($scope.org.shop_close || "").slice(0, 5);
        $scope.settingsForm.name = $scope.org.name || "";
        $scope.settingsForm.email = $scope.org.email || "";
        AuthService.saveOrgSession(AuthService.getOrgToken(), $scope.org);
      });

      ApiService.getLimits()
        .then(function (res) {
          $scope.limits = res.data.limits || [];
          $scope.limits.forEach(function (l) {
            $scope.limitsForm[l.work_type] = l.hours_per_week;
          });
        })
        .finally(function () {
          $scope.loading = false;
        });
    }

    load();

    $scope.updateName = function () {
      if (!$scope.settingsForm.name || !$scope.settingsForm.name.trim()) {
        showErrorToast("Organisation name cannot be empty.");
        return;
      }
      ApiService.orgUpdate(orgId, { name: $scope.settingsForm.name.trim() }) // ← was updateOrg
        .then(function (res) {
          $scope.org = res.data.organisation;
          AuthService.saveOrgSession(AuthService.getOrgToken(), $scope.org);
          showToast("Organisation name updated.");
        })
        .catch(function (err) {
          showErrorToast(
            err.data && err.data.error
              ? err.data.error
              : "Failed to update organisation name.",
          );
        });
    };

    $scope.updateEmail = function () {
      if (!$scope.settingsForm.email || !$scope.settingsForm.email.trim()) {
        showErrorToast("Email cannot be empty.");
        return;
      }
      ApiService.orgUpdate(orgId, { email: $scope.settingsForm.email.trim() }) // ← was updateOrg
        .then(function (res) {
          $scope.org = res.data.organisation;
          AuthService.saveOrgSession(AuthService.getOrgToken(), $scope.org);
          showToast("Admin email updated.");
        })
        .catch(function (err) {
          showErrorToast(
            err.data && err.data.error
              ? err.data.error
              : "Failed to update email.",
          );
        });
    };

    $scope.updatePassword = function () {
      if (!$scope.settingsForm.password) {
        showErrorToast("Please enter a new password.");
        return;
      }
      if ($scope.settingsForm.password !== $scope.settingsForm.confirm_pw) {
        showErrorToast("Passwords do not match.");
        return;
      }
      ApiService.orgUpdate(orgId, { password: $scope.settingsForm.password }) // ← was updateOrg
        .then(function () {
          $scope.settingsForm.password = "";
          $scope.settingsForm.confirm_pw = "";
          showToast("Password updated successfully.");
        })
        .catch(function (err) {
          showErrorToast(
            err.data && err.data.error
              ? err.data.error
              : "Failed to update password.",
          );
        });
    };

    $scope.saveShopHours = function () {
      $scope.saving = true;
      ApiService.orgUpdate(orgId, $scope.shopForm) // ← was updateOrg
        .then(function (res) {
          $scope.org = res.data.organisation;
          showToast("Shop hours updated.");
        })
        .catch(function (err) {
          showErrorToast(
            err.data && err.data.errors
              ? JSON.stringify(err.data.errors)
              : "Failed to save shop hours.",
          );
        })
        .finally(function () {
          $scope.saving = false;
        });
    };

    // ── Update Weekly Limit ───────────────────────────────────────────────────

    $scope.saveLimit = function (workType) {


      ApiService.setLimit({
        work_type: workType,
        hours_per_week: $scope.limitsForm[workType],
      })
        .then(function () {
          load();
          showToast(workType.replace("_", " ") + " limit saved.");
        })
        .catch(function (err) {
          showErrorToast(
            err.data && err.data.errors
              ? JSON.stringify(err.data.errors)
              : "Failed to update limit.",
          );
        });
    };

    $scope.logout = function () {
      AuthService.orgLogout(orgId);
    };
  },
]);
