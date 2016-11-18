(function() {
'use strict';

angular.module("PlanItWebApp")
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
      user: '<'
    },
    templateUrl: 'static/js/apikeys/apikeys.html',
    controller: ['$http', function apikeysController($http) {
      var me = this;
      console.log("apikeyController running.");

      me.remove = function onRemove(idx){
          console.log("onRemove "+idx);
          $http.post('/remove_key/'+idx).then(function success(response){
            console.log("remove_key: ");
            console.log(response);
            me.keys = response.data.keys;
          }, function fail(response){
            console.log("remove_key failed: ");
            console.log(response);
          }
          );
        };
      me.disable = function onDisable(idx){
        console.log("onDisable "+idx);
      };
      me.updateKeys = function updateKeys(keys){
        // convert unix timestamps to local time
        for (var i in keys){
          var d = new Date(keys[i].created.$date);
          keys[i].created = d.toString();
        }
        console.log(keys);
        me.keys = keys;
      };
      me.addKey = function onAddKey(){
        $http.post('/create_key').then(function success(response){
          console.log("create key: ");
          console.log(response);
          me.updateKeys(response.data.keys);
        }, function fail(response){
          console.log("create_key failed: ");
          console.log(response);
        }
        );
      };

      $http.get('/list_keys').then(function success(response){
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
