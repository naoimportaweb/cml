<?php
// Porta de entrada do webpage. Quem abre .../cml/webpage/ cai aqui e vai para a lista de
// mapas do domain certo — sem isto o servidor devolve um indice de diretorio.
require_once dirname(__DIR__) . "/api/mysql.php";

$LISTA = "view/relationship/index.php";

try {
    // Reusa o Mysql::domains(), que ja le domains + restricted do data/config.json. Nao le
    // banco: e so o config.
    $domains = Mysql::domains();
    $nomes   = [];
    foreach( $domains as $d ){ array_push( $nomes, $d["name"] ); }

    $pedido = isset($_GET["domain"]) ? $_GET["domain"] : "";

    if( in_array( $pedido, $nomes ) ) {
        header( "Location: " . $LISTA . "?domain=" . urlencode( $pedido ) );
        exit;
    }
    // Um domain so: nao ha o que escolher.
    if( count( $nomes ) == 1 ) {
        header( "Location: " . $LISTA . "?domain=" . urlencode( $nomes[0] ) );
        exit;
    }
    if( count( $nomes ) == 0 ) {
        throw new Exception("Nenhum domain configurado no data/config.json.");
    }
    // Varios domains: escolher e do usuario. Cair no "default" calado esconderia os outros.
    $erro = null;
} catch (Exception $e) {
    error_log("webpage/index: " . $e->getMessage(), 0);
    $erro   = $e->getMessage();
    $nomes  = [];
}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CML</title>
  <link rel="stylesheet" href="public/cml.css">
<style>
.dominios { display: flex; flex-direction: column; gap: 2px; max-width: 420px; }
.dominios a {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 12px 14px; text-decoration: none; color: var(--text-primary);
  background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px;
}
.dominios a:hover { background: var(--hover); border-color: var(--person); }
.dominios .tag { font-size: 11px; color: var(--muted); }
</style>
</head>
<body>
<div class="wrap">
  <header><h1>CML — Mapas de vínculos</h1></header>
<?php if( $erro != null ) { ?>
  <p class="aviso"><?php echo htmlspecialchars($erro, ENT_QUOTES, "UTF-8"); ?></p>
<?php } else { ?>
  <p class="aviso">Escolha o domain:</p>
  <div class="dominios">
<?php foreach( $domains as $d ) {
        $n = htmlspecialchars($d["name"], ENT_QUOTES, "UTF-8"); ?>
    <a href="<?php echo $LISTA; ?>?domain=<?php echo urlencode($d["name"]); ?>">
      <span><?php echo $n; ?></span>
      <span class="tag"><?php echo $d["restricted"] ? "restrito" : "aberto"; ?></span>
    </a>
<?php } ?>
  </div>
<?php } ?>
</div>
</body>
</html>
