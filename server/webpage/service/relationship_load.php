<?php

require_once dirname(__DIR__) . "/controller/relationship/relationship.php";
error_log("domain:". $_GET['domain'], 0);
$mapac = new RelationshipController( $_GET['id'], $_GET['domain'] );

echo json_encode( $mapac->toJson() );
?>