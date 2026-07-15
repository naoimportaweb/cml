<?php
// TODO: listar todos os mapas e dar permissao de busca.
// (era texto solto fora do <?php e vazava impresso no topo da pagina)
// dirname(__DIR__) e nao dirname(dirname(__DIR__)): este arquivo esta em webpage/view/, um
// nivel abaixo de webpage/, igual ao service/relationship_load.php. Com o dirname extra o
// require apontava para server/controller/ (fora do webpage/) e a pagina era 500 sempre.
require_once dirname(__DIR__) . "/controller/relationship/relationship.php";

// Os mesmos flags da view/relationship: sem JSON_HEX_TAG um text_label contendo
// "</script>" fecha a tag e o resto vira codigo executavel.
$JS = JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT;

$id     = isset($_GET["id"])     ? $_GET["id"]     : "";
$domain = isset($_GET["domain"]) ? $_GET["domain"] : "";

$mapac = null;
$erro  = null;
try {
    if( $id == "" || $domain == "" ) {
        throw new Exception("Informe id e domain.");
    }
    $mapac = new RelationshipController( $id, $domain );
} catch (Exception $e) {
    // Relationship::loadData lanca quando o mapa nao existe; sem este catch a pagina
    // inteira morre em 500 branco.
    $erro = $e->getMessage();
}
?>

<html>
<head>
    <meta charset="utf-8">
</head>

<body>
<?php if( $erro != null ) { ?>
<p><?php echo htmlspecialchars($erro, ENT_QUOTES, "UTF-8"); ?></p>
</body>
</html>
<?php return; } ?>

 <canvas id="mapa" name="mapa" width="<?php echo $mapac->getWidth() + 10;  ?>" height="<?php echo $mapac->getHeight()  ;  ?>" >
</canvas>

<script>
        var mapa = <?php echo json_encode( $mapac->getMapa()->toJson(), $JS ); ?>;

        // 14px Courier tem que bater com o EntityBox::CHAR_W do model, que e quem
        // calcula entity.w e a moldura do canvas. Estava 16px aqui e a caixa era
        // desenhada com text_label.length * 10 por conta propria: o PHP reservava uma
        // largura e o JS desenhava outra, cortando as caixas na borda direita.
        var CHAR_FONT = "14px Courier";

        function drawEntity(entity){
            const canvas = document.getElementById("mapa");
            const ctx = canvas.getContext("2d");
            ctx.beginPath();
            ctx.fillStyle = "white";

            ctx.font = CHAR_FONT;
            ctx.setLineDash([]);

            if(entity.etype == "other"){
                ctx.fillStyle = "yellow";
                ctx.fillRect(entity.x, entity.y, entity.w, entity.h);
                ctx.fillStyle = "black";
                ctx.fillText(entity.text_label, entity.x + 5, entity.y + 13);
                ctx.stroke();
            }
            if(entity.etype == "person"){
                ctx.beginPath();
                ctx.fillStyle = "white";
                ctx.fillRect(entity.x, entity.y, entity.w, entity.h);
                ctx.fillStyle = "black";
                ctx.roundRect(entity.x, entity.y, entity.w, entity.h, 20);
                ctx.fillStyle = "black";
                ctx.fillText(entity.text_label, entity.x + 5, entity.y + 13);
                ctx.stroke();
            }
            if(entity.etype == "organization"){
                ctx.beginPath();
                ctx.fillStyle = "white";
                ctx.fillRect(entity.x, entity.y, entity.w, entity.h);
                ctx.fillStyle = "black";
                ctx.rect(entity.x, entity.y, entity.w, entity.h);
                ctx.fillStyle = "black";
                ctx.fillText(entity.text_label, entity.x + 5, entity.y + 13);
                ctx.stroke();
            }
            if(entity.etype == "link"){
                // to[0]/from[0] direto estourava em link sem ponta ligada; um link pode
                // ter varias pontas de cada lado.
                ctx.beginPath();
                ctx.setLineDash([5, 3]);
                ctx.strokeStyle = "red";
                for(var i = 0; i < entity.to.length; i++) {
                    ctx.moveTo(entity.center_x, entity.center_y);
                    ctx.lineTo(entity.to[i].center_x, entity.to[i].center_y);
                }
                ctx.stroke();
                ctx.beginPath();
                ctx.strokeStyle = "blue";
                for(var i = 0; i < entity.from.length; i++) {
                    ctx.moveTo(entity.center_x, entity.center_y);
                    ctx.lineTo(entity.from[i].center_x, entity.from[i].center_y);
                }
                ctx.stroke();
                ctx.beginPath();
                ctx.setLineDash([]);
                ctx.strokeStyle = "black";
                ctx.fillStyle = "white";
                ctx.fillRect(entity.x, entity.y, entity.w, entity.h);
                ctx.fillStyle = "black";
                ctx.fillText(entity.text_label, entity.x + 5, entity.y + 13);
                ctx.stroke();
            }
        }

        // reset diagrama
        var canvas = document.getElementById("mapa");
        var ctx = canvas.getContext("2d");
        ctx.fillStyle = "white";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // links primeiro, para as linhas ficarem atras das caixas
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
