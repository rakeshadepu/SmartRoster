'use strict';

angular.module('TimetableApp')
.controller('GlobalUsersCtrl', ['$scope', '$routeParams', 'AuthService', 'ApiService',
function($scope, $routeParams, AuthService, ApiService) {

  const orgId    = $routeParams.orgId;
  $scope.orgId   = orgId;
  $scope.query   = '';
  $scope.result  = null;   // null = not searched, false = not found, object = found
  $scope.message = null;
  $scope.loading = false;
  $scope.error   = null;

  $scope.search = function() {
    var q = ($scope.query || '').trim();
    if (!q) { $scope.error = 'Enter an email address or mobile number.'; return; }

    // Basic format check — must look like email or digits
    var isEmail  = q.indexOf('@') !== -1;
    var isPhone  = /^\d{6,15}$/.test(q.replace(/\D/g,'')) && !isEmail;

    if (!isEmail && !isPhone) {
      $scope.error = 'Enter a complete email address or mobile number (digits only).';
      return;
    }

    $scope.loading = true;
    $scope.error   = null;
    $scope.result  = null;
    $scope.message = null;

    ApiService.orgSearchUser(orgId, q)
    .then(function(res) {
      if (res.data.user) {
        $scope.result  = res.data.user;
        $scope.message = null;
      } else {
        $scope.result  = false;
        $scope.message = res.data.message;
      }
    })
    .catch(function() {
      $scope.error = 'Search failed. Try again.';
    })
    .finally(function() { $scope.loading = false; });
  };

  $scope.clear = function() {
    $scope.query   = '';
    $scope.result  = null;
    $scope.message = null;
    $scope.error   = null;
  };

  $scope.workTypeBadge = function(wt) {
    return { FULL_TIME:'badge-green', PART_TIME:'badge-blue', MINIJOB:'badge-amber' }[wt] || 'badge-gray';
  };
}]);
