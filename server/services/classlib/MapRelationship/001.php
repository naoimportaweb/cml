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
        error_log("salvar",);
        $mysql = new Mysql("");
        $sqls = array();
        $valuess = array();
        array_push($sqls,  "INSERT INTO diagram_relationship (id, name, keyword, person_id) VALUES( ?,?,?,? ) ON DUPLICATE KEY UPDATE name = ?, keyword = ?" );
        array_push( $valuess, [ $post_data["parameters"]["id"], $post_data["parameters"]["name"], $post_data["parameters"]["keyword"], $user->id, $post_data["parameters"]["name"], $post_data["parameters"]["keyword"] ] );

        for($i = 0; $i < count($post_data["parameters"]["elements"]); $i++) {
            $element = $post_data["parameters"]["elements"][$i];
            error_log($element["id"], 0);
            if( $element["etype"] == "link"){
                continue;
            }
            // entidade
            array_push($sqls, "INSERT INTO entity (id, text_label, description, etype) VALUES(?, ?, ?, ?) ON DUPLICATE KEY UPDATE text_label = ?, description =?, etype =?");
            array_push( $valuess,[ $element["entity_id"], $element["text"], $element["full_description"], $element["etype"], $element["text"], $element["full_description"], $element["etype"] ]);
            // relacionamento
            array_push($sqls,  "INSERT INTO diagram_relationship_element (id, diagram_relationship_id, entity_id, x, y, w, h) VALUES(?, ?, ?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE x=?, y=?, w=?, h=?" );
            array_push( $valuess, [ $element["id"], $post_data["parameters"]["id"], $element["entity_id"], $element["x"], $element["y"], $element["w"], $element["h"], $element["x"], $element["y"], $element["w"], $element["h"]  ] );
            // referencia
            for($j = 0; $j < count($element["references"]); $j){
                $reference = $element["references"][$j];
                array_push($sqls, "INSERT INTO diagram_relationship_element_reference (id, entity_id, title, link1, link2, link3 ) VALUES(?, ?, ?, ?, ?, ? )  ON DUPLICATE KEY UPDATE  title=?, link1=?, link2=?, link3=?");
                array_push( $valuess, [ $reference["id"], $reference["entity_id"], $reference["title"], $reference["link1"], $reference["link2"], $reference["link3"], $reference["title"], $reference["link1"], $reference["link2"], $reference["link3"] ] );
            }
        }

        for($i = 0; $i < count($post_data["parameters"]["elements"]); $i++) {
            $element = $post_data["parameters"]["elements"][$i];
            if( $element["etype"] != "link"){
                continue;
            }
            for($j = 0; $j < count($element["to"]); $j++) {
                error_log( $element["to"][$j]["id"] );
                array_push($sqls, "INSERT INTO diagram_relationship_link (id, diagram_relationship_element_id, ltype) values(?, ?, ?)  ON DUPLICATE KEY UPDATE diagram_relationship_element_id= ?");
                array_push( $valuess,  [ $element["to"][$j]["id"] . substr($element["id"], 0, 20), $element["to"][$j]["id"],2, $element["to"][$j]["id"] ]);
            }
            for($j = 0; $j < count($element["from"]); $j++) {
                array_push($sqls, "INSERT INTO diagram_relationship_link (id, diagram_relationship_element_id, ltype) values(?, ?, ?)  ON DUPLICATE KEY UPDATE diagram_relationship_element_id= ?");
                array_push( $valuess, [ $element["from"][$j]["id"] . substr($element["id"], 0, 20), $element["to"][$j]["id"],1, $element["to"][$j]["id"] ]);
            }
        }
        error_log( json_encode($sqls), 0 );
        return ( $mysql->ExecuteNoQuery($sqls, $valuess) > 0 );
    }

}

?>
