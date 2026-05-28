"use strict";

angular.module("TimetableApp").controller("OrgDashboardCtrl", [
  "$scope",
  "$location",
  "$routeParams",
  "AuthService",
  "ApiService",
  function ($scope, $location, $routeParams, AuthService, ApiService) {
    const orgId = $routeParams.orgId;
    $scope.orgId = orgId;
    $scope.org = AuthService.getOrg();
    $scope.employees = [];
    $scope.loading = true;
    $scope.error = null;
    $scope.success = null;

    $scope.showForm = false;
    $scope.creating = false;
    $scope.newEmpName = "";
    $scope.createdCred = null;

    $scope.editModal = false;
    $scope.editEmployee = {};

    $scope.resetModal = false;
    $scope.resetCred = null;

    $scope.showSettings = false;
    $scope.settingsForm = {
      name: $scope.org ? $scope.org.name : "",
      shop_open: $scope.org
        ? ($scope.org.shop_open || "").slice(0, 5)
        : "08:00",
      shop_close: $scope.org
        ? ($scope.org.shop_close || "").slice(0, 5)
        : "18:00",
      email: $scope.org ? $scope.org.email : "",
      password: "",
      confirm_pw: "",
    };

    function loadAll() {
      $scope.loading = true;
      ApiService.orgMe(orgId)
        .then((res) => {
          $scope.org = res.data.organisation;
          AuthService.saveOrgSession(AuthService.getOrgToken(), $scope.org);
          $scope.employees = res.data.employees || [];
          $scope.settingsForm.name = $scope.org.name;
          $scope.settingsForm.shop_open = ($scope.org.shop_open || "").slice(
            0,
            5,
          );
          $scope.settingsForm.shop_close = ($scope.org.shop_close || "").slice(
            0,
            5,
          );
          $scope.settingsForm.email = $scope.org.email;
        })
        .catch(() => {
          $scope.error = "Session expired. Please log in again.";
          setTimeout(() => AuthService.orgLogout(orgId), 2000);
        })
        .finally(() => {
          $scope.loading = false;
        });
    }

    loadAll();

    $scope.createEmployee = function () {
      if (!$scope.newEmpName.trim()) return;
      $scope.creating = true;
      $scope.error = null;
      $scope.createdCred = null;

      ApiService.orgCreateEmployee(orgId, { full_name: $scope.newEmpName })
        .then((res) => {
          $scope.createdCred = res.data.employee;
          $scope.newEmpName = "";
          $scope.showForm = false;
          loadAll();
        })
        .catch((err) => {
          $scope.error =
            err.data && err.data.error
              ? err.data.error
              : "Failed to create employee.";
        })
        .finally(() => {
          $scope.creating = false;
        });
    };

    $scope.openEdit = function (emp) {
      $scope.editEmployee = {
        pk: emp.id,
        full_name: emp.full_name,
        is_active: emp.is_active,
      };
      $scope.editModal = true;
      $scope.error = null;
    };

    $scope.saveEdit = function () {
      ApiService.orgUpdateEmployee(orgId, $scope.editEmployee.pk, {
        full_name: $scope.editEmployee.full_name,
        is_active: $scope.editEmployee.is_active,
      })
        .then(() => {
          $scope.editModal = false;
          $scope.success = "Employee updated.";
          loadAll();
          setTimeout(() => {
            $scope.$apply(() => {
              $scope.success = null;
            });
          }, 3000);
        })
        .catch(() => {
          $scope.error = "Update failed.";
        });
    };

    $scope.deactivate = function (emp) {
      if (!confirm(`Deactivate ${emp.full_name}?`)) return;
      ApiService.orgDeleteEmployee(orgId, emp.id)
        .then(() => {
          $scope.success = `${emp.full_name} deactivated.`;
          loadAll();
          setTimeout(() => {
            $scope.$apply(() => {
              $scope.success = null;
            });
          }, 3000);
        })
        .catch(() => {
          $scope.error = "Deactivate failed.";
        });
    };

    $scope.resetPassword = function (emp) {
      if (!confirm(`Reset password for ${emp.full_name}?`)) return;
      ApiService.orgResetEmpPw(orgId, emp.id)
        .then((res) => {
          $scope.resetCred = {
            user_id: res.data.user_id,
            password: res.data.new_password,
          };
          $scope.resetModal = true;
        })
        .catch(() => {
          $scope.error = "Reset failed.";
        });
    };

    $scope.saveSettings = function () {
      $scope.error = null;
      const payload = {
        name: $scope.settingsForm.name,
        shop_open: $scope.settingsForm.shop_open,
        shop_close: $scope.settingsForm.shop_close,
        email: $scope.settingsForm.email,
      };
      if ($scope.settingsForm.password) {
        if ($scope.settingsForm.password !== $scope.settingsForm.confirm_pw) {
          $scope.error = "Passwords do not match.";
          return;
        }
        payload.password = $scope.settingsForm.password;
      }
      ApiService.orgUpdate(orgId, payload)
        .then((res) => {
          $scope.success = "Settings saved.";
          $scope.showSettings = false;
          $scope.org = res.data.organisation;
          AuthService.saveOrgSession(AuthService.getOrgToken(), $scope.org);
          $scope.settingsForm.password = "";
          $scope.settingsForm.confirm_pw = "";
          setTimeout(() => {
            $scope.$apply(() => {
              $scope.success = null;
            });
          }, 3000);
        })
        .catch((err) => {
          $scope.error =
            err.data && err.data.error ? err.data.error : "Save failed.";
        });
    };

    $scope.copyText = function (text, $event) {
      navigator.clipboard.writeText(text);
      const btn = $event.target;
      btn.textContent = "Copied!";
      btn.classList.add("copied");
      setTimeout(() => {
        btn.textContent = "Copy";
        btn.classList.remove("copied");
      }, 2000);
    };

    $scope.logout = function () {
      AuthService.orgLogout(orgId);
    };
  },
]);
