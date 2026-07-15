<?php
// Lista os documentos anexados a um mapa — os mesmos que o botao "Documentos" da GUI
// gerencia. Reusa a classe Document do RPC em vez de reescrever a query: assim a lista da
// web e a do cliente nunca divergem.
//
// Sem sessao, por decisao de projeto: o report e publico. O $user vai null — a Document
// so o usa para carimbar quem subiu, e aceita nulo.
require_once dirname(dirname(__DIR__)) . "/services/classlib/Document/001.php";

header("Content-Type: application/json; charset=utf-8");

$id     = isset($_GET["id"])     ? $_GET["id"]     : "";
$domain = isset($_GET["domain"]) ? $_GET["domain"] : "";

try {
    if( $id == "" || $domain == "" ) {
        throw new Exception("Informe id e domain.");
    }
    $d = new Document();
    $lista = $d->list_by_map( null, null, array("parameters" => array("diagram_relationship_id" => $id)), $domain );
    echo json_encode( array("documentos" => $lista, "total" => count($lista)) );
} catch (Exception $e) {
    error_log("document_list: " . $e->getMessage(), 0);
    http_response_code(404);
    echo json_encode( array("error" => $e->getMessage()) );
}
?>
