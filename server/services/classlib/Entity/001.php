<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class Entity
{
    private $id = null;
    private $name = "";

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
}

?>
