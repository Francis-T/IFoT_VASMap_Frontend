// RSU_DATA = [
//   [
//       { sw_id: "SW_1", id: "RSU_1", lon : 135.728923, lat : 34.729994 },
//       { sw_id: "SW_1", id: "RSU_2", lon : 135.729658, lat : 34.729951 }, 
//       { sw_id: "SW_1", id: "RSU_3", lon : 135.730424, lat : 34.729924 }, 
//       { sw_id: "SW_1", id: "RSU_4", lon : 135.731765, lat : 34.729814 }, 
//       { sw_id: "SW_1", id: "RSU_5", lon : 135.732436, lat : 34.729779 }, 
//       { sw_id: "SW_1", id: "RSU_6", lon : 135.733042, lat : 34.729726 }
//   ],
//   [
//       { sw_id: "SW_2", id: "RSU_7", lon : 135.731467, lat : 34.731135 },
//       { sw_id: "SW_2", id: "RSU_8", lon : 135.731408, lat : 34.730840 },
//       { sw_id: "SW_2", id: "RSU_9", lon : 135.731322, lat : 34.730439 },
//       { sw_id: "SW_2", id: "RSU_10", lon : 135.731065, lat : 34.729346 },
//       { sw_id: "SW_2", id: "RSU_11", lon : 135.730706, lat : 34.729046 },
//       { sw_id: "SW_2", id: "RSU_12", lon : 135.730035, lat : 34.729020 }
//   ],
// ];

var selected_rsu_list = [];
var map = null;
var overlays = []
var global_chart_data = {};
var RSU_DATA = [];

function getRoadColor(idx) {
  var colors = [
      '#FFFFFF',
      '#EE8888',
  ];

  return colors[idx];
}

function createMap(params) {
    var markers = []

    for (var rsu of RSU_DATA) {
        let m = new ol.Feature({
          geometry: new ol.geom.Point( ol.proj.fromLonLat([rsu.lon, rsu.lat])), 
          name : rsu.rsu_id,
          lon : rsu.lon,
          lat : rsu.lat,
        });

        m.setStyle(new ol.style.Style({
            image: new ol.style.Icon(({
                crossOrigin: 'anonymous',
                src: params.marker_path,
                color: getRoadColor(0),
            }))
        }));

        markers.push(m)
    }

    var vectorSource = new ol.source.Vector({ features : markers });
    map = new ol.Map({
        target: 'map',
        layers: [
          new ol.layer.Tile({
            source: new ol.source.OSM()
          }),
          new ol.layer.Vector({
            source: vectorSource,
          }),
        ],
        view: new ol.View({
          //center: ol.proj.fromLonLat([135.731195, 34.729879]),
          center: ol.proj.fromLonLat([-86.7867889, 36.1655724]),
          zoom: 12
        }),
        interactions: ol.interaction.defaults({
          doubleClickZoom :false,
          dragAndDrop: false,
          dragPan: false,
          keyboardPan: false,
          keyboardZoom: false,
          mouseWheelZoom: false,
          pointer: false,
        }),
    });

    addMapInteractions(map, vectorSource);

    return map;
}

function addMapInteractions(map, vectorSource) {
    // a normal select interaction to handle click
    var select = new ol.interaction.Select();
    map.addInteraction(select);


    // a DragBox interaction used to select features by drawing boxes
    var dragBox = new ol.interaction.DragBox();

    map.addInteraction(dragBox);

    dragBox.on('boxend', function() {
        // features that intersect the box are added to the collection of
        // selected features
        var extent = dragBox.getGeometry().getExtent();

        let timerId = setTimeout(logList, 100);
        vectorSource.forEachFeatureIntersectingExtent(extent, function(feature) {
            let selection = document.getElementById("rsu_selection");
            // let list_item = document.createElement("li");
            // list_item.innerHTML = feature.values_.name + " " + feature.values_.sw_id;
            // let hidden = document.createElement("input");
            selected_rsu_list.push({
                id: feature.values_.name,
                sw_id: feature.values_.sw_id,
                lon: feature.values_.lon,
                lat: feature.values_.lat,
            });

            clearTimeout(timerId);
            timerId = setTimeout(logList, 100);
            // selection.appendChild(list_item);
            return;
        });
    });

    // clear selection when drawing a new box and when clicking on the map
    dragBox.on('boxstart', function() {
        let selection = document.getElementById("rsu_selection");
        selection.innerHTML = "";
        selected_rsu_list = []
        return;
    });

    return map;
}

function logList() {
    let selection = document.getElementById("rsu_selection");
    for (let i = 0; i < selected_rsu_list.length; i++) {
        if (i > 0) {
            selection.innerHTML += ", ";
        }
        selection.innerHTML += selected_rsu_list[i].id;
    }
    return true;
}

function addRSUOverlay(rsu_id, data, max_data, min_data) {
    target_rsu_info = null;
    for (rsu_info of RSU_DATA) {
        if (rsu_info.rsu_id == rsu_id) {
            target_rsu_info = rsu_info;
            break;
        }
    }

    if (target_rsu_info == null) {
        console.log("RSU not found: " + rsu_id);
        return;
    }

    color_scale = chroma.scale(['#ffa500AA', '#008000AA']);
    scale_value = (data - min_data) / (max_data - min_data);

    let elem = document.createElement("div");
    let text = document.createElement("div");
    elem.classList.add('marker');
    elem.id = target_rsu_info.id;
    elem.style.backgroundColor = color_scale(scale_value);
    text.innerHTML = data.toFixed(0);
    text.classList.add("marker-text");

    elem.appendChild(text); 

    var marker = new ol.Overlay({
        position: ol.proj.fromLonLat([target_rsu_info.lon, target_rsu_info.lat]),
        positioning: "top-left",
        element: elem,
        offset: [-32.5, -36],
    });
    map.addOverlay(marker);
    overlays.push(marker);

    console.log(overlays);

    return;
}

function clearRSUOverlays() {
    for (ov of overlays) {
        map.removeOverlay(ov);
    }

    return;
}

function displayAverageSpeedData(result) {
    let data = result.data;

    let rsu_key_list = Object.keys(data);
    let table = document.getElementById("tbl_results_body");

    /* Clear the table first */
    table.innerHTML = "";

    clearRSUOverlays();

    let max_speed = 0;
    let min_speed = 999;

    for (rsu_key of rsu_key_list) {
        let speed = data[rsu_key];
        if (speed > max_speed) {
            max_speed = speed;
        }

        if (speed < min_speed) {
            min_speed = speed;
        }
    }

    for (rsu_key of rsu_key_list) {
        let tbl_row = document.createElement("tr");
        let tbl_rsu_id = document.createElement("td");
        let tbl_speed = document.createElement("td");

        /* Fill in the <td> elements */
        tbl_rsu_id.innerHTML = rsu_key;
        let speed = data[rsu_key];
        tbl_speed.innerHTML = speed.toFixed(2) + " kph";

        /* Put <td> elements in <tr> */
        tbl_row.appendChild(tbl_rsu_id);
        tbl_row.appendChild(tbl_speed);

        /* Put <tr> in the table body */
        table.appendChild(tbl_row);

        addRSUOverlay(rsu_key, speed, max_speed, min_speed);
    }

    console.log(`Max: ${max_speed}, Min: ${min_speed}`);
    return;
}

function requestAverageSpeeds() {
    console.log(selected_rsu_list);

    /* Get the split count */
    let split_count = parseInt($("#nmb_split_count").val());

    let target_rsu_list = [];
    for (rsu_item of selected_rsu_list) {
        target_rsu_list.push(rsu_item.id);
    }

    $.ajax({
        url : "get_ave_speed_data",
        data : { 'rsu_list' : JSON.stringify(target_rsu_list),
                 'split_count' : split_count },
        method : "POST",
        success : function(data) {
            let result = JSON.parse(data);

            /* Display the average speed data in the map */
            displayAverageSpeedData(result);

            /* Request the execution times for the previous task too */
            requestExecTimeData(result.unique_id);

            return;
        },
        beforeSend : function() {
            $("#btn_query_speeds").attr("disabled", true);
        },
    }).always(function (){
            $("#btn_query_speeds").attr("disabled", false);
    });
    return;
}

/********************************************
 *  Time Execution Data Charting Functions  *
 ********************************************/
function displayExecTimeData(unique_id, result) {
    /* Prepare the bar chart data */
    let chart_labels = [];
    let start_time_list = [];
    let proc_time_list = [];
    let earliest_start = Infinity;
    let latest_end = 0;

    /* Get the earliest start time */
    let table = document.getElementById("tbl_exec_times_body");
    table.innerHTML = "";
    for (task of result) {
        base_start = (parseFloat(task.start_time) / 1000000.0);
        if (base_start < earliest_start) {
            earliest_start = base_start;
        }

        let tbl_row = document.createElement("tr");
        let tbl_operation = document.createElement("td");
        let tbl_start_time = document.createElement("td");
        let tbl_end_time = document.createElement("td");
        let tbl_duration = document.createElement("td");

        /* Fill in the <td> elements */
        tbl_operation.innerHTML = task.operation;
        tbl_start_time.innerHTML = task.start_time;
        tbl_end_time.innerHTML = task.end_time;
        tbl_duration.innerHTML = task.duration;

        /* Put <td> elements in <tr> */
        tbl_row.appendChild(tbl_operation);
        tbl_row.appendChild(tbl_start_time);
        tbl_row.appendChild(tbl_end_time);
        tbl_row.appendChild(tbl_duration);

        /* Put <tr> in the table body */
        table.appendChild(tbl_row);
    }

    for (task of result) {
        chart_labels.push(task.operation);

        base_start = (parseFloat(task.start_time) / 1000000.0);
        task_start = base_start - earliest_start;
        start_time_list.push(task_start);

        base_end = (parseInt(task.end_time) / 1000000.0);
        norm_end = base_end - earliest_start;
        task_end = norm_end - task_start;
        if (norm_end > latest_end) {
            latest_end = norm_end;
        }
        proc_time_list.push(task_end);
    }

    global_chart_data = {
        labels : chart_labels,
        datasets: [
            {
                label: 'Start Time',
                backgroundColor: '#FFFFFF00',
                data: start_time_list,
            },
            {
                label: 'Processing Time',
                backgroundColor: '#006600FF',
                data: proc_time_list,
            }
        ],
    };

    $("#summ_exec_times").html(`Overall Time: ${latest_end}`);

    if (window.bar_chart != undefined) {
        console.log("Chart exists");
        window.bar_chart.data = global_chart_data;
        window.bar_chart.options.title.text = `Task Execution Times (Task: ${unique_id})`;
        window.bar_chart.options.scales.xAxes[0].ticks.max = latest_end;
        window.bar_chart.scales["x-axis-0"].max = latest_end;
        window.bar_chart.update();
        return;
    }

    /* TODO Create the chart */
    let canvas =  document.getElementById('timing_chart');
    let ctx = canvas.getContext('2d');
    // ctx.clearRect(0, 0, canvas.width, canvas.height);
    window.bar_chart = new Chart(ctx, {
        type: 'horizontalBar',
        data: global_chart_data,
        options: {
            title: {
                display: true,
                text: `Task Execution Times (Task: ${unique_id})`,
            },
            tooltips: {
                mode: 'index',
                intersect: false
            },
            responsive: false,
            scales: {
                xAxes: [{
                    stacked: true,
                    ticks: {
                        min: 0,
                        max: latest_end,
                    },
                }],
                yAxes: [{
                    stacked: true
                }]
            }
        }
    });
    let chart_elem = document.getElementById('timing_chart');
    chart_elem.style.display = 'inline';

    return;
}

function requestExecTimeData(unique_id) {
    $.ajax({
        url : `get_exec_time/${unique_id}`,
        method : "GET",
        success : function(data) {
            let result = JSON.parse(data);
            displayExecTimeData(unique_id, result['exec_time_logs'][unique_id]);
            return;
        },
    });
    return;
}

function loadMapData(map_params) {
    $.ajax({
        url : "get_rsu_list",
        method: "GET",
        success : function (data) {
            RSU_DATA = JSON.parse(data);
            console.log("Creating the map");
            createMap(map_params);
            return;
        },
    });
}


