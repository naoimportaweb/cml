<?php

//error_reporting(E_ALL);

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class Classification
{
    private $id = null;

    public function search( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        $sql = "SELECT * FROM classification as cls WHERE LOWER(cls.text_label) LIKE LOWER( ? ) ";
        $valores = [ $post_data["parameters"]["text_label"]];
        $buffers = $mysql->DataTable($sql, $valores);
        foreach($buffers as $buffer) {
            $sql = "SELECT * FROM classification_item where classification_id = ? ";
            $valores = [ $buffer["id"] ];
            $buffer["itens"] = $mysql->DataTable($sql, $valores);
        }
        return $buffers;
    }

    

}

?>
