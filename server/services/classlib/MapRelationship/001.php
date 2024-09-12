<?php

require_once dirname(dirname(__DIR__)) . "/api/mysql.php";

class MapRelationship
{
    private $id = null;
    private $name = "";

    public function load( $id ) {
        $mysql = Mysql("");
        $this->load( $mysql->DataTable("SELECT * from diagram_relationship where id = ?", [ $id ])[0] );

        return ( $this->id != null);
    }

    public function load( $datatable ) {
        $this->id   = $datatable["id"];
        $this->name = $datatable["name"];
    }

    public function create( ) {
        $mysql = Mysql("");
        $sql = "INSERT INTO diagram_relationship (id, name) values(?, ?)";
        $valores = [$this->id, $this->name];
        return $mysql->ExecuteNoQuery($sql, $valores);
    }    

}

?>