
Listar todos os mapas e dar permissao de busca
<?php
require_once dirname(dirname(__DIR__)) . "/controller/relationship/relationship.php";
$mapac = new RelationshipController( $_GET['id'], $_GET['domain'] );
?>

<html>
<head>
    <script>
        var mapa = <?php echo json_encode( $mapac->getMapa()->toJson() ) ; ?>;
        

        function drawEntity(entity){
            const canvas = document.getElementById("mapa");
            const ctx = canvas.getContext("2d");
            ctx.beginPath();
            ctx.fillStyle = "white";

            ctx.font = "16px Courier";
            ctx.setLineDash([]);

            if(entity.etype == "other"){
                ctx.fillStyle = "yellow";
                ctx.fillRect(entity.x, entity.y, (entity.text_label.length * 10) + 10, entity.h);
                ctx.fillStyle = "black";
                ctx.fillText(entity.text_label ,entity.x + 5, entity.y + 13);
                ctx.stroke();
            }
            if(entity.etype == "person"){
                ctx.beginPath();
                ctx.fillStyle = "white";
                ctx.fillRect(entity.x, entity.y, (entity.text_label.length * 10) + 10, entity.h);
                ctx.fillStyle = "black";
                ctx.roundRect(entity.x, entity.y, (entity.text_label.length * 10) + 10, entity.h, 20);
                
                ctx.fillStyle = "black";
                ctx.fillText(entity.text_label ,entity.x + 5, entity.y + 13);
                ctx.stroke();
            }
            if(entity.etype == "organization"){
                ctx.beginPath();
                ctx.fillStyle = "white";
                ctx.fillRect(entity.x, entity.y, (entity.text_label.length * 10) + 10, entity.h);
                ctx.fillStyle = "black";
                ctx.rect(entity.x, entity.y, (entity.text_label.length * 10) + 10, entity.h);
                ctx.fillStyle = "black";
                ctx.fillText(entity.text_label ,entity.x + 5, entity.y + 13);
                ctx.stroke();
            }
            if(entity.etype == "link"){
                ctx.beginPath();
                ctx.fillStyle = "blue";
                ctx.setLineDash([5, 3]);
                ctx.strokeStyle = "red";
                ctx.moveTo(entity.center_x, entity.center_y);
                ctx.lineTo(entity.to[0].center_x, entity.to[0].center_y);
                ctx.stroke();
                ctx.beginPath();
                ctx.strokeStyle = "blue";
                ctx.moveTo(entity.center_x, entity.center_y);
                ctx.lineTo(entity.from[0].center_x, entity.from[0].center_y);
                ctx.stroke();
                ctx.beginPath();
                ctx.strokeStyle = "black";
                ctx.fillStyle = "white";
                ctx.fillRect(entity.x, entity.y, (entity.text_label.length * 10) + 10, entity.h);
                ctx.fillStyle = "black";
                ctx.fillText(entity.text_label ,entity.x + 5, entity.y + 13);
                ctx.stroke();
            }
            
            
        }
        
    </script>
</head>

<body>
 <canvas id="mapa" name="mapa" width="<?php echo $mapac->getWidth() + 10;  ?>" height="<?php echo $mapac->getHeight()  ;  ?>" >
</canvas>

<script>
        // reset diagrama
        var canvas = document.getElementById("mapa");
        var ctx = canvas.getContext("2d");
        ctx.fillStyle = "white";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        for(var i = 0; i < mapa.elements.length; i++){
            if(mapa.elements[i].etype == "link")
                drawEntity(mapa.elements[i]);
        }
        for(var i = 0; i < mapa.elements.length; i++){
            if(mapa.elements[i].etype != "link")
                drawEntity(mapa.elements[i]);
        }
</script> 
</body>
</html>