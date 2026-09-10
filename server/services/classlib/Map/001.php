<?php

error_reporting(E_ALL);

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class Map
{
    public function search( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $sql = "SELECT dr.*, pe.username FROM diagram_relationship as dr inner join person as pe on pe.id = dr.person_id WHERE LOWER(dr.name) LIKE LOWER( ? ) or LOWER(dr.keyword) LIKE LOWER( ? )";
        $valores = [ $post_data["parameters"]["name"], $post_data["parameters"]["name"]];
        $relationship = $mysql->DataTable($sql, $valores);
        // creation_time/modification_time entram aqui porque a lista de mapas do cliente
        // ordena por data de edicao: sem elas o organograma nao teria por onde ordenar,
        // enquanto o mapa de relacionamento tem (o dr.* ja traz as duas).
        $sql = "SELECT ochart.organization_id as organization_id, ochart.id as id, ochart.text_label as name, ent.text_label as organization_text_label, pe.username as username, ochart.creation_time as creation_time, ochart.modification_time as modification_time FROM organization_chart as ochart inner join entity as ent on ochart.organization_id = ent.id  inner join person as pe on pe.id = ochart.person_id WHERE LOWER(ochart.text_label) LIKE LOWER( ? ) or LOWER( ent.text_label) LIKE LOWER( ? )";
        $valores = [ $post_data["parameters"]["name"], $post_data["parameters"]["name"]];
        $organization = $mysql->DataTable($sql, $valores);
        // Timeline e o terceiro tipo de documento e entra na MESMA lista de abrir. O nome do
        // mapa de origem vem junto (LEFT JOIN: a timeline pode ser solta) para a lista dizer
        // de qual mapa ela e a linha do tempo.
        $sql = "SELECT dt.id as id, dt.text_label as name, dt.keyword as keyword, dt.diagram_relationship_id as diagram_relationship_id, "
             . "dr.name as relationship_name, pe.username as username, dt.creation_time as creation_time, dt.modification_time as modification_time "
             . "FROM diagram_timeline as dt "
             . "INNER JOIN person as pe on pe.id = dt.person_id "
             . "LEFT JOIN diagram_relationship as dr on dr.id = dt.diagram_relationship_id "
             . "WHERE LOWER(dt.text_label) LIKE LOWER( ? ) or LOWER(dt.keyword) LIKE LOWER( ? )";
        $valores = [ $post_data["parameters"]["name"], $post_data["parameters"]["name"]];
        $timeline = $mysql->DataTable($sql, $valores);
        return array("relationship" => $relationship, "organization" => $organization, "timeline" => $timeline);
    }
}

?>



