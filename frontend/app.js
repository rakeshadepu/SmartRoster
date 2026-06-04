"use strict";

const API_BASE = "http://127.0.0.1:8000/api";

// Public endpoints that must NEVER have any Authorization header attached
const PUBLIC_ENDPOINTS = [
  /\/api\/auth\/login\//,
  /\/api\/auth\/refresh\//,
  /\/api\/org\/register\//,
  /\/api\/org\/[^/]+\/public\//,
  /\/api\/org\/[^/]+\/join\//,
  /\/api\/org\/[^/]+\/login\//,
  /\/api\/org\/login\//,
];

// Org-admin-only endpoints that use Org-Token instead of Bearer JWT
const ORG_ADMIN_ENDPOINTS = [
  /\/api\/org\/[^/]+\/me(\/|$)/,
  /\/api\/org\/[^/]+\/update(\/|$)/,
  /\/api\/org\/[^/]+\/employees(\/|$)/,
  /\/api\/org\/[^/]+\/add-user(\/|$)/,
  /\/api\/org\/[^/]+\/global-users(\/|$)/,
  /\/api\/org\/[^/]+\/logout(\/|$)/,
  // Org-admin timetable management endpoints
  /\/api\/org\/[^/]+\/workers(\/|$)/,
  /\/api\/org\/[^/]+\/settings(\/|$)/,
  /\/api\/org\/[^/]+\/email-conflicts(\/|$)/,
  /\/api\/work-limits(\/|$)/,
  /\/api\/availability(\/|$)/,
  /\/api\/timetable(\/|$)/,
];

function matchesAny(url, patterns) {
  return patterns.some(function (rx) {
    return rx.test(url);
  });
}

angular
  .module("TimetableApp", ["ngRoute"])

  // ── Routes ───────────────────────────────────────────────────────────────
  .config([
    "$routeProvider",
    function ($routeProvider) {
      $routeProvider

        .when("/", {
          templateUrl: "views/home.html",
          controller: "HomeCtrl",
          access: "home",
        })
        .when("/org/register", {
          templateUrl: "views/org/register.html",
          controller: "OrgRegisterCtrl",
          access: "public",
        })
        .when("/org/:orgId/login", {
          templateUrl: "views/org/login.html",
          controller: "OrgLoginCtrl",
          access: "public",
        })

        // Join/login page for workers
        // Backend: GET /api/org/<org_id>/join/
        // Post-login: /org/<orgId>/u/<userId>/dashboard
        .when("/org/:orgId/join", {
          templateUrl: "views/org/join.html",
          controller: "OrgJoinCtrl",
          access: "public",
        })

        // Org admin (Org-Token)
        .when("/org/:orgId/dashboard", {
          templateUrl: "views/org/dashboard.html",
          controller: "OrgDashboardCtrl",
          access: "org",
        })
        .when("/org/:orgId/add-user", {
          templateUrl: "views/org/add-user.html",
          controller: "AddUserCtrl",
          access: "org",
        })
        .when("/org/:orgId/global-users", {
          templateUrl: "views/org/global-users.html",
          controller: "GlobalUsersCtrl",
          access: "org",
        })
        .when("/org/:orgId/manage", {
          templateUrl: "views/org/manage.html",
          controller: "OrgWorkersCtrl",
          access: "org",
        })
        .when("/org/:orgId/schedule", {
          templateUrl: "views/org/schedule.html",
          controller: "OrgTimetableCtrl",
          access: "org",
        })
        .when("/org/:orgId/settings", {
          templateUrl: "views/org/settings.html",
          controller: "OrgSettingsCtrl",
          access: "org",
        })

        // Worker / Employee routes — pattern: /org/:orgId/u/:userId/<page>
        .when("/org/:orgId/u/:userId/dashboard", {
          templateUrl: "views/worker/dashboard.html",
          controller: "WorkerDashboardCtrl",
          access: "worker",
        })

        .when("/org/:orgId/u/:userId/timetable", {
          templateUrl: "views/worker/timetable.html",
          controller: "WorkerTimetableCtrl",
          access: "worker",
        })
        .when("/org/:orgId/u/:userId/availability", {
          templateUrl: "views/worker/availability.html",
          controller: "AvailabilityCtrl",
          access: "worker",
        })

        .otherwise({ redirectTo: "/" });
    },
  ])

  // ── HTTP Interceptor ─────────────────────────────────────────────────────
  .factory("JwtInterceptor", [
    "$window",
    "$q",
    function ($window, $q) {
      return {
        request: function (config) {
          if (!config.url.startsWith(API_BASE)) return config;
          config.headers = config.headers || {};

          // Never attach any auth header to public endpoints
          if (matchesAny(config.url, PUBLIC_ENDPOINTS)) {
            delete config.headers["Authorization"];
            return config;
          }

          var orgTok = $window.localStorage.getItem("org_token");
          // Guard: treat the string "null" as absent (legacy bug protection)
          if (orgTok === "null" || orgTok === "undefined") orgTok = null;

          var jwt = $window.localStorage.getItem("access_token");
          if (jwt === "null" || jwt === "undefined") jwt = null;

          if (matchesAny(config.url, ORG_ADMIN_ENDPOINTS) && orgTok) {
            config.headers["Authorization"] = "Org-Token " + orgTok;
          } else if (jwt) {
            config.headers["Authorization"] = "Bearer " + jwt;
          }
          // If neither token exists, send no Authorization header
          // (server will return 401 which is handled below)

          return config;
        },

        responseError: function (rejection) {
          if (
            rejection.status === 401 &&
            rejection.config &&
            !matchesAny(rejection.config.url, PUBLIC_ENDPOINTS)
          ) {
            var org = null;
            try {
              org = JSON.parse($window.localStorage.getItem("org") || "null");
            } catch (e) {}

            if (matchesAny(rejection.config.url, ORG_ADMIN_ENDPOINTS)) {
              // Org-Token expired or missing — clear org session, go to org login
              $window.localStorage.removeItem("org_token");
              $window.localStorage.removeItem("org");
              $window.location.href = org
                ? "#/org/" + org.org_id + "/login"
                : "#/";
            } else {
              // JWT expired — clear worker session, go to worker join page
              $window.localStorage.removeItem("access_token");
              $window.localStorage.removeItem("refresh_token");
              $window.localStorage.removeItem("user");
              $window.location.href = org
                ? "#/org/" + org.org_id + "/join"
                : "#/";
            }
          }
          return $q.reject(rejection);
        },
      };
    },
  ])

  .config([
    "$httpProvider",
    function ($httpProvider) {
      $httpProvider.interceptors.push("JwtInterceptor");
    },
  ])

  // ── Route guard + global helpers ─────────────────────────────────────────
  .run([
    "$rootScope",
    "$location",
    "AuthService",
    function ($rootScope, $location, AuthService) {
      $rootScope.workTypeBadge = function (wt) {
        return (
          {
            FULL_TIME: "badge-green",
            PART_TIME: "badge-blue",
            MINIJOB: "badge-amber",
          }[wt] || "badge-gray"
        );
      };

      $rootScope.showCopyToast = false;

      $rootScope.copyJoinLink = function ($event) {
        if ($event) $event.preventDefault();

        const org = JSON.parse(localStorage.getItem("org") || "{}");

        const joinLink =
          window.location.origin + "/#/org/" + org.org_id + "/join";

        navigator.clipboard.writeText(joinLink);

        $rootScope.showCopyToast = true;

        setTimeout(function () {
          $rootScope.$apply(function () {
            $rootScope.showCopyToast = false;
          });
        }, 2500);
      };

      $rootScope.$on("$routeChangeStart", function (event, next) {
        var access = next.access || "private";
        var user = AuthService.getUser();
        var isOrg = AuthService.isOrgAdmin();
        var params = next.params || {};

        if (access === "home" || access === "public") return;

        if (access === "org") {
          if (!isOrg) {
            event.preventDefault();
            var oid = params.orgId || "";
            $location.path(oid ? "/org/" + oid + "/login" : "/");
          }
          return;
        }

        // JWT-protected routes
        if (!user) {
          event.preventDefault();
          var oid2 = params.orgId || "";
          $location.path(oid2 ? "/org/" + oid2 + "/join" : "/");
          return;
        }

        var orgId = params.orgId || user.org_slug || "";
        var userId = user.user_id || "";

        // All JWT users are WORKER role — no role-based redirect needed
      });

      $rootScope.currentUser = AuthService.getUser();
      $rootScope.$on("userChanged", function () {
        $rootScope.currentUser = AuthService.getUser();
      });
    },
  ]);
