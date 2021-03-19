
const DEBUG = true;

var currentBraceleteId = null;
const timerDelayMS = 3000;

var log = function (x) {
  if (DEBUG) {
    console.log(x);
  }
};

var drawTemperature = function (tempDataArray) {
  log("drawTemperature...");
  log(tempDataArray);
  x = [];
  y = [];
  for (let dat of tempDataArray) {
    //log(dat);
    x.push(dat.time);
    y.push(dat.temperature);
  }
  //log(x); log(y);

  var grapthElem = document.getElementById('tempGraph');

  var data = [{ x: x, y: y, mode: 'lines+markers', line: { color: '#007bff', width: 4 }, marker: { size: 10 } }];
  var layout = {
    showlegend: false,
    // horizontal threshold line
    shapes: [{
      type: 'line',
      xref: 'paper',
      x0: 0, //x[0],
      y0: TEMPERATURE_THRESHOLD,
      x1: 100, //x[x.length-1],
      y1: TEMPERATURE_THRESHOLD,
      opacity: 0.3,
      line: { color: 'rgb(255, 0, 0)', width: 4 /*, dash:'dot' */ }
    }]
  }; //{ title: 'T, C', showlegend: false };
  //var params = {staticPlot: true};
  var params = { margin: { t: 0 } };
  Plotly.newPlot(grapthElem, data, layout, params);
}

var getUsers = function () {
  log("getUsers...");

  var xmlhttp = new XMLHttpRequest();
  var url = "/api/users";

  xmlhttp.onreadystatechange = function () {
    if (this.readyState == 4 && this.status == 200) {
      var arr = JSON.parse(this.responseText);
      log(arr);

      // clear table
      var table = document.getElementById("usersTable");
      if (table !== null) {
        var tableHeaderRowCount = 1;
        var rowCount = table.rows.length;
        for (var i = tableHeaderRowCount; i < rowCount; i++) {
          table.deleteRow(tableHeaderRowCount);
        }
        // add data
        for (let dat of arr.data) {
          log(dat);
          var tr = document.createElement('tr');
          table.tBodies[0].appendChild(tr);
          let add_td = function (tr, info) {
            var d = document.createElement('td');
            tr.appendChild(d);
            d.innerHTML = info;
          };
          //let bracelet_id = dat.bracelet_id;
          add_td(tr, dat.bracelet_id);
          add_td(tr, dat.name);
          add_td(tr, dat.user_class);
          add_td(tr, dat.email);
          var temperature = dat.temperature;
          add_td(tr, dat.temperature);
          add_td(tr, dat.time);

          if (dat.temperature > TEMPERATURE_THRESHOLD) {
            tr.style.backgroundColor = '#f9acac';
          }

          tr.addEventListener('click', function (event) {
            log('tr click' + dat.bracelet_id);
            //var targetElement = event.target;
            //log(targetElement);
            getUserTemperatureData(dat.bracelet_id);
          })
        }
      }
    }
  };
  xmlhttp.open("GET", url, true);
  xmlhttp.send();

};

var getUserTemperatureData = function (id) {
  log("getUserTemperatureData..." + id);

  currentBraceleteId = id;

  var xmlhttp = new XMLHttpRequest();
  var url = "/api/data?id=" + id;

  xmlhttp.onreadystatechange = function () {
    if (this.readyState == 4 && this.status == 200) {
      var arr = JSON.parse(this.responseText);
      log(arr);
      drawTemperature(arr.data);
    }
  };
  xmlhttp.open("GET", url, true);
  xmlhttp.send();
};

function myTimer() {
  log("onTimer...")
  //getUserTemperatureData(currentBraceleteId);
}

window.onload = function () {
  log('Start...');
  getUsers();
  getUserTemperatureData(1);

  let res = window.setInterval(myTimer, timerDelayMS);
  log(res);
};
