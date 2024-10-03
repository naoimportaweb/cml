<?php
require_once dirname(dirname(__DIR__)) . "/controller/relationship/relationship.php";

$mapac = new RelationshipController( $_GET['id'] );

?>

<html>
<head>
    <script>
        var mapa = <?php echo json_encode( $mapac->getMapa()->toJson() ) ; ?>;
        console.log( mapa );

        function drawEntity(entity){
            const canvas = document.getElementById("mapa");
            const ctx = canvas.getContext("2d");
            ctx.beginPath();
            if(entity.etype == "person"){
                ctx.rect(entity.x, entity.y, (entity.text_label.length * 10) + 10, entity.h);
                ctx.stroke();
            }
            if(entity.etype == "organization"){
                ctx.rect(entity.x, entity.y, (entity.text_label.length * 10) + 10, entity.h);
                ctx.stroke();
            }
            ctx.font = "16px Courier";
            ctx.fillText(entity.text_label ,entity.x + 5, entity.y + 12);
        }
        
    </script>
</head>

<body>
 <canvas id="mapa" name="mapa" width="<?php echo $mapac->getWidth() + 200;  ?>" height="<?php echo $mapac->getHeight() + 200;  ?>" style="border:1px solid #0000FF;">
</canvas>

<script>
        for(var i = 0; i < mapa.elements.length; i++){
            drawEntity(mapa.elements[i]);
        }
</script> 
</body>
</html>