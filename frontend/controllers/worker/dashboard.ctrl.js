'use strict';

/**
 * WorkerDashboardCtrl
 * Route: /org/:orgId/u/:userId/dashboard   (access: worker)
 * Workers see their own upcoming shifts and availability prompt.
 * Org admin management features are at /org/:orgId/dashboard (Org-Token).
 */
angular.module('TimetableApp')
.controller('WorkerDashboardCtrl', ['$scope', '$routeParams', 'AuthService', 'ApiService',
function($scope, $routeParams, AuthService, ApiService) {

  const orgId  = $routeParams.orgId;
  const userId = $routeParams.userId;

  $scope.orgId      = orgId;
  $scope.userId     = userId;
  $scope.user       = AuthService.getUser();
  $scope.loading    = true;
  $scope.error      = null;

  $scope.myShifts    = [];
  $scope.totalHours  = 0;
  $scope.currentWeek = null;

  ApiService.listTimetables().then(function(res) {
    var timetables = res.data.timetables || [];
    var latest = timetables[0];
    if (latest) {
      ApiService.getWorkerView(latest.id).then(function(r) {
        $scope.myShifts    = r.data.shifts       || [];
        $scope.totalHours  = r.data.total_hours  || 0;
        $scope.currentWeek = { start: r.data.week_start, end: r.data.week_end };
      });
    }
  }).finally(function() { $scope.loading = false; });

  $scope.logout = function() { AuthService.logout(); };
}]);
