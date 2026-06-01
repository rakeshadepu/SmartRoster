'use strict';

/**
 * OrgSettingsCtrl
 * Route: /org/:orgId/settings   (access: org)
 * Manages shop hours and work type weekly hour limits.
 * Authenticated via Org-Token (org admin).
 * Backend URLs: /api/org/<orgId>/settings/  and  /api/work-limits/
 */
angular.module('TimetableApp')
.controller('OrgSettingsCtrl', ['$scope', '$routeParams', 'AuthService', 'ApiService',
function($scope, $routeParams, AuthService, ApiService) {

  const orgId  = $routeParams.orgId;

  $scope.orgId      = orgId;
  $scope.org        = AuthService.getOrg();
  $scope.limits     = [];
  $scope.loading    = true;
  $scope.saving     = false;
  $scope.error      = null;
  $scope.success    = null;
  $scope.shopForm   = { shop_open: '', shop_close: '' };
  $scope.limitsForm = { FULL_TIME: 40, PART_TIME: 20, MINIJOB: 10 };

  function load() {
    ApiService.getOrg(orgId).then(function(res) {
      $scope.org = res.data.organisation;
      $scope.shopForm.shop_open  = ($scope.org.shop_open  || '').slice(0, 5);
      $scope.shopForm.shop_close = ($scope.org.shop_close || '').slice(0, 5);
    });
    ApiService.getLimits().then(function(res) {
      $scope.limits = res.data.limits || [];
      $scope.limits.forEach(function(l) { $scope.limitsForm[l.work_type] = l.hours_per_week; });
    }).finally(function() { $scope.loading = false; });
  }

  load();

  $scope.saveShopHours = function() {
    $scope.saving  = true;
    $scope.error   = null;
    $scope.success = null;
    ApiService.updateOrg(orgId, $scope.shopForm).then(function(res) {
      $scope.org     = res.data.organisation;
      $scope.success = 'Shop hours updated.';
    }).catch(function(err) {
      $scope.error = err.data && err.data.errors ?
        JSON.stringify(err.data.errors) : 'Failed to save.';
    }).finally(function() {
      $scope.saving = false;
      setTimeout(function() { $scope.$apply(function() { $scope.success = null; }); }, 3000);
    });
  };

  $scope.saveLimit = function(workType) {
    $scope.error = null;
    ApiService.setLimit({ work_type: workType, hours_per_week: $scope.limitsForm[workType] })
    .then(function() {
      $scope.success = workType.replace('_', ' ') + ' limit saved.';
      load();
    }).catch(function(err) {
      $scope.error = err.data && err.data.errors ?
        JSON.stringify(err.data.errors) : 'Failed to update.';
    }).finally(function() {
      setTimeout(function() { $scope.$apply(function() { $scope.success = null; }); }, 3000);
    });
  };

  $scope.logout = function() { AuthService.orgLogout(orgId); };
}]);
