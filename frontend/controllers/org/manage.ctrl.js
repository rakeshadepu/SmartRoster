"use strict";

/**
 * OrgWorkersCtrl
 * Route: /org/:orgId/manage   (access: org)
 * Manages the worker roster — create, edit, deactivate, reset password.
 * Authenticated via Org-Token (org admin).
 * Backend URLs: /api/org/<orgId>/workers/  and  /api/org/<orgId>/<workerUserId>/
 */
angular.module("TimetableApp").controller("OrgWorkersCtrl", [
  "$scope",
  "$routeParams",
  "AuthService",
  "ApiService",
  function ($scope, $routeParams, AuthService, ApiService) {
    const orgId = $routeParams.orgId;

    $scope.orgId = orgId;
    $scope.org = AuthService.getOrg();
    $scope.workers = [];
    $scope.loading = true;
    $scope.error = null;
    $scope.success = null;
    $scope.newWorker = { full_name: "", work_type: "FULL_TIME" };
    $scope.showCreateForm = false;
    $scope.creating = false;
    $scope.createdCred = null;
    $scope.editModal = false;
    $scope.editWorker = {};
    $scope.resetModal = false;
    $scope.resetCred = null;
    $scope.filter = { work_type: "", is_active: "" };

    // Email conflict state
    $scope.emailConflicts = [];
    $scope.conflictModal = false;
    $scope.conflictWorker = null;
    $scope.conflictNewEmail = "";
    $scope.conflictSaving = false;
    $scope.conflictError = null;

    function loadWorkers() {
      $scope.loading = true;
      $scope.error = null;
      var params = {};
      if ($scope.filter.work_type) params.work_type = $scope.filter.work_type;
      if ($scope.filter.is_active !== "")
        params.is_active = $scope.filter.is_active;
      ApiService.listWorkers(orgId, params)
        .then(function (res) {
          $scope.workers = res.data.workers || [];
        })
        .catch(function (err) {
          if (err && err.status === 401) {
            // Interceptor will redirect to org login — don't double-navigate
            return;
          }
          $scope.error = "Failed to load workers. Please refresh the page.";
        })
        .finally(function () {
          $scope.loading = false;
        });
    }

    function loadConflicts() {
      ApiService.getEmailConflicts(orgId)
        .then(function (res) {
          $scope.emailConflicts = res.data.conflicts || [];
        })
        .catch(function (err) {
          // 401 means session expired — the interceptor handles redirect.
          // For any other error, silently skip conflict display (non-critical).
          if (err && err.status !== 401) {
            console.warn("Email conflict check failed:", err.status);
          }
        });
    }

    loadWorkers();
    loadConflicts();
    $scope.applyFilter = loadWorkers;

    $scope.createWorker = function () {
      if (!$scope.newWorker.full_name.trim()) return;
      $scope.creating = true;
      $scope.error = null;
      $scope.createdCred = null;

      ApiService.createWorker(orgId, $scope.newWorker)
        .then(function (res) {
          var w = res.data.worker;
          $scope.createdCred = {
            name: w.full_name,
            user_id: w.user_id,
            password: w.plain_password,
            work_type: w.work_type,
            join_url: window.location.origin + "/#/org/" + orgId + "/join",
          };
          $scope.newWorker = { full_name: "", work_type: "FULL_TIME" };
          $scope.showCreateForm = false;
          loadWorkers();
        })
        .catch(function (err) {
          $scope.error =
            err.data && err.data.errors
              ? JSON.stringify(err.data.errors)
              : "Failed to create worker.";
        })
        .finally(function () {
          $scope.creating = false;
        });
    };

    $scope.openEdit = function (worker) {
      $scope.editWorker = {
        user_id: worker.user_id,
        full_name: worker.full_name,
        work_type: worker.work_type,
        is_active: worker.is_active,
        email: worker.email || "",
      };
      $scope.editModal = true;
      $scope.error = null;
    };

    $scope.saveEdit = function () {
      var payload = {
        full_name: $scope.editWorker.full_name,
        work_type: $scope.editWorker.work_type,
        is_active: $scope.editWorker.is_active,
      };
      if ($scope.editWorker.email !== undefined) {
        payload.email = $scope.editWorker.email;
      }
      ApiService.updateWorker(orgId, $scope.editWorker.user_id, payload)
        .then(function () {
          $scope.editModal = false;
          $scope.success = "Worker updated.";
          loadWorkers();
          loadConflicts();
          setTimeout(function () {
            $scope.$apply(function () {
              $scope.success = null;
            });
          }, 3000);
        })
        .catch(function (err) {
          $scope.error =
            err.data && err.data.errors
              ? JSON.stringify(err.data.errors)
              : "Update failed.";
        });
    };

    // Open the conflict-resolution modal for a specific conflict
    $scope.openConflictFix = function (conflict) {
      $scope.conflictWorker = conflict;
      $scope.conflictNewEmail = "";
      $scope.conflictError = null;
      $scope.conflictModal = true;
    };

    $scope.saveConflictEmail = function () {
      if ($scope.conflictNewEmail.trim()) {
        $scope.conflictError = "Please enter a new email address.";
        console.log("nothing")
        return;
      }
      console.log("something")
      $scope.conflictSaving = true;
      $scope.conflictError = null;
      ApiService.updateWorkerEmail(
        orgId,
        $scope.conflictWorker.user_id,
        $scope.conflictNewEmail.trim(),
      )
        .then(function () {
          $scope.conflictModal = false;
          $scope.conflictWorker = null;
          $scope.success = "Worker email updated. Conflict resolved.";
          loadWorkers();
          loadConflicts();
          setTimeout(function () {
            $scope.$apply(function () {
              $scope.success = null;
            });
          }, 4000);
        })
        .catch(function (err) {
          $scope.conflictError =
            err.data && err.data.errors && err.data.errors.email
              ? err.data.errors.email[0]
              : "Failed to update email. Please try a different address.";
        })
        .finally(function () {
          $scope.conflictSaving = false;
        });
    };

    $scope.deactivate = function (worker) {
      if (!confirm("Deactivate " + worker.full_name + "?")) return;
      ApiService.deleteWorker(orgId, worker.user_id)
        .then(function () {
          $scope.success = worker.full_name + " deactivated.";
          loadWorkers();
          setTimeout(function () {
            $scope.$apply(function () {
              $scope.success = null;
            });
          }, 3000);
        })
        .catch(function () {
          $scope.error = "Failed to deactivate.";
        });
    };

    $scope.resetPassword = function (worker) {
      if (!confirm("Reset password for " + worker.full_name + "?")) return;
      ApiService.resetPassword(orgId, worker.user_id)
        .then(function (res) {
          $scope.resetCred = {
            name: worker.full_name,
            user_id: res.data.user_id,
            password: res.data.new_password,
          };
          $scope.resetModal = true;
        })
        .catch(function () {
          $scope.error = "Password reset failed.";
        });
    };

    $scope.copyText = function (text, $event) {
      navigator.clipboard.writeText(text);
      var btn = $event.target;
      btn.textContent = "Copied!";
      btn.classList.add("copied");
      setTimeout(function () {
        btn.textContent = "Copy";
        btn.classList.remove("copied");
      }, 2000);
    };

    $scope.testClose = function () {
      // console.log("close clicked");
      $scope.showCreateForm = false;
    };

    $scope.closeConflictModal = function () {
      $scope.conflictModal = false;
      $scope.conflictWorker = null;
      $scope.conflictNewEmail = "";
      $scope.conflictError = null;
    };

    $scope.logout = function () {
      AuthService.orgLogout(orgId);
    };
  },
]);
