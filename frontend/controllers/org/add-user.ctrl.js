'use strict';

angular.module('TimetableApp')
.controller('AddUserCtrl', ['$scope', '$location', '$routeParams', 'AuthService', 'ApiService',
function($scope, $location, $routeParams, AuthService, ApiService) {

  const orgId    = $routeParams.orgId;
  $scope.orgId   = orgId;
  $scope.loading = false;
  $scope.error   = null;
  $scope.created = null;  // holds credentials after success

  $scope.form = {
    first_name  : '',
    last_name   : '',
    email       : '',
    phone       : '',
    role        : 'WORKER',
    work_type   : 'FULL_TIME',
    nationality : '',
    dob         : '',
    iban        : '',
    bic         : '',
    house_number: '',
    street      : '',
    city        : '',
    country     : '',
    zip_code    : '',
  };

  $scope.countries = [
    { name:'Argentina',    code:'+54',  digits:10, flag:'🇦🇷' },
    { name:'Australia',    code:'+61',  digits:9,  flag:'🇦🇺' },
    { name:'Austria',      code:'+43',  digits:10, flag:'🇦🇹' },
    { name:'Belgium',      code:'+32',  digits:9,  flag:'🇧🇪' },
    { name:'Brazil',       code:'+55',  digits:11, flag:'🇧🇷' },
    { name:'China',        code:'+86',  digits:11, flag:'🇨🇳' },
    { name:'Denmark',      code:'+45',  digits:8,  flag:'🇩🇰' },
    { name:'France',       code:'+33',  digits:9,  flag:'🇫🇷' },
    { name:'Germany',      code:'+49',  digits:11, flag:'🇩🇪' },
    { name:'Greece',       code:'+30',  digits:10, flag:'🇬🇷' },
    { name:'India',        code:'+91',  digits:10, flag:'🇮🇳' },
    { name:'Italy',        code:'+39',  digits:10, flag:'🇮🇹' },
    { name:'Japan',        code:'+81',  digits:10, flag:'🇯🇵' },
    { name:'Mexico',       code:'+52',  digits:10, flag:'🇲🇽' },
    { name:'Netherlands',  code:'+31',  digits:9,  flag:'🇳🇱' },
    { name:'Norway',       code:'+47',  digits:8,  flag:'🇳🇴' },
    { name:'Poland',       code:'+48',  digits:9,  flag:'🇵🇱' },
    { name:'Portugal',     code:'+351', digits:9,  flag:'🇵🇹' },
    { name:'Russia',       code:'+7',   digits:10, flag:'🇷🇺' },
    { name:'Saudi Arabia', code:'+966', digits:9,  flag:'🇸🇦' },
    { name:'Singapore',    code:'+65',  digits:8,  flag:'🇸🇬' },
    { name:'South Africa', code:'+27',  digits:9,  flag:'🇿🇦' },
    { name:'South Korea',  code:'+82',  digits:10, flag:'🇰🇷' },
    { name:'Spain',        code:'+34',  digits:9,  flag:'🇪🇸' },
    { name:'Sweden',       code:'+46',  digits:9,  flag:'🇸🇪' },
    { name:'Switzerland',  code:'+41',  digits:9,  flag:'🇨🇭' },
    { name:'Turkey',       code:'+90',  digits:10, flag:'🇹🇷' },
    { name:'UAE',          code:'+971', digits:9,  flag:'🇦🇪' },
    { name:'UK',           code:'+44',  digits:10, flag:'🇬🇧' },
    { name:'USA/Canada',   code:'+1',   digits:10, flag:'🇺🇸' },
  ];

  $scope.selectedCountry = $scope.countries.find(function(c){ return c.name === 'Germany'; }) || $scope.countries[0];
  $scope.phoneError = null;
  $scope.phoneOk    = false;

  // Watch phone + country for validation
  $scope.$watch(function() {
    return { phone: $scope.form.phone, country: $scope.selectedCountry };
  }, function(val) {
    var raw    = (val.phone || '').trim();
    var c      = val.country;
    var digits = raw.replace(/\D/g, '');
    $scope.phoneError = null;
    $scope.phoneOk    = false;
    if (!c || !raw) return;
    if (digits.charAt(0) === '0') {
      $scope.phoneError = 'Do not start with 0 — ' + c.digits + ' digits without leading zero.';
      return;
    }
    if (raw !== digits) {
      $scope.phoneError = 'Digits only — no spaces or dashes.';
      return;
    }
    if (digits.length !== c.digits) {
      $scope.phoneError = c.name + ' needs exactly ' + c.digits + ' digits (you entered ' + digits.length + ').';
      return;
    }
    $scope.phoneOk = true;
  }, true);

  $scope.onCountryChange = function() {
    $scope.form.phone = '';
    $scope.phoneError = null;
    $scope.phoneOk    = false;
  };

  $scope.submit = function() {
    $scope.error = null;

    if (!$scope.phoneOk) {
      $scope.error = 'Please enter a valid mobile number.';
      return;
    }

    $scope.loading = true;
    var payload = angular.copy($scope.form);
    payload.phone = $scope.form.phone; // already digits-only from watcher

    ApiService.orgAddUser(orgId, payload)
    .then(function(res) {
      $scope.created = {
        user          : res.data.user,
        plain_password: res.data.plain_password,
        message       : res.data.message,
      };
    })
    .catch(function(err) {
      var e = err.data && err.data.errors;
      if (e) {
        var msgs = [];
        Object.entries(e).forEach(function(pair) {
          var field = pair[0], errs = pair[1];
          var label = field === 'non_field_errors' ? '' : field.replace(/_/g,' ') + ': ';
          (Array.isArray(errs) ? errs : [errs]).forEach(function(m) {
            msgs.push(label + m);
          });
        });
        $scope.error = msgs.join(' · ');
      } else {
        $scope.error = 'Failed to create user. Please try again.';
      }
    })
    .finally(function() { $scope.loading = false; });
  };

  $scope.copyText = function(text, $event) {
    navigator.clipboard.writeText(text);
    var btn = $event.target;
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(function() { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2000);
  };

  $scope.addAnother = function() {
    $scope.created = null;
    $scope.error   = null;
    $scope.form    = {
      first_name:'', last_name:'', email:'', phone:'',
      role:'WORKER', work_type:'FULL_TIME',
      nationality:'', dob:'', iban:'', bic:'',
      house_number:'', street:'', city:'', country:'', zip_code:'',
    };
    $scope.phoneOk = false;
  };

  $scope.goBack = function() {
    $location.path('/org/' + orgId + '/dashboard');
  };
}]);
