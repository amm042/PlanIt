$(function(){
    var places = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.whitespace,
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        prefetch: 'places.json'
    });

    // passing in `null` for the `options` arguments will result in the default
    // options being used
    $('#search .typeahead').typeahead(null, {
        name: 'places',
        source: places,
        limit: 30
    });

    var coords = [];
    var marker_points = [];
    var map;
    var places = {}

    var tower_icon = {
        url: "static/img/tower.svg",
        anchor: new google.maps.Point(25,50),
        scaledSize: new google.maps.Size(50,50)
    };

    var iot_red_icon = {
        url: "static/img/iot_red.svg",
        //anchor: new google.maps.Point(25,50),
        scaledSize: new google.maps.Size(10,10)
    };

    var iot_green_icon = {
        url: "static/img/iot_green.svg",
        //anchor: new google.maps.Point(25,50),
        scaledSize: new google.maps.Size(10,10)
    }



    function DownloadControl(controlDiv, map){
        var controlUI = document.createElement('div');
        controlUI.style.backgroundColor = '#fff';
        controlUI.style.border = '2px solid #fff';
        controlUI.style.borderRadius = '3px';
        controlUI.style.boxShadow = '0 2px 6px rgba(0,0,0,.3)';
        controlUI.style.cursor = 'pointer';
        controlUI.style.marginBottom = '22px';
        controlUI.style.textAlign = 'center';
        controlUI.title = 'Click to download the signal data';
        controlDiv.appendChild(controlUI);

        // Set CSS for the control interior.
        var controlText = document.createElement('div');
        controlText.style.color = 'rgb(25,25,25)';
        controlText.style.fontFamily = 'Roboto,Arial,sans-serif';
        controlText.style.fontSize = '16px';
        controlText.style.lineHeight = '38px';
        controlText.style.paddingLeft = '5px';
        controlText.style.paddingRight = '5px';
        controlText.innerHTML = 'Download';
        controlUI.appendChild(controlText);

        // Setup the click event listeners: simply set the map to Chicago.
        controlUI.addEventListener('click', function() {
            if(data_points && data_points.length > 0){
                console.log(data_points);
                downloadJSON(data_points);
            }
        }); 

    }

    function downloadJSON(jsonData){
        let dataStr = JSON.stringify(jsonData);
        let dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);

        let exportFileDefaultName = 'data.json';

        let linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
    }


    function populate(str){
        var addi_str = "";
        if(tower_marker){
            var lat = tower_marker.position.lat();
            var lng = tower_marker.position.lng();
            var tower = {"lat": lat, "lng": lng};
            addi_str = "&tower=" + JSON.stringify(tower);
        }
        var query = "query?name=" + $("#search-box").val() + addi_str;
        console.log(query);
        $.getJSON(query, function(data){
            var coordinates = data["coordinates"];
            coords.length = 0;
            for(var i = 0; i < coordinates.length; i++){
                coords.push({lat: coordinates[i][1], lng: coordinates[i][0]});  
            }
            shape = new google.maps.Polygon({
                paths: coords,
                strokeColor: places[str].color,
                strokeOpacity: 0.5,
                strokeWeight: 2,
                fillColor: places[str].color,
                fillOpacity: 0.3
            });


            shape.setMap(map);

            // allow tower selection
            google.maps.event.addListener(shape, 'click', function(event) {
                place_tower(event.latLng);
            });


            // put all the IoT devices
            var devices = data.points;
            for(var i = 0; i< devices.length; i++){
                //var marker = new google.maps.Marker({
                //    position: {lat: devices[i][1], lng: devices[i][0]},
                //    map: map,
                //    title: "Device " + i.toString(),
                //    icon: iot_green_icon
                //});
                //markers.push(marker);
                marker_points.push({lat: devices[i][1], lng: devices[i][0]});
            }

            console.log(data);
        });

    };


    var data_points = [];
    var has_button = false; 
    $("#search-button").click(function(){
        if(marker_points){
            if(data_points){
                data_points.length = 0;
            } else{
                data_points = [];
            }
            var base;
            if(!tower_marker){
                base = map.getCenter();
            } else {
                base = tower_marker.position; 
            }
            base_pos = {lat: base.lat(), lng: base.lng()};

            for(var i = 0; i < marker_points.length; i++){
                var marker = marker_points[i];
                var pos = {lat: marker.lat, lng: marker.lng};
                $.ajax({
                    type: 'POST',
                    url: '/simulate',
                    data: JSON.stringify({from: base_pos, to: pos, index: i}),
                    success: function(data) {
                        if(data.lat){
                            //var power = Number(data["Signal power level"].replace("dbm", ""));
                            data_points.push(data);
                            var index = data.index;
                            if(data["snr"][0] < -10){
                                var marker = new google.maps.Marker({
                                    position: {lat: marker_points[index].lat, lng: marker_points[index].lng},
                                    map: map,
                                    title: "Device " + i.toString(),
                                    icon: iot_red_icon
                                });
                                                //markers.push(marker);
                            } else{
                                var marker = new google.maps.Marker({
                                    position: {lat: marker_points[index].lat, lng: marker_points[index].lng},
                                    map: map,
                                    title: "Device " + i.toString(),
                                    icon: iot_green_icon
                                });
                                               //markers.push(marker); 
                            } 
                            google.maps.event.trigger(map, "resize");
                        }
                        //Plotly.redraw(graphDiv);      
                    },
                    contentType: "application/json",
                    dataType: 'json'
                });

            }

            if(!has_button){
                var downloadControlDiv = document.createElement('div');
                var downloadControl = new DownloadControl(downloadControlDiv, map);

                downloadControlDiv.index = 1;
                map.controls[google.maps.ControlPosition.TOP_CENTER].push(downloadControlDiv);
                has_button = true;
            }
        }
    });


    $('#search .typeahead').bind('typeahead:select', function (ev, suggestion) {
        if(places[suggestion]){
            var color = places[suggestion].color;
        } else {
            var color = Please.make_color({format:"hex"});
        }

        places[suggestion] = {"name": suggestion, "color": color};

        // add to the labels
        $("#place-selection").append('<span class="tag label label-info" style="background-color:' + color + '">' + suggestion + '<a class="remove fa fa-times"></a></span>');

        populate(suggestion);
        console.log(suggestion);
        // clear the search input
        $('.typeahead').typeahead('val', '');
    });

    var tower_marker;
    function place_tower(loc){
        if(tower_marker){
            tower_marker.setMap(null);
        }
        tower_marker = new google.maps.Marker({
            position:loc,
            map: map,
            icon: tower_icon
        });
        //map.setCenter(loc);
    }


    map = new google.maps.Map(document.getElementById('map'), {
        center: {lat: 40.9645, lng: -76.8844},
        zoom: 13
    });

    google.maps.event.addListener(map, 'click', function(event) {
        place_tower(event.latLng);
    });

});
