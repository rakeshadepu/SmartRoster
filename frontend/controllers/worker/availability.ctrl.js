'use strict';

/**
 * AvailabilityCtrl
 * Route: /org/:orgId/u/:userId/availability   (access: worker)
 * Worker submits their weekly availability.
 */
angular.module('TimetableApp')
.controller('AvailabilityCtrl', ['$scope', '$routeParams', 'AuthService', 'ApiService',
function($scope, $routeParams, AuthService, ApiService) {

  const orgId  = $routeParams.orgId;
  const userId = $routeParams.userId;

  $scope.orgId   = orgId;
  $scope.userId  = userId;
  $scope.user    = AuthService.getUser();
  $scope.loading = false;
  $scope.error   = null;
  $scope.success = null;
  $scope.existing = [];

  const DAYS = [
    { code:'MON', label:'Monday'    },
    { code:'TUE', label:'Tuesday'   },
    { code:'WED', label:'Wednesday' },
    { code:'THU', label:'Thursday'  },
    { code:'FRI', label:'Friday'    },
    { code:'SAT', label:'Saturday'  },
    { code:'SUN', label:'Sunday'    },
  ];
  $scope.days = DAYS;

  function getNextMonday() {
    var d = new Date(), day = d.getDay();
    d.setDate(d.getDate() + (day === 0 ? 1 : 8 - day));
    return d.toISOString().slice(0, 10);
  }

  $scope.weekStart = getNextMonday();
  $scope.slots = DAYS.map(function(d) {
    return { day: d.code, label: d.label, checked: false, start_time: '09:00' };
  });

  function loadExisting() {
    ApiService.getAvailability({ week_start: $scope.weekStart }).then(function(res) {
      $scope.existing = res.data.availability || [];
      $scope.slots.forEach(function(s) { s.checked = false; s.start_time = '09:00'; delete s.id; });
      $scope.existing.forEach(function(a) {
        var slot = $scope.slots.find(function(s) { return s.day === a.day; });
        if (slot) { slot.checked = true; slot.start_time = a.start_time.slice(0, 5); slot.id = a.id; }
      });
    });
  }

  loadExisting();
  $scope.changeWeek = function() { loadExisting(); };

  $scope.submit = function() {
    $scope.loading = true;
    $scope.error   = null;
    $scope.success = null;
    var checked = $scope.slots.filter(function(s) { return s.checked; });
    if (checked.length === 0) {
      $scope.error   = 'Select at least one day.';
      $scope.loading = false;
      return;
    }

    var deletePromises = $scope.existing.map(function(a) {
      return ApiService.deleteAvailability(a.id).catch(function(){});
    });

    Promise.all(deletePromises).then(function() {
      return Promise.all(checked.map(function(s) {
        return ApiService.submitAvailability({
          week_start: $scope.weekStart, day: s.day, start_time: s.start_time,
        });
      }));
    }).then(function() {
      $scope.$apply(function() {
        $scope.success = 'Availability saved for week of ' + $scope.weekStart + '.';
        loadExisting();
      });
    }).catch(function() {
      $scope.$apply(function() { $scope.error = 'Submission failed. Try again.'; });
    }).finally(function() {
      $scope.$apply(function() { $scope.loading = false; });
      setTimeout(function() { $scope.$apply(function() { $scope.success = null; }); }, 5000);
    });
  };

  $scope.logout = function() { AuthService.logout(); };
}]);
