<?php

require_once dirname(__DIR__) . "/controller/relationship/relationship_list.php";

header("Content-Type: application/json; charset=utf-8");

$domain = isset($_GET["domain"]) ? $_GET["domain"] : "";

try {
    if( $domain == "" ) {
        throw new Exception("Informe o domain.");
    }
    $c = new RelationshipListController( $domain );
    echo json_encode( $c->toJson() );
} catch (Exception $e) {
    // Mesmo contrato do relationship_load: falha tratada devolve JSON com "error", nunca
    // um 500 de corpo vazio que o cliente nao consegue explicar.
    error_log("relationship_list: " . $e->getMessage(), 0);
    http_response_code(404);
    echo json_encode( array("error" => $e->getMessage()) );
}
?>
