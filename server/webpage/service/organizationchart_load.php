<?php

require_once dirname(__DIR__) . "/controller/organizationchart/organizationchart.php";

header("Content-Type: application/json; charset=utf-8");

$id     = isset($_GET["id"])     ? $_GET["id"]     : "";
$domain = isset($_GET["domain"]) ? $_GET["domain"] : "";

try {
    if( $id == "" || $domain == "" ) {
        throw new Exception("Informe id e domain.");
    }
    $c = new OrganizationChartController( $id, $domain );
    echo json_encode( $c->toJson() );
} catch (Exception $e) {
    // Mesma razao do relationship_load: sem este catch o endpoint responde 500 com corpo
    // vazio e o cliente nao sabe se o organograma nao existe ou se o servidor caiu.
    error_log("organizationchart_load: " . $e->getMessage(), 0);
    http_response_code(404);
    echo json_encode( array("error" => $e->getMessage()) );
}
?>
