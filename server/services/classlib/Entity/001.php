<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class Entity
{
    private $id = null;
    private $name = "";

    public function merge_to( $ip, $user, $post_data, $domain) {
        $mysql = new Mysql( $domain );
        $old_entity_id = $post_data["parameters"]["old_entity_id"];
        $new_entity_id = $post_data["parameters"]["new_entity_id"];
        $sqls = [];
        $values = [];

        $old_object = $mysql->DataTable("select * from entity where id= ?", [ $old_entity_id ]);
        $new_object = $mysql->DataTable("select * from entity where id= ?", [ $new_entity_id ]);

        if( $old_object["text_label"] !=  $new_object["text_label"]) {
            throw new Exception("O nome dos objetos são diferentes.");
        }
        array_push($sqls, "UPDATE entity_classification_item set entity_id = ? where entity_id = ?");
        array_push($values, [$new_entity_id, $old_entity_id]);

        array_push($sqls, "UPDATE diagram_relationship_element set entity_id = ? where entity_id = ?");
        array_push($values, [$new_entity_id, $old_entity_id]);

        array_push($sqls, "UPDATE diagram_relationship_element_reference set entity_id = ? where entity_id = ?");
        array_push($values, [$new_entity_id, $old_entity_id]);

        array_push($sqls, "UPDATE organization_chart_item_entity set entity_id = ? where entity_id = ?");
        array_push($values, [$new_entity_id, $old_entity_id]);

        array_push($sqls, "DELETE FROM entity where id= ?");
        array_push($values, [$old_entity_id]);

        return $mysql->ExecuteNoQuery($sqls, $values);
    }

    public function to_type( $ip, $user, $post_data, $domain) {
        $mysql = new Mysql( $domain );
        $sql = "UPDATE entity SET etype= ? WHERE id = ?";
        return $mysql->ExecuteNoQuery($sql, [ $post_data["parameters"]["type"], $post_data["parameters"]["id"] ]);
    }

    public function search( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $sql = "";
        $valores = [];
        if( $post_data["parameters"]["etype"] != "" ) {
            $sql = "SELECT ent.* from entity as ent WHERE ent.etype = ? and ( LOWER(ent.text_label) LIKE LOWER( ? )  or LOWER(ent.small_label) LIKE LOWER( ? )   )";
            $valores = [ $post_data["parameters"]["etype"], $post_data["parameters"]["text_label"], $post_data["parameters"]["text_label"]];
        } else {
            $sql = "SELECT ent.* from entity as ent WHERE  LOWER(ent.text_label) LIKE LOWER( ? )  or LOWER(ent.small_label) LIKE LOWER( ? )  ";
            $valores = [ $post_data["parameters"]["text_label"], $post_data["parameters"]["text_label"]];           
        }
        return $mysql->DataTable($sql, $valores);
    }

    public function duplicate( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $sql = "SELECT ent.* from entity as ent WHERE ent.etype = ? and ent.id <> ? and ent.text_label = ?  ";
        $valores = [ $post_data["parameters"]["etype"], $post_data["parameters"]["id"], $post_data["parameters"]["text_label"]];
        return $mysql->DataTable($sql, $valores);
    }
}

?>
