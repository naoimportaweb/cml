<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class User
{
    public $id;
    public $name;
    public $username;

    

    public function teste( $ip, $user, $post_data, $domain ) {
        return array("username" => $post_data["parameters"]["username"]);
    }

    public function load( $id , $domain ) {
        $mysql = new Mysql( $domain );
        $this->load_data( $mysql->DataTable("SELECT * from person where id = ?", [ $id ])[0] );
        return ( $this->id != null);
    }

    public function load_data( $datatable ) {
        $this->id       = $datatable["id"];
        $this->name     = $datatable["name"];
        $this->username = $datatable["username"];
    }

}

?>