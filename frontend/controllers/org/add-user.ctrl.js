"use strict";

angular.module("TimetableApp").controller("AddUserCtrl", [
  "$scope",
  "$rootScope",
  "$location",
  "$routeParams",
  "AuthService",
  "ApiService",
  function (
    $scope,
    $rootScope,
    $location,
    $routeParams,
    AuthService,
    ApiService,
  ) {
    const orgId = $routeParams.orgId || $scope.$parent.orgId;
    $scope.orgId = orgId;
    $scope.loading = false;
    $scope.error = null;
    $scope.created = null;

    // Edit mode state
    $scope.editMode = false;
    $scope.editUserId = null;

    function blankForm() {
      return {
        first_name: "",
        last_name: "",
        email: "",
        phone: "",
        employee_code: "",
        role: "WORKER",
        work_type: "",
        nationality: "",
        dob: "",
        iban: "",
        bic: "",
        house_number: "",
        street: "",
        city: "",
        country: "",
        zip_code: "",
      };
    }

    $scope.form = blankForm();
    $scope.roles = [
      { value: "WORKER", label: "Worker" },
      { value: "MANAGER", label: "Manager" },
      { value: "ADMIN", label: "Admin" },
    ];

    $scope.countries = [
      { name: "Argentina", code: "+54", digits: 10, flag: "🇦🇷" },
      { name: "Australia", code: "+61", digits: 9, flag: "🇦🇺" },
      { name: "Austria", code: "+43", digits: 10, flag: "🇦🇹" },
      { name: "Belgium", code: "+32", digits: 9, flag: "🇧🇪" },
      { name: "Brazil", code: "+55", digits: 11, flag: "🇧🇷" },
      { name: "China", code: "+86", digits: 11, flag: "🇨🇳" },
      { name: "Denmark", code: "+45", digits: 8, flag: "🇩🇰" },
      { name: "France", code: "+33", digits: 9, flag: "🇫🇷" },
      { name: "Germany", code: "+49", digits: 11, flag: "🇩🇪" },
      { name: "Greece", code: "+30", digits: 10, flag: "🇬🇷" },
      { name: "India", code: "+91", digits: 10, flag: "🇮🇳" },
      { name: "Italy", code: "+39", digits: 10, flag: "🇮🇹" },
      { name: "Japan", code: "+81", digits: 10, flag: "🇯🇵" },
      { name: "Mexico", code: "+52", digits: 10, flag: "🇲🇽" },
      { name: "Netherlands", code: "+31", digits: 9, flag: "🇳🇱" },
      { name: "Norway", code: "+47", digits: 8, flag: "🇳🇴" },
      { name: "Poland", code: "+48", digits: 9, flag: "🇵🇱" },
      { name: "Portugal", code: "+351", digits: 9, flag: "🇵🇹" },
      { name: "Russia", code: "+7", digits: 10, flag: "🇷🇺" },
      { name: "Saudi Arabia", code: "+966", digits: 9, flag: "🇸🇦" },
      { name: "Singapore", code: "+65", digits: 8, flag: "🇸🇬" },
      { name: "South Africa", code: "+27", digits: 9, flag: "🇿🇦" },
      { name: "South Korea", code: "+82", digits: 10, flag: "🇰🇷" },
      { name: "Spain", code: "+34", digits: 9, flag: "🇪🇸" },
      { name: "Sweden", code: "+46", digits: 9, flag: "🇸🇪" },
      { name: "Switzerland", code: "+41", digits: 9, flag: "🇨🇭" },
      { name: "Turkey", code: "+90", digits: 10, flag: "🇹🇷" },
      { name: "UAE", code: "+971", digits: 9, flag: "🇦🇪" },
      { name: "UK", code: "+44", digits: 10, flag: "🇬🇧" },
      { name: "USA/Canada", code: "+1", digits: 10, flag: "🇺🇸" },
    ];

    $scope.selectedCountry =
      $scope.countries.find(function (c) {
        return c.name === "Germany";
      }) || $scope.countries[0];

    $scope.phoneError = null;
    $scope.phoneOk = false;

    // ── Listen for edit data broadcast from parent controller ─────────────────
    $scope.$on("editWorkerData", function (evt, workerData) {
      if (!workerData) {
        // Add mode — reset everything
        $scope.editMode = false;
        $scope.editUserId = null;
        $scope.form = blankForm();
        $scope.error = null;
        $scope.created = null;
        $scope.phoneOk = false;
        $scope.phoneError = null;
        return;
      }

      // Edit mode — pre-fill form
      $scope.editMode = true;
      $scope.editUserId = workerData.user_id;
      $scope.form = {
        first_name: workerData.first_name || "",
        last_name: workerData.last_name || "",
        email: workerData.email || "",
        phone: workerData.phone || "",
        employee_code: workerData.employee_code || "",
        role: workerData.role || "WORKER",
        work_type: workerData.work_type || "FULL_TIME",
        nationality: workerData.nationality || "",
        dob: workerData.dob || "",
        iban: workerData.iban || "",
        bic: workerData.bic || "",
        house_number: workerData.house_number || "",
        street: workerData.street || "",
        city: workerData.city || "",
        country: workerData.country || "",
        zip_code: workerData.zip_code || "",
      };
      $scope.error = null;
      $scope.created = null;

      // If phone present, mark as ok (it was valid when saved)
      if (workerData.phone) {
        $scope.phoneOk = true;
        $scope.phoneError = null;
      }
    });

    // ── Phone validation watcher ──────────────────────────────────────────────
    $scope.$watch(
      function () {
        return { phone: $scope.form.phone, country: $scope.selectedCountry };
      },
      function (val) {
        var raw = (val.phone || "").trim();
        var c = val.country;
        var digits = raw.replace(/\D/g, "");
        $scope.phoneError = null;
        $scope.phoneOk = false;
        if (!c || !raw) return;
        if (digits.charAt(0) === "0") {
          $scope.phoneError =
            "Do not start with 0 — " +
            c.digits +
            " digits without leading zero.";
          return;
        }
        if (raw !== digits) {
          $scope.phoneError = "Digits only — no spaces or dashes.";
          return;
        }
        if (digits.length !== c.digits) {
          $scope.phoneError =
            c.name +
            " needs exactly " +
            c.digits +
            " digits (you entered " +
            digits.length +
            ").";
          return;
        }
        $scope.phoneOk = true;
      },
      true,
    );

    $scope.onCountryChange = function () {
      $scope.form.phone = "";
      $scope.phoneError = null;
      $scope.phoneOk = false;
    };

    // ── Submit (add or edit) ──────────────────────────────────────────────────
    $scope.submit = function () {
      $scope.error = null;

      if (!$scope.form.first_name.trim()) {
        $scope.error = "First name is required.";
        return;
      }
      if (!$scope.form.last_name.trim()) {
        $scope.error = "Last name is required.";
        return;
      }
      if (!$scope.form.email.trim()) {
        $scope.error = "Email address is required.";
        return;
      }
      if (!$scope.form.dob) {
        $scope.error = "Date of birth is required.";
        return;
      }
      if (!$scope.form.nationality.trim()) {
        $scope.error = "Nationality is required.";
        return;
      }
      if (!$scope.form.work_type) {
        $scope.error = "Please choose a type of employment.";
        return;
      }
      if (!$scope.phoneOk) {
        $scope.error = "Please enter a valid mobile number.";
        return;
      }

      $scope.loading = true;
      var payload = angular.copy($scope.form);

      if ($scope.editMode) {
        // ── UPDATE existing worker ──────────────────────────────────────────
        ApiService.updateWorker(orgId, $scope.editUserId, payload)
          .then(function () {
            $rootScope.$emit("workerSaved", null); // null = no new credential to show
            // Also broadcast for same-scope listeners
            $scope.$emit("workerSaved", null);
          })
          .catch(function (err) {
            $scope.error = _extractError(
              err,
              "Failed to update worker. Please try again.",
            );
          })
          .finally(function () {
            $scope.loading = false;
          });
      } else {
        // ── CREATE new worker ───────────────────────────────────────────────
        // ── CREATE new worker ───────────────────────────────────────────────
        ApiService.orgAddUser(orgId, payload)
          .then(function (res) {
            var cred = {
              name: res.data.user.full_name,
              user_id: res.data.user.user_id,
              password: res.data.plain_password,
              join_url: window.location.origin + "/#/org/" + orgId + "/join",
            };
            // DO NOT set $scope.created here — modal closes immediately on emit.
            // Parent controller (OrgWorkersCtrl) receives cred and shows it on the main page.
            $scope.$emit("workerSaved", cred);
          })
          .catch(function (err) {
            $scope.error = _extractError(
              err,
              "Failed to create user. Please try again.",
            );
          })
          .finally(function () {
            $scope.loading = false;
          });
      }
    };

    function _extractError(err, fallback) {
      var e = err.data && err.data.errors;
      if (e) {
        var msgs = [];
        Object.entries(e).forEach(function (pair) {
          var field = pair[0],
            errs = pair[1];
          var label =
            field === "non_field_errors" ? "" : field.replace(/_/g, " ") + ": ";
          (Array.isArray(errs) ? errs : [errs]).forEach(function (m) {
            msgs.push(label + m);
          });
        });
        return msgs.join(" · ");
      }
      return (err.data && err.data.error) || fallback;
    }

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

    $scope.addAnother = function () {
      $scope.created = null;
      $scope.error = null;
      $scope.editMode = false;
      $scope.editUserId = null;
      $scope.form = blankForm();
      $scope.phoneOk = false;
    };

    $scope.cancelForm = function () {
      $scope.$emit("closeAddWorkerForm");
    };

    $scope.goBack = function () {
      $location.path("/org/" + orgId + "/dashboard");
    };
  },
]);
