(function(global) {
'use strict';

var map = {};

map.initMap = function(){
  var me = this;

  console.log("initMap called");
  console.log(document.getElementById('map'));

  me.themap = new google.maps.Map(
    document.getElementById('map'), {
            center: {lat: -34.397, lng: 150.644},
            zoom: 8});
  console.log(me.themap);
};
global.map = map;

angular.module("cslpwanApp", ['uiGmapgoogle-maps']);

angular.module("cslpwanApp")
  .config(['uiGmapGoogleMapApiProvider', function(uiGmapGoogleMapApiProvider){
      uiGmapGoogleMapApiProvider.configure({
        key: 'AIzaSyAq1_YAhPeiAWTI6E3BIzb2B77Zk7lUSFc',
        //v: '3.20', //defaults to latest 3.X anyhow
        //libraries: 'weather,geometry,visualization'
      });
    }]
  )// config
  // .config(function($locationProvider) {
  //   $locationProvider.html5Mode(true);
  // }) //config
  .component('shapepicker', {
    bindings: {
      key: '@',
      user: '<',
      staticprefix: '@',
      apiprefix: '@',
    },
    templateUrl: 'static/js/cslpwan/shapepicker.html',
    controller: ['$http', '$window', '$location',
      function shapepickerController($http, $window, $location) {

      var me = this;


      me.states = $window.state_data;

      me.cityCountyReset = function() {
        me.selectedCities = [];
        document.getElementById('cityInput').value = me.selectedCities;
        me.selectedCounties = [];
        document.getElementById('countyInput').value = me.selectedCounties;

        me.selectedCitiesChange();
        me.selectedCountiesChange();
      }
      me.makePolys = function(objs, idprefix){
        var p2 = [];
        var i = 0;
        for (var o in objs){
          // ignore non-polygons for now
          if (objs[o].geometry.type == 'Polygon'){
            // add id for gmaps to each poly
            objs[o]['id'] = idprefix + i;
            i++;
            //console.log(objs[o]);
            p2.push(objs[o]);
          } else if (objs[o].geometry.type == 'MultiPolygon'){
            // create individual polygons.
              for (var j=0; j <objs[o].geometry.coordinates.length; j++){
                var tmp = {
                    'type': 'Feature',
                    'properties': objs[o].properties,
                    'geometry': {'type': 'Polygon'},
                    'id' : idprefix + i};
                i++;
                tmp.geometry.coordinates = objs[o].geometry.coordinates[j];
                //console.log(tmp);
                p2.push(tmp);
              }
          }
        }

        return p2;
      }

      me.$onInit = function(){

        console.log("shapepickerController onInit:");
        console.log("shapepickerController running with apiprefix: " + me.apiprefix);
        console.log("shapepickerController running with key: " + me.key);

        me.show = {
            map : false,
            unselection : false,
            selection : false,
            points : false,
          };
        //me.map = { center: { latitude: 45, longitude: -73 }, zoom: 8 };
        me.map = { center:{ latitude: 45, longitude: -73 }, bounds: {},
          zoom: 7, pan: true };
        me.sampleSize = 500;
        me.points = [];
        $("#numPointsInput").val = me.sampleSize.toString();
        console.log(  $("#numPointsInput").val() );
        me.countyPolysSelected ={
          polys: [],
          fill: {color: "#006000", opacity: 0.6},
          stroke: {color:"#008000", weight:3, opacity: 0.8 }};
        me.cityPolysSelected ={
          polys: [],
          fill: {color: "#000060", opacity: 0.6},
          stroke: {color:"#000080", weight:3, opacity: 0.8 }};

        me.cityPolys = {
          polys: [],
          stroke: {color:"#000080", weight:1, opacity: 0.5 },
          fill: {color: "#000000", opacity: 0}};
        me.countyPolys = {
          polys: [],
          stroke: {color: "#008000", weight:1, opacity: 0.5 },
          fill: {color: "#000000", opacity: 0}
        };

        me.polyEvents = {
          click: function (gPoly, eventName, polyModel) {
              console.log("Poly " + eventName + ": id:" + polyModel.id );
              //console.log(polyModel);

              if (polyModel.id.includes('city')){
                var q= me.selectedCities.indexOf(polyModel.properties.GEO_ID);
                if (q < 0){
                  me.selectedCities.push(polyModel.properties.GEO_ID);
                }else{
                  me.selectedCities.splice(q, 1)
                }
                document.getElementById('cityInput').value = me.selectedCities;
                me.selectedCitiesChange();

              }
              if (polyModel.id.includes('county')){
                var q=  me.selectedCounties.indexOf(polyModel.properties.GEO_ID);
                if (q<0){
                  me.selectedCounties.push(polyModel.properties.GEO_ID);
                }else{
                  me.selectedCounties.splice(q, 1);
                }
                document.getElementById('countyInput').value = me.selectedCounties;
                me.selectedCountiesChange();
              }

            }

        };

        me.loaderImg = 'static/img/ajax-transparent.gif';

        me.cities = [];
        me.counties = [];
        me.selectedState = null;
        me.selectedCities = [];
        me.selectedCounties = [];
        var s = $location.search();
        console.log(s);
        if ('state' in s){
          console.log("Setting state " + s.state);
          me.selectedState = s.state;
          document.getElementById('stateInput').value = me.selectedState;
        }
        if (me.selectedState != null)
          me.selectedStateChange();

        if ('cities' in s && s.cities.length>0){
          console.log("Setting cities");

          me.selectedCities = s.cities.split(",");
          $("#cityInput").val = me.selectedCities;
        }
        if ('counties' in s && s.counties.length>0){
          console.log("Setting counties");
          me.selectedCounties = s.counties.split(",");
          $("#countyInput").val = me.selectedCounties;
        }
        if (me.selectedCities.length > 0)
          me.selectedCitiesChange();
        if (me.selectedCounties.length > 0)
          me.selectedCountiesChange();

        me.busy = false

      } //$onInit

      me.selectedStateChange = function () {

        if (me.selectedState == undefined){
          return;
        }

        var bd = me.states[me.selectedState].bounds;
        // me.bounds = {'ne': {'lat': parseFloat(bd[3]), 'lng': parseFloat(bd[2])},
        //                   'sw': {'lat': parseFloat(bd[1]), 'lng': parseFloat(bd[0])}};
        me.map.bounds = {'northeast': {'latitude': parseFloat(bd[3]), 'longitude': parseFloat(bd[2])},
                          'southwest': {'latitude': parseFloat(bd[1]), 'longitude': parseFloat(bd[0])}};
        me.map.center = me.states[me.selectedState].centroid;

        me.show.map = true;

        console.log("selected state " + me.selectedState + " loading data.");

        // unselect previous city/county selections
        me.selectedCities = [];
        me.selectedCounties = [];

        if ($location.search().state != me.selectedState){
          $location.search({state: me.selectedState,
                            cities: me.selectedCities.toString(),
                            counties: me.selectedCounties.toString()});
          console.log($location);
        }

        me.busy = true;
        // = 'static/img/ajax-loader.gif';
        $http.post(me.apiprefix + 'geonames', {state: me.selectedState, key:me.key})
          .then(function susccess(response){
              console.log('get geonames complete.');
              me.cities = response.data.cities
              me.counties = response.data.counties

              ///console.log("update poly paths:");
              //console.log(p2);
              me.cityPolys.polys = me.makePolys(me.cities, 'state.'+me.selectedState+'.city.poly');
              console.log(me.cityPolys.polys.length + " city polys made");

              me.countyPolys.polys = me.makePolys(me.counties, 'state.'+me.selectedState+'.county.poly');
              console.log(me.countyPolys.polys.length + " county polys made");

              me.show.unselection=true;
              me.show.selection = true;
              // if we loaded these from the locations search, we need
              // to re-fire the events to actualy select the polys, now
              // that we have them.
              if (me.selectedCities.length > 0)
                me.selectedCitiesChange();
              if (me.selectedCounties.length > 0 )
                me.selectedCountiesChange();

              me.busy  = false
              // = 'static/img/ajax-transparent.gif';
          }, function fail(response){
              me.busy = false
              //'static/img/ajax-transparent.gif';
              alert("Failed to get cities and counties.")
              me.selectedState = null;
          }
        );
      }// selectedStateChange
      me.selectedCitiesChange = function(){
        me.cityPolysSelected.polys = [];
        for (var i=0; i<me.cityPolys.polys.length; i++){
          for (var j=0; j<me.selectedCities.length; j++){
            if (me.cityPolys.polys[i].properties.GEO_ID == me.selectedCities[j]){
              me.cityPolysSelected.polys.push(me.cityPolys.polys[i]);
            }
          }
        }
        $location.search({state: me.selectedState,
                          cities: me.selectedCities.toString(),
                          counties: me.selectedCounties.toString()});
      } // selectedCitiesChange
      me.selectedCountiesChange = function(){
        me.countyPolysSelected.polys = [];
        for (var i=0; i<me.countyPolys.polys.length; i++){
          for (var j=0; j<me.selectedCounties.length; j++){
            if (me.countyPolys.polys[i].properties.GEO_ID == me.selectedCounties[j]){
              me.countyPolysSelected.polys.push(me.countyPolys.polys[i]);
            }
          }
        }
        $location.search({state: me.selectedState,
                          cities: me.selectedCities.toString(),
                          counties: me.selectedCounties.toString()});
      }
      me.removeSamplePoints = function(){
        me.show.unselection=true;
        me.show.selection = true;
        me.show.points = false;
        me.points = [];
      }
      me.samplePoints = function (){
        console.log('sampling ' + me.sampleSize + ' points.');

        me.busy = true
        $http.post(me.apiprefix + 'sample', {
            count: me.sampleSize,
            state: me.selectedState,
            cities: me.selectedCities,
            counties: me.selectedCounties,
            key: me.key
          })
          .then(function susccess(response){
            me.show.unselection=false;
            me.show.selection = true;

            me.busy = false;
            console.log(response.data);
            console.log("point id is " + response.data.pointid.toString());
            me.points = response.data.points;
            me.show.points = true;
            var s= $location.search();
            s.pointid = response.data.pointid.toString();
            $location.search (s);

          }, function fail(response){
            me.busy = false
            console.log("FAIL");
            console.log(response);
          });

      } // sample points


    }] // controller

  });


})(window);
