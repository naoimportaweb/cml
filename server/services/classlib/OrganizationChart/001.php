<?php

//error_reporting(E_ALL);

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class OrganizationChart
{

    public function load( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        
        return $buffer_diagram;
    }



    public function create( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        $sql = "INSERT INTO organization_chart (id, organization_id, text_label, person_id) values(?, ?, ?, ?)";
        $valores = [$post_data["parameters"]["id"], $post_data["parameters"]["organization_id"]  , $post_data["parameters"]["text_label"], $user->id ];
        return $mysql->ExecuteNoQuery($sql, $valores);
    }    

   


}

?>
