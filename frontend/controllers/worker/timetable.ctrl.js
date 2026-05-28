'use strict';

/**
 * WorkerTimetableCtrl
 * Route: /org/:orgId/u/:userId/timetable   (access: worker)
 * Worker's personal timetable view.
 */
angular.module('TimetableApp')
.controller('WorkerTimetableCtrl', ['$scope', '$routeParams', 'AuthService', 'ApiService',
function($scope, $routeParams, AuthService, ApiService) {

  const orgId  = $routeParams.orgId;
  const userId = $routeParams.userId;

  $scope.orgId      = orgId;
  $scope.userId     = userId;
  $scope.user       = AuthService.getUser();
  $scope.timetables = [];
  $scope.selected   = null;
  $scope.myShifts   = [];
  $scope.totalHours = 0;
  $scope.weekBudget = $scope.user ? $scope.user.weekly_hours : 0;
  $scope.loading    = true;
  $scope.error      = null;

  const DAY_LABELS = {
    MON:'Monday', TUE:'Tuesday', WED:'Wednesday', THU:'Thursday',
    FRI:'Friday', SAT:'Saturday', SUN:'Sunday'
  };
  $scope.days     = ['MON','TUE','WED','THU','FRI','SAT','SUN'];
  $scope.dayLabel = function(d) { return DAY_LABELS[d] || d; };

  function load() {
    ApiService.listTimetables().then(function(res) {
      $scope.timetables = res.data.timetables || [];
      if ($scope.timetables.length > 0) $scope.selectTimetable($scope.timetables[0]);
    }).finally(function() { $scope.loading = false; });
  }

  load();

  $scope.selectTimetable = function(tt) {
    $scope.selected = tt;
    $scope.myShifts = [];
    ApiService.getWorkerView(tt.id).then(function(res) {
      $scope.myShifts   = res.data.shifts      || [];
      $scope.totalHours = res.data.total_hours || 0;
      $scope.weekStart  = res.data.week_start;
      $scope.weekEnd    = res.data.week_end;
    }).catch(function() { $scope.error = 'Could not load shifts.'; });
  };

  $scope.shiftForDay    = function(d) { return $scope.myShifts.find(function(s){ return s.day === d; }) || null; };
  $scope.utilisationPct = function() {
    return !$scope.weekBudget ? 0 : Math.min(100, Math.round(100 * $scope.totalHours / $scope.weekBudget));
  };

  $scope.downloadPdf = function() {
    if (!$scope.selected) return;
    var url   = ApiService.pdfUrl($scope.selected.id);
    var token = localStorage.getItem('access_token');
    fetch(url, { headers: { Authorization: 'Bearer ' + token } })
      .then(function(r) { return r.blob(); })
      .then(function(blob) {
        var a      = document.createElement('a');
        a.href     = URL.createObjectURL(blob);
        a.download = 'my_timetable_' + $scope.weekStart + '.pdf';
        a.click();
      }).catch(function() { $scope.$apply(function() { $scope.error = 'PDF download failed.'; }); });
  };

  $scope.logout = function() { AuthService.logout(); };
}]);
