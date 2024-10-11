<?php

error_reporting(E_ALL);

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class Map
{
    public function search( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        error_log(json_encode($post_data), 0);
        $sql = "SELECT dr.*, pe.username FROM diagram_relationship as dr inner join person as pe on pe.id = dr.person_id WHERE LOWER(dr.name) LIKE LOWER( ? ) or LOWER(dr.keyword) LIKE LOWER( ? )";
        $valores = [ $post_data["parameters"]["name"], $post_data["parameters"]["name"]];
        $relationship = $mysql->DataTable($sql, $valores);
        error_log(json_encode($relationship), 0);
        $sql = "SELECT ochart.organization_id as organization_id, ochart.id as id, ochart.text_label as name, ent.text_label as organization_text_label, pe.username as username FROM organization_chart as ochart inner join entity as ent on ochart.organization_id = ent.id  inner join person as pe on pe.id = ochart.person_id WHERE LOWER(ochart.text_label) LIKE LOWER( ? ) or LOWER( ent.text_label) LIKE LOWER( ? )";
        $valores = [ $post_data["parameters"]["name"], $post_data["parameters"]["name"]];
        $organization = $mysql->DataTable($sql, $valores);
        error_log(json_encode($organization),0);
        return array("relationship" => $relationship, "organization" => $organization);
    }

    

}

?>



