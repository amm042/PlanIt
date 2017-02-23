(function(global) {
'use strict';

// var map = {};

// map.initMap = function(){
//   var me = this;
//
//   console.log("initMap called");
//   console.log(document.getElementById('map'));
//
//   me.themap = new google.maps.Map(
//     document.getElementById('map'), {
//             center: {lat: -34.397, lng: 150.644},
//             zoom: 8});
//   console.log(me.themap);
// };
// global.map = map;

// googlemaps fitbounds helper
// http://shades-of-orange.com/post/Remove-The-Padding-From-The-Google-Map-API-v3-fitBounds()-Method
function myFitBounds(myMap, bounds) {
    myMap.fitBounds(bounds); // calling fitBounds() here to center the map for the bounds

    var overlayHelper = new google.maps.OverlayView();
    overlayHelper.draw = function () {
        if (!this.ready) {
            var extraZoom = getExtraZoom(this.getProjection(), bounds, myMap.getBounds());
            if (extraZoom > 0) {
                myMap.setZoom(myMap.getZoom() + extraZoom);
            }
            this.ready = true;
            google.maps.event.trigger(this, 'ready');
        }
    };
    overlayHelper.setMap(myMap);
}

function getExtraZoom(projection, expectedBounds, actualBounds) {

    // in: LatLngBounds bounds -> out: height and width as a Point
    function getSizeInPixels(bounds) {
        var sw = projection.fromLatLngToContainerPixel(bounds.getSouthWest());
        var ne = projection.fromLatLngToContainerPixel(bounds.getNorthEast());
        //return new google.maps.Point(Math.abs(sw.y - ne.y), Math.abs(sw.x - ne.x));
        return new google.maps.Point( Math.round(10000 * Math.abs(sw.y - ne.y)) / 10000, Math.round(10000 * Math.abs(sw.x - ne.x)) / 10000 );
    }

    var expectedSize = getSizeInPixels(expectedBounds),
        actualSize = getSizeInPixels(actualBounds);

    if (Math.floor(expectedSize.x) == 0 || Math.floor(expectedSize.y) == 0) {
        return 0;
    }

    var qx = actualSize.x / expectedSize.x;
    var qy = actualSize.y / expectedSize.y;
    var min = Math.min(qx, qy);

    if (min < 1) {
        return 0;
    }

    return Math.floor(Math.log(min) / Math.LN2 /* = log2(min) */);
}

angular.module("lpwanApp", ['uiGmapgoogle-maps']);

angular.module("lpwanApp")
  .config(['uiGmapGoogleMapApiProvider', function(uiGmapGoogleMapApiProvider){
      uiGmapGoogleMapApiProvider.configure({
        key: 'AIzaSyAq1_YAhPeiAWTI6E3BIzb2B77Zk7lUSFc',
        //v: '3.20', //defaults to latest 3.X anyhow
        libraries: 'places, drawing'
      });
    }]
  )// config
  // .config(function($locationProvider) {
  //   $locationProvider.html5Mode(true);
  // }) //config
  .component('planit', {
    bindings: {
      key: '@',
      user: '<',
      staticprefix: '@',
      apiprefix: '@',
    },
    templateUrl: 'static/js/planit/planit.html',
    controller: ['$http', '$window', '$location', '$timeout', '$scope',
      function planitController($http, $window, $location, $timeout, $scope) {

      var me = this;

      me.placeToMaker = function (place, id) {
        if (!place || place == 'undefined' ) {
          return;
        }
        var marker = {
          id: id,
          active: 'active',
          place_id: place.place_id,
          name: place.name,
          address: place.formatted_address,
          geometry:{ // GeoJSON
            type: 'Point',
            coordinates:[place.geometry.location.lng(), place.geometry.location.lat()]
            },
          ll: place.geometry.location,
          latlng: place.geometry.location.toString()
        };
        return marker;
      } // placeToMaker
      me.mouseEventToMarker = function (mevt, id) {
        if (!mevt || mevt == 'undefined' ) {
          return;
        }

        var marker = {
          id: id,
          active: 'active',
          geometry:{ // GeoJSON
            type: 'Point',
            coordinates:[mevt.latLng.lng(), mevt.latLng.lat()]
            },
          ll: mevt.latLng,
          latlng: mevt.latLng.toString()
        };
        return marker;
      } // mouseEventToMarker
      me.removeBase = function(idx){
        me.circles[me.basestations[idx].id].setMap(null);
        delete me.circles[me.basestations[idx].id];

        me.basestations.splice(idx, 1);
        if (me.basestations.length==1){
          me.map.fitPoints = false;
          me.map.center = $.extend({}, me.basestations[0].geometry);
          me.map.zoom = 9;
        }else{
          me.map.fitPoints = true;
        }
      }//removeBase
      me.removeAllBase = function(){
        for (var i=0; i<me.basestations.length; i++){
          me.circles[me.basestations[i].id].setMap(null);
        }
        me.circles = [];
        me.basestations = [];
        me.map.fitPoints = false;
        //me.map.center = $.extend({}, marker.geometry);
        //me.map.zoom = 14;
      }//
      me.addCircle = function(gmap, marker){
        //add coverage circle to gmap using given marker
        var c = new google.maps.Circle({
          center: marker.ll,
          clickable: false,
          draggable: false,
          fillOpacity: 0.2,
          strokeColor: 'DarkBlue',
          fillColor: 'Blue',
          strokeWeight: 1,
          map: gmap,
          visible: true,
          radius: me.radius*1000,
        })
        me.circles[marker.id] = c;
        //marker.circle = c
      }
      me.$onInit = function(){
        console.log("planitController onInit:");
        console.log("planitController running with apiprefix: " + me.apiprefix);
        console.log("planitController running with key: " + me.key);

        me.states = $window.state_data;
        me.basestations = [];
        me.points = [];
        me.baseid = 0;
        me.radius = 30;
        me.circles = {};

        me.showHideButtonText= 'Hide';
        me.showHideResultText= 'Hide';
        me.show = {
            map : true,
            points : true,
            basestations:true,
          };

        me.map = { center: { latitude: 38.0959, longitude: -95.1429 },
                  bounds: {},
                  zoom: 4,
                  pan: true,
                  fitPoints: false,
                  control: {},
                  events:{
                    dblclick: function(gmap, eventName, args){
                      $scope.$apply(function() {
                        var marker = me.mouseEventToMarker(args[0], me.baseid++)
                        me.addCircle(me.map.control.getGMap(), marker);
                        for (var i=0; i< me.basestations.length; i++){
                          me.basestations[i].active = '';
                        }
                        me.basestations.push(marker);
                        console.log("map dblclick");
                        if (me.basestations.length==1){
                          me.map.fitPoints = false;
                          me.map.center = $.extend({}, marker.geometry);
                          me.map.zoom = 9;
                        }else{
                          me.map.fitPoints = true;
                        }
                        console.log(me.basestations);
                      })}
                    }, // map.events
                  searchTemplate: 'searchbox.tpl.html',
                  searchEvents: {
                    places_changed: function(searchBox){
                      console.log("places_changed");
                      var place = searchBox.getPlaces();
                      console.log(place[0]);
                      var marker = me.placeToMaker(place[0], me.baseid++)
                      console.log(marker);

                      me.addCircle(me.map.control.getGMap(), marker);
                      for (var i=0; i< me.basestations.length; i++){
                        me.basestations[i].active = '';
                      }
                      me.basestations.push(marker)

                      if (me.basestations.length==1){
                        me.map.fitPoints = false;
                        me.map.center = $.extend({}, marker.geometry);
                        me.map.zoom = 9;
                      }else{
                        me.map.fitPoints = true;
                      }
                      console.log(me.basestations);
                    }
                  }, // map.serchEvents
                  markerEvents: {
                    dragend: function(marker, eventName, model, args){
                      $scope.$apply(function() {
                        console.log("marker dragend");
                        console.log(marker);
                        console.log(model);
                        console.log(args);

                        me.circles[model.id].setMap(null);
                        delete me.circles[model.id];

                        model.latlng = args[0].latLng.toString();
                        model.ll = args[0].latLng;
                        me.addCircle(me.map.control.getGMap(), model);
                      })
                    },
                    click: function(marker, eventName, model, args){
                      console.log("marker click " + args[0].latLng.toString());
                      console.log(model);
                      console.log(args);
                      for (var i=0; i< me.basestations.length; i++){
                        me.basestations[i].active = '';
                      }
                      model.active= 'active';
                    }
                  }// map.markerEvents

                }; // map

        me.sampleSize = 500;

        me.numRuns = 2;
        me.basestations = [];
        me.freqMhz = 900.0;
        me.lossThreshold = 148;
        me.txHeight = 5;
        me.rxHeight = 1;
        me.itwomModel = 'city';

        me.loaderImg = 'static/img/ajax-transparent.gif';
        if('pointid' in $location.search()){
          me.samplePoints();
        }
        if('analysisid' in $location.search()){
          // create a fake analyzeresponse
          me.analyzeResponse = {jobid: 0, id: $location.search().analysisid};
          me.checkAnalyzeResult();
        }
        if ($http.pendingRequests.length == 0){
          me.busy = false;
        }
      } //$onInit
      me.showLocation = function(){
        var gmap = me.map.control.getGMap();
        var bounds = gmap.getBounds();
        console.log(gmap.getCenter().toString());
        console.log(gmap.getZoom());
      }
      me.hideSamplePoints = function(){
        if (me.show.points){
          me.show.points = false;
          me.showHideButtonText = 'Show';
        }else{
          me.map.fitPoints = false;
          me.show.points = true;
          me.showHideButtonText = 'Hide';
        }
      }
      me.samplePoints = function (clearexisting=false){
        if (clearexisting){
          me.points = [];
          $location.search('pointid', null);
        }

        if ('getGMap' in me.map.control){
          var gmap = me.map.control.getGMap();
          var bounds = gmap.getBounds();
        }
        console.log('sampling ' + me.sampleSize + ' points.');
        console.log("search is");
        console.log($location.search());
        me.busy = true
        $http.post(me.apiprefix + 'sample', {
            pointid: $location.search().pointid,
            count: me.sampleSize,
            basestations: me.basestations,
            bounds: bounds,
            key: me.key
          })
          .then(function susccess(response){
            me.busy = false;

            console.log(response.data);
            if ('basestations' in response.data){
              me.map.fitPoints = true;
              me.basestations = response.data.basestations;
              me.show.basestations = true;
              me.baseid= me.basestations.length;
            }
            if ('pointid' in response.data){
              console.log("point id is " + response.data.pointid.toString());
              me.map.fitPoints = true;
              me.show.points = true;
              me.showHideButtonText = 'Hide';
              me.points = response.data.points;
              $location.search('pointid', response.data.pointid.toString());
            }
            /*
            if ('getGMap' in me.map.control){
              // use bounds to fit map if we have it.
              me.map.fitPoints = false;
              var gmap = me.map.control.getGMap();
              console.log('set bounds to:');
              console.log(response.data.args.bounds);
              //gmap.fitBounds(response.data.args.bounds);
              var b = response.data.args.bounds;
              myFitBounds(gmap, new google.maps.LatLngBounds(
                {lat:b.north, lng:b.west}, {lat:b.south, lng:b.east}));
              console.log('bounds are:');
              console.log(gmap.getBounds().toString());
            }
          */
            $('.nav-tabs a[data-target="#analyze"]').tab('show');
          }, function fail(response){
            me.busy = false;
            console.log("FAIL");
            console.log(response);
          });

      } // sample points

      me.checkAnalyzeResult = function(){
          $http.post(me.apiprefix + 'analyzeResult', {
              key: me.key,
              jobid: me.analyzeResponse.jobid,
              id: me.analyzeResponse.id}).then(function success(response){
                if (response.data.complete){
                  console.log("got analyzeResult [complete].");
                  console.log(response);
                  me.busy = false

                  $location.search('analysisid', response.data.id);
                  me.coverage = response.data.coverage
                  me.loss = response.data.loss

                  // remove any existing overlays.
                  if (me.overlay != undefined){
                    me.overlay.setMap(null);
                    delete me.overlay;
                  }

                  var gmap = me.map.control.getGMap();

                  me.overlay = new google.maps.GroundOverlay(
                    response.data.contour,
                    response.data.args.bounds,
                    {opacity: 0.5}
                  )
                  me.overlay.setMap(gmap);
                  me.showHideResultText= 'Hide';
                }else{
                  console.log("got analyzeResult [NOT complete].");
                  console.log(response);
                  $timeout(me.checkAnalyzeResult, 100);
                }

              }, function fail(response){
                me.busy = false
                console.log("failed to get analyzeResult.");
                console.log(response);
              });
        };//checkAnalyzeResult
      me.hideAnalyze = function(){
        if (me.overlay.getMap() != null){
          me.overlay.setMap(null);
          me.showHideResultText = 'Show';
        }else{
          var gmap = me.map.control.getGMap();
          me.overlay.setMap(gmap);
          me.showHideResultText = 'Hide';
        }
      }//clearAnalyze
      me.analyze = function(){
        me.busy = true;
        var gmap = me.map.control.getGMap();
        var bounds = gmap.getBounds();
        //console.log(gmap.getBounds().toJSON());
        $http.post(me.apiprefix + 'analyze', {
          static: me.staticprefix,
          key: me.key,
          freq: me.freqMhz,
          model: me.itwomModel,
          basestations: me.basestations,
          lossThreshold: me.lossThreshold,
          txHeight: me.txHeight,
          rxHeight: me.rxHeight,
          model: me.itwomModel,
          pointid: $location.search().pointid,
          //bounds: JSON.stringify (bounds)
          bounds: bounds
        }).then(function success(response){

          me.busy = true
          console.log("analyze response");
          console.log(response);
          me.analyzeResponse = response.data;

          if (me.analyzeResponse.complete){
            me.busy = false

            me.coverage = response.data.coverage
            me.loss = response.data.loss
            $location.search('analysisid', response.data.id);
            // remove any existing overlays.
            if (me.overlay != undefined){
              me.overlay.setMap(null);
              delete me.overlay;
            }

            me.overlay = new google.maps.GroundOverlay(
              response.data.contour,
              bounds,
              {opacity: 0.5}
            )
            me.overlay.setMap(gmap);
          }else{
            $timeout(me.checkAnalyzeResult, 100);
          }

        }, function fail(response){
          me.busy = false
          console.log("FAIL");
          console.log(response);
        });

      } //analyze

    }] // controller

  });


})(window);
