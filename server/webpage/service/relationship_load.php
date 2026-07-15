<?php

require_once dirname(__DIR__) . "/controller/relationship/relationship.php";

header("Content-Type: application/json; charset=utf-8");

$id     = isset($_GET["id"])     ? $_GET["id"]     : "";
$domain = isset($_GET["domain"]) ? $_GET["domain"] : "";

try {
    if( $id == "" || $domain == "" ) {
        throw new Exception("Informe id e domain.");
    }
    $mapac = new RelationshipController( $id, $domain );
    echo json_encode( $mapac->toJson() );
} catch (Exception $e) {
    // Sem este catch a excecao do Relationship::loadData sobe ate o PHP e o endpoint
    // responde 500 com corpo vazio: o cliente fica sem saber se o mapa nao existe, se
    // o domain esta errado ou se o servidor caiu.
    error_log("relationship_load: " . $e->getMessage(), 0);
    http_response_code(404);
    echo json_encode( array("error" => $e->getMessage()) );
}
?>
