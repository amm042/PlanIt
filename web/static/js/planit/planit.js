(function(global) {
'use strict';

var planit = {};
planit.addMarker = function(location){
  var me = this;
  var marker = new google.maps.Marker({
          position: location,
          map: me.map,
          draggable: true
        });
  me.markers.push(marker);

  // make all markers visible
  // http://stackoverflow.com/questions/19304574/center-set-zoom-of-map-to-cover-all-visible-markers
  var bounds = new google.maps.LatLngBounds();
  for (var i = 0; i < me.markers.length; i++) {
   bounds.extend(me.markers[i].getPosition());
  }

  if (me.markers.length == 1){

    me.map.setCenter(location);
    me.map.setZoom(17);  // Why 17? Because it looks good.

  } else{
    me.map.fitBounds(bounds);
    //remove one zoom level to ensure no marker is on the edge.
    me.map.setZoom(me.map.getZoom()-1);
  }
};

planit.initMap = function(){
  var me = this;

  console.log("initMap called");
  console.log(document.getElementById('map'));

  me.map = new google.maps.Map(
    document.getElementById('map'), {
            center: {lat: -34.397, lng: 150.644},
            zoom: 8});
  console.log(me.map);

  me.map.addListener('click', function(event){
    me.addMarker(event.latLng);
  });

  me.markers = [];

  var input = document.getElementById('mapSearchBox');
  me.autocomplete = new google.maps.places.Autocomplete(input);

  //planit.map.controls[google.maps.ControlPosition.TOP_LEFT].push(input);

  // Bias the SearchBox results towards current map's viewport.
  me.map.addListener('bounds_changed', function() {
      me.autocomplete.setBounds(me.map.getBounds());
  });

  me.autocomplete.addListener('place_changed', function() {
    var place = me.autocomplete.getPlace();
    if (!place.geometry) {
      // User entered the name of a Place that was not suggested and
      // pressed the Enter key, or the Place Details request failed.
      window.alert("No details available for input: '" + place.name + "'");
      return;
    }

    me.addMarker(place.geometry.location)
    // // If the place has a geometry, then present it on a map.
    // if (place.geometry.viewport) {
    //   me.map.fitBounds(place.geometry.viewport);
    // } else {
    //   me.map.setCenter(place.geometry.location);
    //   me.map.setZoom(17);  // Why 17? Because it looks good.
    // }
    // me.marker.setPosition(place.geometry.location);
    // me.marker.setVisible(true);

  });


}

global.planit = planit

})(window);
