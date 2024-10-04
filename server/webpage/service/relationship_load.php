<?php

require_once dirname(__DIR__) . "/controller/relationship/relationship.php";
$mapac = new RelationshipController( $_GET['id'] );

echo json_encode( $mapac->toJson() );
?>