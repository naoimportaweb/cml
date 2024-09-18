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

    public function save($ip, $user, $post_data ){
        $mysql = new Mysql("");
        $sqls = [ "INSERT INTO diagram_relationship (id, name, keyword, person_id) VALUES( ?,?,?,? ) ON DUPLICATE KEY UPDATE name = ?, keyword = ?" ];
        $valuess = [ [$post_data["parameters"]["id"], $post_data["parameters"]["name"], $post_data["parameters"]["keyword"], $user->id, $post_data["parameters"]["name"], $post_data["parameters"]["keyword"]] ];

        for($i = 0; $i < count($post_data["parameters"]["elements"]); $i++) {
            $element = $post_data["parameters"]["elements"][$i];
            // entidade
            $sqls.push("INSERT INTO entity (id, text_label, description, etype) VALUES(?, ?, ?, ?) ON DUPLICATE KEY UPDATE text_label = ?, description =?, etype =?");
            // relacionamento

            // referencia
        }
        return ( $mysql->ExecuteNoQuery($sqls, $valuess) > 0 );
    }

}

?>

{'id': 'c9d497fa3f7e4d689e6a6e35d6495920_c786d2d693104f90a488a76e8fb43ca1_a80236f39daa48e3a9b62053783978db', 'name': 'educacao', 'keyword': 'ato', 'elements': [{'id': 'ea8a633840ce4abfa63745237f475c0b_1220c3a7e3ee4f9a8bfc6113bb3748ed_a3d617fce92e4c98adaed358115c04f7', 'x': 1031, 'y': 176, 'w': 54, 'h': 18, 'text': 'Person', 'full_description': '', 'etype': 'person', 'references': []}]}
