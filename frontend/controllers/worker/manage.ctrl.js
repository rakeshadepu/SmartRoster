'use strict';

/**
 * WorkersCtrl
 * Route: /org/:orgId/u/:userId/manage   (access: employee)
 * Manages the worker roster — create, edit, deactivate, reset password.
 * Backend URLs: /api/org/<orgId>/workers/  and  /api/org/<orgId>/<workerUserId>/
 */
angular.module('TimetableApp')
.controller('WorkersCtrl', ['$scope', '$routeParams', 'AuthService', 'ApiService',
function($scope, $routeParams, AuthService, ApiService) {

  const orgId  = $routeParams.orgId;
  const userId = $routeParams.userId;   // logged-in employee's user_id (from URL)

  $scope.orgId      = orgId;
  $scope.userId     = userId;
  $scope.user       = AuthService.getUser();
  $scope.workers    = [];
  $scope.loading    = true;
  $scope.error      = null;
  $scope.success    = null;
  $scope.newWorker  = { full_name: '', work_type: 'FULL_TIME' };
  $scope.showCreateForm = false;
  $scope.creating   = false;
  $scope.createdCred = null;
  $scope.editModal  = false;
  $scope.editWorker = {};
  $scope.resetModal = false;
  $scope.resetCred  = null;
  $scope.filter     = { work_type: '', is_active: '' };

  function loadWorkers() {
    $scope.loading = true;
    var params = {};
    if ($scope.filter.work_type) params.work_type = $scope.filter.work_type;
    if ($scope.filter.is_active !== '') params.is_active = $scope.filter.is_active;
    // GET /api/org/<orgId>/workers/
    ApiService.listWorkers(orgId, params).then(function(res) {
      $scope.workers = res.data.workers || [];
    }).catch(function() {
      $scope.error = 'Failed to load workers.';
    }).finally(function() { $scope.loading = false; });
  }

  loadWorkers();
  $scope.applyFilter = loadWorkers;

  $scope.createWorker = function() {
    if (!$scope.newWorker.full_name.trim()) return;
    $scope.creating    = true;
    $scope.error       = null;
    $scope.createdCred = null;

    // POST /api/org/<orgId>/workers/
    ApiService.createWorker(orgId, $scope.newWorker).then(function(res) {
      var w = res.data.worker;
      $scope.createdCred = {
        name      : w.full_name,
        user_id   : w.user_id,
        password  : w.plain_password,
        work_type : w.work_type,
        join_url  : window.location.origin + '/#/org/' + orgId + '/join',
      };
      $scope.newWorker = { full_name: '', work_type: 'FULL_TIME' };
      $scope.showCreateForm = false;
      loadWorkers();
    }).catch(function(err) {
      $scope.error = err.data && err.data.errors ?
        JSON.stringify(err.data.errors) : 'Failed to create worker.';
    }).finally(function() { $scope.creating = false; });
  };

  $scope.openEdit = function(worker) {
    $scope.editWorker = {
      user_id   : worker.user_id,
      full_name : worker.full_name,
      work_type : worker.work_type,
      is_active : worker.is_active,
    };
    $scope.editModal = true;
    $scope.error = null;
  };

  $scope.saveEdit = function() {
    // PATCH /api/org/<orgId>/<workerUserId>/
    ApiService.updateWorker(orgId, $scope.editWorker.user_id, {
      full_name : $scope.editWorker.full_name,
      work_type : $scope.editWorker.work_type,
      is_active : $scope.editWorker.is_active,
    }).then(function() {
      $scope.editModal = false;
      $scope.success   = 'Worker updated.';
      loadWorkers();
      setTimeout(function() { $scope.$apply(function() { $scope.success = null; }); }, 3000);
    }).catch(function() { $scope.error = 'Update failed.'; });
  };

  $scope.deactivate = function(worker) {
    if (!confirm('Deactivate ' + worker.full_name + '?')) return;
    // DELETE /api/org/<orgId>/<workerUserId>/
    ApiService.deleteWorker(orgId, worker.user_id).then(function() {
      $scope.success = worker.full_name + ' deactivated.';
      loadWorkers();
      setTimeout(function() { $scope.$apply(function() { $scope.success = null; }); }, 3000);
    }).catch(function() { $scope.error = 'Failed to deactivate.'; });
  };

  $scope.resetPassword = function(worker) {
    if (!confirm('Reset password for ' + worker.full_name + '?')) return;
    // POST /api/org/<orgId>/<workerUserId>/reset-password/
    ApiService.resetPassword(orgId, worker.user_id).then(function(res) {
      $scope.resetCred = {
        name     : worker.full_name,
        user_id  : res.data.user_id,
        password : res.data.new_password,
      };
      $scope.resetModal = true;
    }).catch(function() { $scope.error = 'Password reset failed.'; });
  };

  $scope.copyText = function(text, $event) {
    navigator.clipboard.writeText(text);
    var btn = $event.target;
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(function() { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2000);
  };

  $scope.logout = function() { AuthService.logout(); };
}]);
