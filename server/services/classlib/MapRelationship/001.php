<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class MapRelationship
{
    private $id = null;
    private $name = "";
    private $keyword = "";
    private $person_id = "";

    public function load( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        $buffer =  $mysql->DataTable("SELECT * from diagram_relationship where id = ?", [ $post_data["parameters"]["id"] ])[0];
        return $buffer;
    }

    public function load_data( $datatable ) {
        $this->id   = $datatable["id"];
        $this->name = $datatable["name"];
        $this->person_id = $datatable["person_id"];
        $this->keyword = $datatable["keyword"];
    }

    public function create( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        $this->id = $post_data["parameters"]["id"];
        $this->name = $post_data["parameters"]["name"];
        $this->keyword = $post_data["parameters"]["keyword"];
        $this->person_id = $user->id;
        $sql = "INSERT INTO diagram_relationship (id, person_id, name, keyword) values(?, ?, ?, ?)";
        $valores = [$this->id, $this->person_id  ,$this->name, $this->keyword];
        return $mysql->ExecuteNoQuery($sql, $valores);
    }    

    public function exists( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        $sql = "SELECT * FROM diagram_relationship WHERE id <> ? and name = ?";
        $valores = [$post_data["parameters"]["id"], $post_data["parameters"]["name"]];
        return count($mysql->DataTable($sql, $valores) ) > 0;
    } 

    public function search( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        $sql = "SELECT dr.*, pe.username FROM diagram_relationship as dr inner join person as pe on pe.id = dr.person_id WHERE dr.name = ?";
        $valores = [ $post_data["parameters"]["name"]];
        return $mysql->DataTable($sql, $valores);
    } 

}

?>