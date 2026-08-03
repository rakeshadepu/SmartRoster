"use strict";

angular.module("TimetableApp").controller("OrgWorkersCtrl", [
  "$scope",
  "$rootScope",
  "$routeParams",
  "AuthService",
  "ApiService",
  function ($scope, $rootScope, $routeParams, AuthService, ApiService) {
    const orgId = $routeParams.orgId;

    $scope.orgId = orgId;
    $scope.org = AuthService.getOrg();
    $scope.workers = [];
    $scope.loading = true;
    $scope.error = null;
    $scope.success = null;
    $scope.showCreateForm = false;
    $scope.editModeWorker = null; // set when opening edit vs add
    $scope.createdCred = null;
    $scope.resetModal = false;
    $scope.resetCred = null;
    $scope.filter = { work_type: "", is_active: "" };
    $scope.sortBy = "joined_at"; // default: newest joined first
    $scope.sortDesc = true;

    // Email conflict state
    $scope.emailConflicts = [];
    $scope.conflictModal = false;
    $scope.conflictWorker = null;
    $scope.conflictNewEmail = "";
    $scope.conflictSaving = false;
    $scope.conflictError = null;

    // Change-password modal state
    $scope.changePassModal = false;
    $scope.changePassWorker = null;
    $scope.changePassForm = {
      current_password: "",
      new_password: "",
      confirm_password: "",
    };
    $scope.changePassError = null;
    $scope.changePassSaving = false;

    // ── Sort state ────────────────────────────────────────────────────────────
    $scope.setSort = function (field) {
      if ($scope.sortBy === field) {
        $scope.sortDesc = !$scope.sortDesc; // toggle direction
      } else {
        $scope.sortBy = field;
        $scope.sortDesc = field === "joined_at"; // dates default desc, names default asc
      }
    };

    $scope.sortIcon = function (field) {
      if ($scope.sortBy !== field) return "⇅";
      return $scope.sortDesc ? "↓" : "↑";
    };

    // ── workTypeBadge helper ──────────────────────────────────────────────────
    $scope.workTypeBadge = function (wt) {
      return {
        "badge-green": wt === "FULL_TIME",
        "badge-blue": wt === "PART_TIME",
        "badge-yellow": wt === "MINIJOB",
      };
    };

    // ── roleBadge helper ──────────────────────────────────────────────────────
    $scope.roleBadge = function (role) {
      return {
        "badge-purple": role === "ADMIN",
        "badge-blue": role === "MANAGER",
        "badge-gray": role === "WORKER",
      };
    };

    // ── Load ─────────────────────────────────────────────────────────────────
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
          if (err && err.status === 401) return;
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
          if (err && err.status !== 401) {
            console.warn("Email conflict check failed:", err.status);
          }
        });
    }

    loadWorkers();
    loadConflicts();
    $scope.applyFilter = loadWorkers;

    // ── Open ADD form (fresh) ─────────────────────────────────────────────────
    $scope.openAddWorker = function () {
      $scope.editModeWorker = null;
      // Broadcast null so AddUserCtrl resets itself
      $rootScope.$broadcast("editWorkerData", null);
      $scope.showCreateForm = true;
    };

    // ── Open EDIT form (pre-filled, no password fields) ───────────────────────
    $scope.openEdit = function (worker) {
      $scope.editModeWorker = worker;
      // Broadcast worker data; AddUserCtrl will receive and pre-fill
      $rootScope.$broadcast("editWorkerData", {
        user_id: worker.user_id,
        first_name: worker.full_name.split(" ")[0] || "",
        last_name: worker.full_name.split(" ").slice(1).join(" ") || "",
        email: worker.email || "",
        employee_code: worker.employee_code || "",
        role: worker.role || "WORKER",
        work_type: worker.work_type || "FULL_TIME",
        // phone/dob/nationality may not be returned by list endpoint;
        // pass what we have — AddUserCtrl will fill the rest as empty
        phone: worker.phone || "",
        nationality: worker.nationality || "",
        dob: worker.dob || "",
        iban: worker.iban || "",
        bic: worker.bic || "",
        house_number: worker.house_number || "",
        street: worker.street || "",
        city: worker.city || "",
        country: worker.country || "",
        zip_code: worker.zip_code || "",
      });
      $scope.showCreateForm = true;
    };

    // Called by AddUserCtrl after a successful save (add or edit)
    $scope.$on("workerSaved", function (evt, cred) {
      $scope.showCreateForm = false;
      $scope.editModeWorker = null;
      if (cred) {
        // New worker — show credentials banner on the main page
        $scope.createdCred = cred;
      } else {
        // Edit — just show a success message
        $scope.success = "Worker updated successfully.";
        setTimeout(function () {
          $scope.$apply(function () {
            $scope.success = null;
          });
        }, 3000);
      }
      loadWorkers();
      loadConflicts();
    });

    $scope.dismissCred = function () {
      $scope.createdCred = null;
    };
    
    // Called by AddUserCtrl when user hits Cancel / close
    $scope.$on("closeAddWorkerForm", function () {
      $scope.showCreateForm = false;
      $scope.editModeWorker = null;
    });

    // ── Change Password modal ─────────────────────────────────────────────────
    $scope.openChangePassword = function (worker) {
      $scope.changePassWorker = worker;
      $scope.changePassForm = {
        current_password: "",
        new_password: "",
        confirm_password: "",
      };
      $scope.changePassError = null;
      $scope.changePassModal = true;
    };

    $scope.saveChangePassword = function () {
      var f = $scope.changePassForm;
      if (!f.current_password || !f.new_password || !f.confirm_password) {
        $scope.changePassError = "All fields are required.";
        return;
      }
      if (f.new_password !== f.confirm_password) {
        $scope.changePassError = "New password and confirmation do not match.";
        return;
      }
      if (f.new_password.length < 6) {
        $scope.changePassError = "New password must be at least 6 characters.";
        return;
      }
      $scope.changePassSaving = true;
      $scope.changePassError = null;

      ApiService.changeWorkerPassword(orgId, $scope.changePassWorker.user_id, {
        current_password: f.current_password,
        new_password: f.new_password,
      })
        .then(function () {
          $scope.changePassModal = false;
          $scope.success = "Password changed successfully.";
          setTimeout(function () {
            $scope.$apply(function () {
              $scope.success = null;
            });
          }, 3000);
        })
        .catch(function (err) {
          $scope.changePassError =
            err.data && err.data.error
              ? err.data.error
              : "Failed to change password. Check the current password and try again.";
        })
        .finally(function () {
          $scope.changePassSaving = false;
        });
    };

    $scope.closeChangePassModal = function () {
      $scope.changePassModal = false;
      $scope.changePassWorker = null;
      $scope.changePassError = null;
    };

    // ── Reset password (admin generates new one) ──────────────────────────────
    $scope.resetPassword = function (worker) {
      if (
        !confirm(
          "Reset password for " +
            worker.full_name +
            "? A new password will be generated.",
        )
      )
        return;
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

    // ── Delete worker ─────────────────────────────────────────────────────────
    $scope.deactivate = function (worker) {
      if (
        !confirm(
          "Delete " +
            worker.full_name +
            " from this organisation? This cannot be undone.",
        )
      )
        return;
      ApiService.deleteWorker(orgId, worker.user_id)
        .then(function () {
          $scope.success = worker.full_name + " deleted.";
          loadWorkers();
          setTimeout(function () {
            $scope.$apply(function () {
              $scope.success = null;
            });
          }, 3000);
        })
        .catch(function () {
          $scope.error = "Delete failed.";
        });
    };

    // ── Email conflict resolution ─────────────────────────────────────────────
    $scope.openConflictFix = function (conflict) {
      $scope.conflictWorker = conflict;
      $scope.conflictNewEmail = "";
      $scope.conflictError = null;
      $scope.conflictModal = true;
    };

    $scope.saveConflictEmail = function () {
      if (!$scope.conflictNewEmail.trim()) {
        // ← bug was inverted
        $scope.conflictError = "Please enter a new email address.";
        return;
      }
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

    $scope.closeConflictModal = function () {
      $scope.conflictModal = false;
      $scope.conflictWorker = null;
      $scope.conflictNewEmail = "";
      $scope.conflictError = null;
    };

    // ── Misc ──────────────────────────────────────────────────────────────────
    $scope.copyText = function (text, $event) {
      const btn = $event.target;

      function showCopied() {
        btn.textContent = "Copied!";
        btn.classList.add("copied");

        setTimeout(function () {
          btn.textContent = "Copy";
          btn.classList.remove("copied");
        }, 2000);
      }

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard
          .writeText(text)
          .then(showCopied)
          .catch(function (err) {
            console.error("Clipboard write failed:", err);
          });
      } else {
        // Fallback for browsers without Clipboard API
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";

        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        try {
          document.execCommand("copy");
          showCopied();
        } catch (err) {
          console.error("Fallback copy failed:", err);
          alert("Unable to copy automatically. Please copy manually.");
        }

        document.body.removeChild(textarea);
      }
    };

    $scope.testClose = function () {
      $scope.showCreateForm = false;
      $scope.editModeWorker = null;
    };

    $scope.logout = function () {
      AuthService.orgLogout(orgId);
    };
  },
]);
