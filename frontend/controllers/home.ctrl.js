"use strict";

angular.module("TimetableApp").controller("HomeCtrl", [
  "$scope",
  "$location",
  "AuthService",
  "ApiService",
  function ($scope, $location, AuthService, ApiService) {
    $scope.orgIdInput = "";
    $scope.checking = false;
    $scope.error = null;

    // If already logged in, redirect appropriately
    const user = AuthService.getUser();
    const org = AuthService.getOrg();
    if (user && user.org_slug) {
      $location.path(`/org/${user.org_slug}/u/${user.user_id}/dashboard`);
      return;
    }
    if (org && org.org_id) {
      $location.path(`/org/${org.org_id}/dashboard`);
      return;
    }

    $scope.goToOrgLogin = function () {
      const id = ($scope.orgIdInput || "").trim();
      if (id.length !== 8) {
        $scope.error = "Organisation ID must be exactly 8 characters.";
        return;
      }

      $scope.checking = true;
      $scope.error = null;

      // Verify the org exists before navigating
      ApiService.orgPublic(id)
        .then(function () {
          $location.path(`/org/${id}/login`);
        })
        .catch(function () {
          $scope.error = "Organisation not found. Check the ID and try again.";
        })
        .finally(function () {
          $scope.checking = false;
        });
    };

    // Clear error when user types
    $scope.clearError = function () {
      $scope.error = null;
    };
  },
]);
