'use strict';

/**
 * OrgTimetableCtrl
 * Route: /org/:orgId/schedule   (access: org)
 * Generates, edits and publishes weekly timetables.
 * Authenticated via Org-Token (org admin).
 */
angular.module('TimetableApp')
.controller('OrgTimetableCtrl', ['$scope', '$sce', '$routeParams', 'AuthService', 'ApiService',
function($scope, $sce, $routeParams, AuthService, ApiService) {

  const orgId  = $routeParams.orgId;

  $scope.orgId      = orgId;
  $scope.org        = AuthService.getOrg();
  $scope.timetables = [];
  $scope.selected   = null;
  $scope.loading    = true;
  $scope.generating = false;
  $scope.error      = null;
  $scope.success    = null;
  $scope.warnings   = [];
  $scope.summary    = {};
  $scope.htmlView   = null;
  $scope.viewMode   = 'grid';

  $scope.genForm        = { week_start: nextMonday(), regenerate: false };
  $scope.editShiftModal = false;
  $scope.editShift      = {};

  const DAYS       = ['MON','TUE','WED','THU','FRI','SAT','SUN'];
  const DAY_LABELS = { MON:'Mon',TUE:'Tue',WED:'Wed',THU:'Thu',FRI:'Fri',SAT:'Sat',SUN:'Sun' };
  $scope.days     = DAYS;
  $scope.dayLabel = function(d) { return DAY_LABELS[d] || d; };

  function nextMonday() {
    var d = new Date(), day = d.getDay();
    d.setDate(d.getDate() + (day === 0 ? 1 : 8 - day));
    return d.toISOString().slice(0, 10);
  }

  function loadList() {
    ApiService.listTimetables().then(function(res) {
      $scope.timetables = res.data.timetables || [];
    }).finally(function() { $scope.loading = false; });
  }
  loadList();

  $scope.selectTimetable = function(tt) {
    $scope.selected = tt; $scope.htmlView = null; $scope.viewMode = 'grid'; $scope.error = null;
  };

  $scope.gridWorkers = function(tt) {
    if (!tt || !tt.shifts) return [];
    var seen = {};
    tt.shifts.forEach(function(s) { seen[s.worker_name] = { id: s.worker, wt: s.work_type }; });
    return Object.entries(seen).sort(function(a,b) { return a[0].localeCompare(b[0]); });
  };

  $scope.shiftForWorkerDay = function(tt, workerName, day) {
    if (!tt || !tt.shifts) return null;
    return tt.shifts.find(function(s) { return s.worker_name === workerName && s.day === day; }) || null;
  };

  $scope.workerTotals = function(tt, workerName) {
    if (!tt || !tt.shifts) return 0;
    return tt.shifts
      .filter(function(s) { return s.worker_name === workerName; })
      .reduce(function(sum, s) { return sum + parseFloat(s.hours || 0); }, 0)
      .toFixed(1);
  };

  $scope.generate = function() {
    if (!$scope.genForm.week_start) return;
    $scope.generating = true; $scope.error = null; $scope.warnings = [];
    ApiService.generateTimetable($scope.genForm.week_start, $scope.genForm.regenerate)
    .then(function(res) {
      $scope.success  = res.data.message;
      $scope.warnings = res.data.warnings || [];
      $scope.summary  = res.data.summary  || {};
      loadList();
      ApiService.getTimetable(res.data.timetable.id).then(function(r) { $scope.selected = r.data.timetable; });
    })
    .catch(function(err) {
      $scope.error = err.data && err.data.errors ? err.data.errors.join(', ') : 'Generation failed.';
    })
    .finally(function() {
      $scope.generating = false;
      setTimeout(function() { $scope.$apply(function() { $scope.success = null; }); }, 5000);
    });
  };

  $scope.publish = function() {
    if (!$scope.selected || !confirm('Publish this timetable? Workers will be able to see it.')) return;
    ApiService.publishTimetable($scope.selected.id).then(function(res) {
      $scope.selected = res.data.timetable; $scope.success = 'Published!'; loadList();
      setTimeout(function() { $scope.$apply(function() { $scope.success = null; }); }, 3000);
    }).catch(function() { $scope.error = 'Publish failed.'; });
  };

  $scope.loadHtmlView = function() {
    if (!$scope.selected) return;
    $scope.viewMode = 'html';
    ApiService.getTimetableHTML($scope.selected.id).then(function(res) {
      $scope.htmlView = $sce.trustAsHtml(res.data);
    }).catch(function() { $scope.error = 'Failed to load HTML view.'; });
  };

  $scope.downloadPdf = function() {
    if (!$scope.selected) return;
    var url   = ApiService.pdfUrl($scope.selected.id);
    var token = localStorage.getItem('org_token');
    fetch(url, { headers: { Authorization: 'Org-Token ' + token } })
      .then(function(r) { return r.blob(); })
      .then(function(blob) {
        var a      = document.createElement('a');
        a.href     = URL.createObjectURL(blob);
        a.download = 'timetable_week_' + $scope.selected.week_start + '.pdf';
        a.click();
      }).catch(function() { $scope.$apply(function() { $scope.error = 'PDF download failed.'; }); });
  };

  $scope.openEditShift = function(shift) {
    $scope.editShift = {
      id          : shift.id,
      timetable   : $scope.selected.id,
      worker_name : shift.worker_name,
      day         : shift.day_display || shift.day,
      start_time  : shift.start_time ? shift.start_time.slice(0, 5) : '',
      end_time    : shift.end_time   ? shift.end_time.slice(0, 5)   : '',
    };
    $scope.editShiftModal = true; $scope.error = null;
  };

  $scope.saveShift = function() {
    ApiService.patchShift($scope.editShift.timetable, $scope.editShift.id,
      { start_time: $scope.editShift.start_time, end_time: $scope.editShift.end_time })
    .then(function() {
      $scope.editShiftModal = false; $scope.success = 'Shift updated.';
      ApiService.getTimetable($scope.selected.id).then(function(r) { $scope.selected = r.data.timetable; });
      setTimeout(function() { $scope.$apply(function() { $scope.success = null; }); }, 3000);
    }).catch(function(err) {
      $scope.error = err.data && err.data.errors ? err.data.errors.join(', ') : 'Update failed.';
    });
  };

  $scope.deleteShift = function(shift) {
    if (!confirm("Remove " + shift.worker_name + "'s shift on " + shift.day + "?")) return;
    ApiService.deleteShift($scope.selected.id, shift.id).then(function() {
      $scope.success = 'Shift removed.';
      ApiService.getTimetable($scope.selected.id).then(function(r) { $scope.selected = r.data.timetable; });
      setTimeout(function() { $scope.$apply(function() { $scope.success = null; }); }, 3000);
    }).catch(function() { $scope.error = 'Delete failed.'; });
  };

  $scope.logout = function() { AuthService.orgLogout(orgId); };
}]);
