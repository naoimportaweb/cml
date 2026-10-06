<?php

require_once dirname(__DIR__) . "/controller/timeline/timeline.php";

header("Content-Type: application/json; charset=utf-8");

$id     = isset($_GET["id"])     ? $_GET["id"]     : "";
$domain = isset($_GET["domain"]) ? $_GET["domain"] : "";

try {
    if( $id == "" || $domain == "" ) {
        throw new Exception("Informe id e domain.");
    }
    $c = new TimelineController( $id, $domain );
    echo json_encode( $c->toJson() );
} catch (Exception $e) {
    error_log("timeline_load: " . $e->getMessage(), 0);
    http_response_code(404);
    echo json_encode( array("error" => $e->getMessage()) );
}
?>
