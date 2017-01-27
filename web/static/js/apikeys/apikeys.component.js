(function() {
'use strict';


angular.module("ApiKeysApp", []);


angular.module("ApiKeysApp")
  .directive('loading', ['$http', function($http){
    //http://stackoverflow.com/questions/17144180/angularjs-loading-screen-on-ajax-request
    return {
         restrict: 'A',
         link: function (scope, elm, attrs)
         {
             scope.isLoading = function () {
                 return $http.pendingRequests.length > 0;
             };
             scope.$watch(scope.isLoading, function (v)
             {
                 if(v){
                     elm.show();
                 }else{
                     elm.hide();
                 }
             });
         }
     };
  }])
  .component('apikeys', {
    bindings: {
      user: '<',
      staticprefix: '@',
      apiprefix: '@'
    },
    templateUrl: 'static/js/apikeys/apikeys.html',
    controller: ['$http', function apikeysController($http) {

      var me = this;
      console.log("apikeyController:");
      console.log(me);
      console.log("apikeyController running with apiprefix: " + me.apiprefix);

      me.remove = function onRemove(idx){
          console.log("onRemove "+me.keys[idx].signature);
          $http.post(
              me.apiprefix+'remove_key',
              {signature:me.keys[idx].signature})
          .then(function success(response){
            me.updateKeys(response.data)
          }, function fail(response){
            console.log("remove_key failed: ");
            console.log(response);
          });
        };
        me.enable = function onEnable(idx){
          console.log("onEnable "+idx);
          $http.post(
              me.apiprefix+'enable_key',
              {signature:me.keys[idx].signature})
          .then(function success(response){
            me.updateKeys(response.data)
          }, function fail(response){
            console.log("enable key failed: ");
            console.log(response);
          });
        };
      me.disable = function onDisable(idx){
        console.log("onDisable "+idx);
        $http.post(
            me.apiprefix+'disable_key',
            {signature:me.keys[idx].signature})
        .then(function success(response){
          me.updateKeys(response.data)
        }, function fail(response){
          console.log("disable key failed: ");
          console.log(response);
        });
      };
      me.updateKeys = function updateKeys(keys){
        // convert unix timestamps to local time
        for (var i in keys){
          var d = new Date(keys[i].created.$date);
          keys[i].created = d.toString();

          if (keys[i].use_info.last_used){
            var d = new Date(keys[i].use_info.last_used.$date);
            keys[i].use_info.last_used = d.toString();
          }else{
            keys[i].use_info.last_used = '-'
          }
        }
        console.log(keys);
        me.keys = keys;
      };
      me.addKey = function onAddKey(){
        $http.post(me.apiprefix+'create_key').then(function success(response){
          console.log("create key: ");
          console.log(response);
          me.updateKeys(response.data.keys);
        }, function fail(response){
          console.log("create_key failed: ");
          console.log(response);
        }
        );
      };

      $http.get(me.apiprefix+'list_keys').then(function success(response){
        console.log("got keys: ");
        console.log(response);
        me.updateKeys(response.data)
      }, function fail(response){
        console.log("list_keys failed: ");
        console.log(response);
      }
      );
    }]

  });


})();
