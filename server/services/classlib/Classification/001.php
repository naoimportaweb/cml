<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class Classification
{
    public function search( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $sql = "SELECT * FROM classification as cls WHERE LOWER(cls.text_label) LIKE LOWER( ? ) ";
        $valores = [ $post_data["parameters"]["text_label"]];
        $buffers = $mysql->DataTable($sql, $valores);
        for($i = 0; $i < count($buffers); $i++) {
            $sql = "SELECT * FROM classification_item where classification_id = ? ";
            $valores = [ $buffers[$i]["id"] ];
            $buffers[$i]["itens"] = $mysql->DataTable($sql, $valores);
        }
        return $buffers;
    }

    public function add( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $id = $post_data["parameters"]["classification_item_id"] . $post_data["parameters"]["entity_id"];
        $sql = "INSERT INTO entity_classification_item(id, classification_item_id, entity_id, start_date, end_date) values( ?, ?, ?, ?, ?)";
        return $mysql->ExecuteNoQuery($sql, [ $id, $post_data["parameters"]["classification_item_id"], $post_data["parameters"]["entity_id"], $post_data["parameters"]["start_date"], $post_data["parameters"]["end_date"] ]) > 0;
    }
}

?>
