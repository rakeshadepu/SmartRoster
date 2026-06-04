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

    function loadAll() {
      $scope.loading = true;
      ApiService.orgMe(orgId)
        .then((res) => {
          $scope.org = res.data.organisation;
          AuthService.saveOrgSession(AuthService.getOrgToken(), $scope.org);
          $scope.employees = res.data.employees || [];
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
      ApiService.updateWorker(orgId, $scope.editEmployee.pk, {
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
      ApiService.deleteWorker(orgId, emp.id)
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
      ApiService.resetPassword(orgId, emp.id)
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

    $scope.closeEditModal = function () {
      console.log("clicked")
      $scope.editModal = false;
      $scope.editEmployee = {};
    };

     $scope.testClose = function () {
       // console.log("close clicked");
       $scope.showCreateForm = false;
     };


    $scope.closeResetModal = function () {
      $scope.resetModal = false;
      $scope.resetCred = null;
    };

    $scope.logout = function () {
      AuthService.orgLogout(orgId);
    };
  },
]);
