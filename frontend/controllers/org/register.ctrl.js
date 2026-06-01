"use strict";

angular.module("TimetableApp").controller("OrgRegisterCtrl", [
  "$scope",
  "$location",
  "ApiService",
  function ($scope, $location, ApiService) {
    $scope.loading = false;
    $scope.error = null;
    $scope.created = null;
    $scope.phoneError = null;
    $scope.phoneOk = false;

    // ── Country list with flag, dial code, expected digit count, placeholder ──
    $scope.countries = [
      {
        name: "Germany",
        code: "+49",
        digits: 11,
        flag: "🇩🇪",
        placeholder: "17612345678",
      },
      {
        name: "India",
        code: "+91",
        digits: 10,
        flag: "🇮🇳",
        placeholder: "9876543210",
      },
      {
        name: "USA/Canada",
        code: "+1",
        digits: 10,
        flag: "🇺🇸",
        placeholder: "2125551234",
      },
      {
        name: "UK",
        code: "+44",
        digits: 10,
        flag: "🇬🇧",
        placeholder: "7911123456",
      },
      {
        name: "France",
        code: "+33",
        digits: 9,
        flag: "🇫🇷",
        placeholder: "612345678",
      },
      {
        name: "Italy",
        code: "+39",
        digits: 10,
        flag: "🇮🇹",
        placeholder: "3201234567",
      },
      {
        name: "Spain",
        code: "+34",
        digits: 9,
        flag: "🇪🇸",
        placeholder: "612345678",
      },
      {
        name: "Netherlands",
        code: "+31",
        digits: 9,
        flag: "🇳🇱",
        placeholder: "612345678",
      },
      {
        name: "Belgium",
        code: "+32",
        digits: 9,
        flag: "🇧🇪",
        placeholder: "471123456",
      },
      {
        name: "Switzerland",
        code: "+41",
        digits: 9,
        flag: "🇨🇭",
        placeholder: "791234567",
      },
      {
        name: "Austria",
        code: "+43",
        digits: 10,
        flag: "🇦🇹",
        placeholder: "6641234567",
      },
      {
        name: "Australia",
        code: "+61",
        digits: 9,
        flag: "🇦🇺",
        placeholder: "412345678",
      },
      {
        name: "Japan",
        code: "+81",
        digits: 10,
        flag: "🇯🇵",
        placeholder: "9012345678",
      },
      {
        name: "China",
        code: "+86",
        digits: 11,
        flag: "🇨🇳",
        placeholder: "13812345678",
      },
      {
        name: "Brazil",
        code: "+55",
        digits: 11,
        flag: "🇧🇷",
        placeholder: "11987654321",
      },
      {
        name: "Russia",
        code: "+7",
        digits: 10,
        flag: "🇷🇺",
        placeholder: "9161234567",
      },
      {
        name: "South Africa",
        code: "+27",
        digits: 9,
        flag: "🇿🇦",
        placeholder: "711234567",
      },
      {
        name: "UAE",
        code: "+971",
        digits: 9,
        flag: "🇦🇪",
        placeholder: "501234567",
      },
      {
        name: "Saudi Arabia",
        code: "+966",
        digits: 9,
        flag: "🇸🇦",
        placeholder: "512345678",
      },
      {
        name: "Singapore",
        code: "+65",
        digits: 8,
        flag: "🇸🇬",
        placeholder: "81234567",
      },
      {
        name: "Turkey",
        code: "+90",
        digits: 10,
        flag: "🇹🇷",
        placeholder: "5321234567",
      },
      {
        name: "Poland",
        code: "+48",
        digits: 9,
        flag: "🇵🇱",
        placeholder: "512345678",
      },
      {
        name: "Sweden",
        code: "+46",
        digits: 9,
        flag: "🇸🇪",
        placeholder: "701234567",
      },
      {
        name: "Norway",
        code: "+47",
        digits: 8,
        flag: "🇳🇴",
        placeholder: "40123456",
      },
      {
        name: "Denmark",
        code: "+45",
        digits: 8,
        flag: "🇩🇰",
        placeholder: "20123456",
      },
      {
        name: "Portugal",
        code: "+351",
        digits: 9,
        flag: "🇵🇹",
        placeholder: "912345678",
      },
      {
        name: "Greece",
        code: "+30",
        digits: 10,
        flag: "🇬🇷",
        placeholder: "6912345678",
      },
      {
        name: "Mexico",
        code: "+52",
        digits: 10,
        flag: "🇲🇽",
        placeholder: "5512345678",
      },
      {
        name: "Argentina",
        code: "+54",
        digits: 10,
        flag: "🇦🇷",
        placeholder: "1112345678",
      },
      {
        name: "South Korea",
        code: "+82",
        digits: 10,
        flag: "🇰🇷",
        placeholder: "1012345678",
      },
    ];

    // Default to Germany
    // $scope.selectedCountry = $scope.countries[0];
    $scope.selectedCountryCode = "+49"; // default Germany

    $scope.form = {
      org_name: "",
      owner_name: "",
      email: "",
      password: "",
      confirm_pw: "",
      phone: "",
      house_number: "",
      street: "",
      city: "",
      country: "",
      zip_code: "",
      shop_open: "08:00",
      shop_close: "18:00",
    };

    $scope.onCountryChange = function () {
      $scope.form.phone = "";
      $scope.phoneError = null;
      $scope.phoneOk = false;
    };

    $scope.validatePhone = function () {
      const raw = ($scope.form.phone || "").trim();
      const digits = raw.replace(/\D/g, "");

      const c = $scope.countries.find(
        (c) => c.code === $scope.selectedCountryCode,
      );

      $scope.phoneError = null;
      $scope.phoneOk = false;

      if (!c || !raw) return;

      if (digits.charAt(0) === "0") {
        $scope.phoneError = `Do not start with 0. Enter ${c.digits} digits without leading zero.`;
        return;
      }

      if (raw !== digits) {
        $scope.phoneError =
          "Enter digits only — no spaces, dashes or brackets.";
        return;
      }

      if (digits.length !== c.digits) {
        $scope.phoneError = `Phone: ${c.code} numbers must be exactly ${c.digits} digits (you entered ${digits.length}).`;
        return;
      }

      $scope.phoneOk = true;
    };

    $scope.register = function () {
      $scope.error = null;

      if ($scope.form.password !== $scope.form.confirm_pw) {
        $scope.error = "Passwords do not match.";
        return;
      }
      if ($scope.form.password.length < 8) {
        $scope.error = "Password must be at least 8 characters.";
        return;
      }
      if (!$scope.phoneOk) {
        $scope.error = "Please enter a valid mobile number.";
        return;
      }

      const baseUrl = window.location.origin;
      $scope.loading = true;

      ApiService.orgRegister({
        org_name: $scope.form.org_name,
        owner_name: $scope.form.owner_name,
        email: $scope.form.email,
        password: $scope.form.password,
        country_code: $scope.selectedCountryCode,
        phone: $scope.form.phone,
        house_number: $scope.form.house_number,
        street: $scope.form.street,
        city: $scope.form.city,
        country: $scope.form.country,
        zip_code: $scope.form.zip_code,
        shop_open: $scope.form.shop_open,
        shop_close: $scope.form.shop_close,
      })
        .then(function (res) {
          function buildUrl(path) {
            var frontendBase =
              window.location.protocol + "//" + window.location.host;
            var cleanPath = path.replace(/^https?:\/\/[^/]+/, "");
            return frontendBase + cleanPath;
          }

          $scope.created = {
            org: res.data.organisation,
            orgId: res.data.org_id,
            loginUrl: buildUrl(res.data.login_url),
            joinUrl: buildUrl(res.data.join_url),
          };
        })
        .catch(function (err) {
          const e = err.data && err.data.errors;
          if (e) {
            // Flatten all error messages into one string
            const msgs = [];
            Object.entries(e).forEach(([field, errs]) => {
              const fieldLabel =
                field.charAt(0).toUpperCase() +
                field.slice(1).replace("_", " ");
              (Array.isArray(errs) ? errs : [errs]).forEach((msg) => {
                msgs.push(
                  field === "non_field_errors" || field === "errors"
                    ? msg
                    : `${fieldLabel}: ${msg}`,
                );
              });
            });
            $scope.error = msgs.join(" · ");
          } else {
            $scope.error = "Registration failed. Please try again.";
          }
        })
        .finally(function () {
          $scope.loading = false;
        });
    };

    $scope.copyText = function (text, $event) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard
          .writeText(text)
          .then(() => {
            showCopied($event);
          })
          .catch(() => {
            fallbackCopy(text, $event);
          });
      } else {
        fallbackCopy(text, $event);
      }

      function fallbackCopy(text, $event) {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        try {
          document.execCommand("copy");
          showCopied($event);
        } catch (err) {
          console.error("Copy failed", err);
        }
        document.body.removeChild(textarea);
      }

      function showCopied($event) {
        const btn = $event.target;
        btn.textContent = "Copied!";
        btn.classList.add("copied");
        setTimeout(() => {
          btn.textContent = "Copy";
          btn.classList.remove("copied");
        }, 2000);
      }
    };

    $scope.goToDashboard = function () {
      if ($scope.created) {
        $location.path("/org/" + $scope.created.orgId + "/login");
      }
    };
  },
]);
