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
        $buffer_diagram =  $mysql->DataTable("SELECT * from diagram_relationship where id = ?", [ $post_data["parameters"]["id"] ])[0];
        $buffer_diagram["elements"] = array();

        $buffer_elements =  $mysql->DataTable("SELECT dre.id as id, ent.id as entity_id, ent.text_label as text_label, ent.description as full_description, ent.etype, dre.x, dre.y, dre.w, dre.h  FROM entity as ent inner join diagram_relationship_element as dre on ent.id = dre.entity_id where dre.diagram_relationship_id = ? order by dre.creation_time asc", [$post_data["parameters"]["id"]]);

        for($i = 0; $i < count($buffer_elements); $i++ ) {
            
            $buffer_elements[$i]["references"] = $mysql->DataTable("SELECT drer.id, drer.title, drer.link1, drer.link2, drer.link3 FROM diagram_relationship_element_reference AS drer where drer.entity_id = ?", [$buffer_elements[$i]["entity_id"]]);

            if( $buffer_elements[$i]["etype"] == "link" ){
                $buffer_elements[$i]["from"] = $mysql->DataTable("SELECT drl.diagram_relationship_element_id as id FROM diagram_relationship_link AS drl where drl.diagram_relationship_element_id_reference = ? and ltype = 1", [   $buffer_elements[$i]["id"]  ]);
                $buffer_elements[$i]["to"] = $mysql->DataTable("SELECT drl.diagram_relationship_element_id as id FROM diagram_relationship_link AS drl where drl.diagram_relationship_element_id_reference = ? and ltype = 2", [   $buffer_elements[$i]["id"]  ]);
            }
        }
        $buffer_diagram["elements"] = $buffer_elements;
        return $buffer_diagram;
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
        $sql = "SELECT dr.*, pe.username FROM diagram_relationship as dr inner join person as pe on pe.id = dr.person_id WHERE dr.name LIKE ?";
        $valores = [ $post_data["parameters"]["name"]];
        return $mysql->DataTable($sql, $valores);
    }

    public function search_entity( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        $sql = "SELECT * FROM entity  where etype <> 'link' and text_label LIKE ?";
        $valores = [ $post_data["parameters"]["name"]];
        return $mysql->DataTable($sql, $valores);
    }
    
    public function save($ip, $user, $post_data ){
        $mysql = new Mysql("");
        $sqls = array();
        $valuess = array();
        array_push($sqls,  "INSERT INTO diagram_relationship (id, name, keyword, person_id) VALUES( ?,?,?,? ) ON DUPLICATE KEY UPDATE name = ?, keyword = ?" );
        array_push( $valuess, [ $post_data["parameters"]["id"], $post_data["parameters"]["name"], $post_data["parameters"]["keyword"], $user->id, $post_data["parameters"]["name"], $post_data["parameters"]["keyword"] ] );

        for($i = 0; $i < count($post_data["parameters"]["elements"]); $i++) {
            $element = $post_data["parameters"]["elements"][$i];
            error_log($element["id"], 0);
            //if( $element["etype"] == "link"){
            //    continue;
            //}
            // entidade
            array_push($sqls, "INSERT INTO entity (id, text_label, description, etype) VALUES(?, ?, ?, ?) ON DUPLICATE KEY UPDATE text_label = ?, description =?, etype =?");
            array_push( $valuess,[ $element["entity_id"], $element["text"], $element["full_description"], $element["etype"], $element["text"], $element["full_description"], $element["etype"] ]);
            // relacionamento
            array_push($sqls,  "INSERT INTO diagram_relationship_element (id, diagram_relationship_id, entity_id, x, y, w, h) VALUES(?, ?, ?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE x=?, y=?, w=?, h=?" );
            array_push( $valuess, [ $element["id"], $post_data["parameters"]["id"], $element["entity_id"], $element["x"], $element["y"], $element["w"], $element["h"], $element["x"], $element["y"], $element["w"], $element["h"]  ] );
            // referencia
            for($j = 0; $j < count($element["references"]); $j++){
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
                array_push($sqls, "INSERT INTO diagram_relationship_link (id, diagram_relationship_element_id, ltype, diagram_relationship_element_id_reference) values(?, ?, ?, ?)  ON DUPLICATE KEY UPDATE diagram_relationship_element_id= ?");
                array_push( $valuess,  [ $element["to"][$j]["id"], $element["to"][$j]["element_id"] ,2, $element["id"], $element["to"][$j]["element_id"] ]);
            }
            for($j = 0; $j < count($element["from"]); $j++) {
                array_push($sqls, "INSERT INTO diagram_relationship_link (id, diagram_relationship_element_id, ltype, diagram_relationship_element_id_reference) values(?, ?, ?, ?)  ON DUPLICATE KEY UPDATE diagram_relationship_element_id= ?");
                array_push( $valuess, [ $element["from"][$j]["id"], $element["from"][$j]["element_id"], 1, $element["id"], $element["from"][$j]["element_id"] ]);
            }
        }
        return ( $mysql->ExecuteNoQuery($sqls, $valuess) > 0 );
    }

}

?>
