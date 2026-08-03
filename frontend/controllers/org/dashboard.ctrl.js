"use strict";

angular.module("TimetableApp").controller("OrgDashboardCtrl", [
  "$scope",
  "$routeParams",
  "AuthService",
  "ApiService",
  function ($scope, $routeParams, AuthService, ApiService) {
    const orgId = $routeParams.orgId;
    $scope.orgId = orgId;
    $scope.org = AuthService.getOrg();
    $scope.employees = [];
    $scope.loading = true;
    $scope.error = null;
    $scope.success = null;
    $scope.createdCred = null;
    $scope.showCreateForm = false;
    $scope.expandedId = null; // tracks which row is open

    $scope.jobHistories = {}; // keyed by user_id
    $scope.historyLoading = {}; // keyed by user_id

    const DAY_CODES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

    // business_hours is now a per-day-of-week array (BusinessHours model)
    // instead of a flat shop_open/shop_close pair on the org itself.
    $scope.todayHours = function () {
      if (!$scope.org || !$scope.org.business_hours) return null;
      const todayCode = DAY_CODES[new Date().getDay() === 0 ? 6 : new Date().getDay() - 1];
      return $scope.org.business_hours.find((d) => d.day_of_week === todayCode) || null;
    };

    $scope.toggleExpand = function (userId) {
      if ($scope.expandedId === userId) {
        $scope.expandedId = null;
        return;
      }
      $scope.expandedId = userId;

      // Only fetch if not already loaded
      if ($scope.jobHistories[userId]) return;

      $scope.historyLoading[userId] = true;
      ApiService.getWorkerHistory(orgId, userId)
        .then(function (res) {
          $scope.jobHistories[userId] = res.data.history || [];
        })
        .catch(function () {
          $scope.jobHistories[userId] = [];
        })
        .finally(function () {
          $scope.historyLoading[userId] = false;
        });
    };

    // ── Load ─────────────────────────────────────────────────────────────
    function loadAll() {
      $scope.loading = true;
      ApiService.orgMe(orgId)
        .then((res) => {
          $scope.org = res.data.organisation;
          AuthService.saveOrgSession(AuthService.getOrgToken(), $scope.org);
          $scope.employees = res.data.workers || [];
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

    // ── Expand / collapse row ─────────────────────────────────────────────
    $scope.toggleExpand = function (userId) {
      $scope.expandedId = $scope.expandedId === userId ? null : userId;
    };

    $scope.isExpanded = function (userId) {
      return $scope.expandedId === userId;
    };

    // ── Add worker modal ──────────────────────────────────────────────────
    $scope.testClose = function () {
      $scope.showCreateForm = false;
    };

    // Receive credential from AddUserCtrl after successful create
    $scope.$on("workerSaved", function (evt, cred) {
      $scope.showCreateForm = false;
      if (cred) {
        $scope.createdCred = cred;
      } else {
        $scope.success = "Worker updated successfully.";
        setTimeout(
          () =>
            $scope.$apply(() => {
              $scope.success = null;
            }),
          3000,
        );
      }
      loadAll();
    });

    $scope.$on("closeAddWorkerForm", function () {
      $scope.showCreateForm = false;
    });

    $scope.dismissCred = function () {
      $scope.createdCred = null;
    };

    // ── Helpers ───────────────────────────────────────────────────────────
    $scope.workTypeBadge = function (wt) {
      return {
        "badge-green": wt === "FULL_TIME",
        "badge-blue": wt === "PART_TIME",
        "badge-yellow": wt === "MINIJOB",
      };
    };

    $scope.workTypeLabel = function (wt) {
      return (
        { FULL_TIME: "Full Time", PART_TIME: "Part Time", MINIJOB: "Mini Job" }[
          wt
        ] || wt
      );
    };

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

    $scope.logout = function () {
      AuthService.orgLogout(orgId);
    };
  },
]);
