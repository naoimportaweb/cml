<!DOCTYPE html>
<html>

<head>
  <script src="../../public/jquery.min.js"></script>
  <meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {font-family: Arial;}

/* Style the tab */
.tab {
  overflow: hidden;
  border: 1px solid #ccc;
  background-color: #f1f1f1;
}

/* Style the buttons inside the tab */
.tab button {
  background-color: inherit;
  float: left;
  border: none;
  outline: none;
  cursor: pointer;
  padding: 14px 16px;
  transition: 0.3s;
  font-size: 17px;
}

/* Change background color of buttons on hover */
.tab button:hover {
  background-color: #ddd;
}

/* Create an active/current tablink class */
.tab button.active {
  background-color: #ccc;
}

/* Style the tab content */
.tabcontent {
  display: none;
  padding: 6px 12px;
  border: 1px solid #ccc;
  border-top: none;
}
</style>
</head>
<body>
<div id="tbl_maps" class="tab"></div>
<div id='div_contents'></div><script>

function drawEntity(entity, canvas, ctx){
    var fontsize = 9;

    ctx.beginPath();
    ctx.fillStyle = "white";

    ctx.font = "14px Courier";
    ctx.setLineDash([]);

    if(entity.etype == "other"){
        ctx.fillStyle = "yellow";
        ctx.fillRect(entity.x, entity.y, (entity.text_label.length * fontsize) , entity.h);
        ctx.fillStyle = "black";
        ctx.fillText(entity.text_label ,entity.x + 5, entity.y + 13);
        ctx.stroke();
    }
    if(entity.etype == "person"){
        ctx.beginPath();
        ctx.fillStyle = "white";
        ctx.fillRect(entity.x, entity.y, (entity.text_label.length * fontsize) , entity.h);
        ctx.fillStyle = "black";
        ctx.roundRect(entity.x, entity.y, (entity.text_label.length * fontsize) , entity.h, 20);
        
        ctx.fillStyle = "black";
        ctx.fillText(entity.text_label ,entity.x + 5, entity.y + 13);
        ctx.stroke();
    }
    if(entity.etype == "organization"){
        ctx.beginPath();
        ctx.fillStyle = "white";
        ctx.fillRect(entity.x, entity.y, (entity.text_label.length * fontsize) , entity.h);
        ctx.fillStyle = "black";
        ctx.rect(entity.x, entity.y, (entity.text_label.length * fontsize) , entity.h);
        ctx.fillStyle = "black";
        ctx.fillText(entity.text_label ,entity.x + 5, entity.y + 13);
        ctx.stroke();
    }
    if(entity.etype == "link"){
        ctx.beginPath();
        ctx.fillStyle = "blue";
        ctx.setLineDash([5, 3]);
        ctx.strokeStyle = "red";
        for(var i = 0; i < entity.to.length; i++) {
          ctx.moveTo(entity.center_x, entity.center_y - 11);
          ctx.lineTo(entity.to[i].center_x, entity.to[i].center_y  - 11);
        }
        ctx.stroke();
        ctx.beginPath();
        ctx.strokeStyle = "blue";
        for(var i = 0; i < entity.from.length; i++) {
          ctx.moveTo(entity.center_x, entity.center_y - 11);
          ctx.lineTo(entity.from[i].center_x, entity.from[i].center_y - 11);
        }
        ctx.stroke();
        ctx.beginPath();
        ctx.strokeStyle = "black";
        ctx.fillStyle = "white";
        ctx.fillRect(entity.x, entity.y, (entity.text_label.length * fontsize) , entity.h);
        ctx.fillStyle = "blue";
        ctx.fillText(entity.text_label ,entity.x + 5, entity.y + 13);
        ctx.stroke();
    }   
}


function drawMapa(mapa){
    var canvas = document.getElementById("mapa_" + mapa.id);
    var ctx = canvas.getContext("2d");
    ctx.fillStyle = "white";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for(var i = 0; i < mapa.elements.length; i++){
        if(mapa.elements[i].etype == "link")
            drawEntity(mapa.elements[i], canvas, ctx);
    }
    for(var i = 0; i < mapa.elements.length; i++){
        if(mapa.elements[i].etype != "link")
            drawEntity(mapa.elements[i], canvas, ctx);
    }
}

function callbackMap(js){

  $("#tbl_maps").append('<button class="tablinks active" onclick="openRelatinship(event, \'div_'+ js.id +'\', \'tbl_maps\',\'div_contents\')">'+ js.name +'</button>');
  $("#div_contents").append('<div id="div_'+ js.id +'" class="tabcontent" style="display: block;">  </div>');
  
  $("#div_" + js.id).append( '<div id="tbl_maps_'+ js.id +'" class="tab"></div><div id="div_contents_'+ js.id +'"></div><script>');
  // -------------- RELATIONSHIPS
  $("#tbl_maps_" + js.id ).append('<button class="tablinks active" onclick="openRelatinship(event, \'div_maps_relationship_'+ js.id +'\',\'tbl_maps_' + js.id + '\',\'div_contents_' + js.id + '\')">Relationship</button>');
  $("#div_contents_" + js.id).append('<div id="div_maps_relationship_'+ js.id +'" class="tabcontent" style="display: block;">  </div>');

  $("#div_maps_relationship_" + js.id).append( '<canvas id="mapa_'+ js.id +'" name="mapa_'+ js.id +'" width="'+ js.width +'" height="'+ js.height +'" >' );
  // -------------- REFERENCES
  $("#tbl_maps_" + js.id ).append('<button class="tablinks" onclick="openRelatinship(event, \'div_maps_references_'+ js.id +'\',\'tbl_maps_' + js.id + '\',\'div_contents_' + js.id + '\')">References</button>');
  $("#div_contents_" + js.id).append('<div id="div_maps_references_'+ js.id +'" class="tabcontent"> References </div>');

  drawMapa(js);
}

function getMap(id, callback){
   $.ajax({url : "../../service/relationship_load.php?id=" + id, success: function(result){
      callback( JSON.parse( result ) );
    }});
}

function openRelatinship(evt, element_selected_id, tablinks_id, tabcontents_id) {
  var i, tabcontent, tablinks;
  tabcontent = document.getElementById(tabcontents_id).children; 
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }
  tablinks = document.getElementById(tablinks_id).children; 
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }
  document.getElementById(element_selected_id).style.display = "block";
  evt.currentTarget.className += " active";
}

getMap( '<?php echo $_GET["id"]; ?>', callbackMap );
</script>
   
</body>
</html> 
