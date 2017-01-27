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
  .component('shapepicker', {
    bindings: {
      key: '@',
      user: '<',
      staticprefix: '@',
      apiprefix: '@',
    },
    templateUrl: 'static/js/cslpwan/shapepicker.html',
    controller: ['$http', '$window', function shapepickerController($http, $window) {

      var me = this;

      me.states = $window.state_data;

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
        console.log(me);
        console.log("shapepickerController running with apiprefix: " + me.apiprefix);
        console.log("shapepickerController running with key: " + me.key);

        me.showMap = false
        //me.map = { center: { latitude: 45, longitude: -73 }, zoom: 8 };
        me.map = { center:{ latitude: 45, longitude: -73 }, bounds: {},
          zoom: 7, pan: true };

        // me.polys = {models: [], path: [],
        //     ,
        //     visible: true,
        //     draggable: false,
        //     geodesic: true
        //   };

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
          fill: {color: "#000000", opacity: 0}};

        me.loaderImg = 'static/img/ajax-transparent.gif';

        me.cities = [];
        me.counties = [];

        me.selectedState = null;
        me.selectedCities = [];
        me.selectedCounties = [];

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

        me.showMap = true;

        console.log("selected state " + me.selectedState + " loading data.");
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
        // console.log("selected cities ");
        // console.log(me.selectedCities);

        me.cityPolysSelected.polys = [];
        for (var i=0; i<me.cityPolys.polys.length; i++){
          for (var j=0; j<me.selectedCities.length; j++){
            if (me.cityPolys.polys[i].properties.GEO_ID == me.selectedCities[j]){
              me.cityPolysSelected.polys.push(me.cityPolys.polys[i]);
            }
          }
        }

      } // selectedCitiesChange
      me.selectedCountiesChange = function(){
        //console.log("selected counties " + me.selectedCounties);
        me.countyPolysSelected.polys = [];
        for (var i=0; i<me.countyPolys.polys.length; i++){
          for (var j=0; j<me.selectedCounties.length; j++){
            if (me.countyPolys.polys[i].properties.GEO_ID == me.selectedCounties[j]){
              me.countyPolysSelected.polys.push(me.countyPolys.polys[i]);
            }
          }
        }
      }

    }] // controller

  });


})(window);
