'use strict';

/**
 * WorkerDashboardCtrl
 * Route: /org/:orgId/u/:userId/dashboard   (access: worker — but guard lets employees through too)
 * EMPLOYEE sees org stats + recent workers.
 * WORKER sees their own upcoming shifts.
 */
angular.module('TimetableApp')
.controller('WorkerDashboardCtrl', ['$scope', '$routeParams', 'AuthService', 'ApiService',
function($scope, $routeParams, AuthService, ApiService) {

  const orgId  = $routeParams.orgId;
  const userId = $routeParams.userId;   // the user_id string from the URL

  $scope.orgId      = orgId;
  $scope.userId     = userId;
  $scope.user       = AuthService.getUser();
  $scope.isEmployee = $scope.user && $scope.user.role === 'EMPLOYEE';

  // Shared
  $scope.loading = true;
  $scope.error   = null;

  // Employee-specific
  $scope.org           = null;
  $scope.stats         = { total:0, active:0, fullTime:0, partTime:0, miniJob:0 };
  $scope.timetables    = [];
  $scope.recentWorkers = [];

  // Worker-specific
  $scope.myShifts    = [];
  $scope.totalHours  = 0;
  $scope.currentWeek = null;

  if ($scope.isEmployee) {
    // ── Employee dashboard ──────────────────────────────────────────────
    ApiService.getOrg(orgId).then(function(res) {
      $scope.org = res.data.organisation;
    });

    ApiService.listWorkers(orgId).then(function(res) {
      var ws = res.data.workers || [];
      $scope.stats.total    = ws.length;
      $scope.stats.active   = ws.filter(function(w){ return w.is_active; }).length;
      $scope.stats.fullTime = ws.filter(function(w){ return w.work_type === 'FULL_TIME'; }).length;
      $scope.stats.partTime = ws.filter(function(w){ return w.work_type === 'PART_TIME'; }).length;
      $scope.stats.miniJob  = ws.filter(function(w){ return w.work_type === 'MINIJOB'; }).length;
      $scope.recentWorkers  = ws.slice(0, 5);
    });

    ApiService.listTimetables().then(function(res) {
      $scope.timetables = (res.data.timetables || []).slice(0, 5);
    }).finally(function() { $scope.loading = false; });

  } else {
    // ── Worker dashboard ────────────────────────────────────────────────
    ApiService.listTimetables().then(function(res) {
      $scope.timetables = res.data.timetables || [];
      var latest = $scope.timetables[0];
      if (latest) {
        ApiService.getWorkerView(latest.id).then(function(r) {
          $scope.myShifts    = r.data.shifts       || [];
          $scope.totalHours  = r.data.total_hours  || 0;
          $scope.currentWeek = { start: r.data.week_start, end: r.data.week_end };
        });
      }
    }).finally(function() { $scope.loading = false; });
  }

  $scope.logout = function() { AuthService.logout(); };
}]);
