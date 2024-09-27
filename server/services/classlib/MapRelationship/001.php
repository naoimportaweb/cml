<?php

//error_reporting(E_ALL);

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
        $buffer_diagram["lock"] = array();

        $buffer_elements =  $mysql->DataTable("SELECT dre.id as id, ent.id as entity_id, ent.data_extra as data_extra, ent.text_label as text_label, ent.description as full_description, ent.etype, dre.x, dre.y, dre.w, dre.h  FROM entity as ent inner join diagram_relationship_element as dre on ent.id = dre.entity_id where dre.diagram_relationship_id = ? order by dre.creation_time asc", [$post_data["parameters"]["id"]]);

        for($i = 0; $i < count($buffer_elements); $i++ ) {
            
            $buffer_elements[$i]["references"] = $mysql->DataTable("SELECT drer.id, drer.title, drer.link1, drer.link2, drer.link3 FROM diagram_relationship_element_reference AS drer where drer.entity_id = ?", [$buffer_elements[$i]["entity_id"]]);

            if( $buffer_elements[$i]["etype"] == "link" ){
                $buffer_elements[$i]["from"] = $mysql->DataTable("SELECT drl.diagram_relationship_element_id as id FROM diagram_relationship_link AS drl where drl.diagram_relationship_element_id_reference = ? and ltype = 1", [   $buffer_elements[$i]["id"]  ]);
                $buffer_elements[$i]["to"] = $mysql->DataTable("SELECT drl.diagram_relationship_element_id as id FROM diagram_relationship_link AS drl where drl.diagram_relationship_element_id_reference = ? and ltype = 2", [   $buffer_elements[$i]["id"]  ]);
            }
        }

        $buffer_diagram["lock"] = $mysql->DataTable("SELECT drl.lock_time, per.username FROM diagram_relationship_lock as drl inner join person as per on drl.person_id = per.id where diagram_relationship_id = ? order by lock_time DESC LIMIT 5", [ $post_data["parameters"]["id"] ]);
        
        $buffer_diagram["locked"] = false;
        $lock = $this->has_lock($post_data["parameters"]["id"]);
        if( $lock != null ){
            if( $lock["person_id"] != $user->id ) {
                $buffer_diagram["locked"] = true;
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
        $this->date_lock = $datatable["date_lock"];
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

    public function has_lock($diagram_relationship_id){
        $mysql = new Mysql("");
        $buffer_lock = $mysql->DataTable("SELECT per.id as person_id, drl.lock_time as lock_time, per.username FROM diagram_relationship_lock as drl inner join person as per on drl.person_id = per.id where drl.diagram_relationship_id = ? order by lock_time DESC LIMIT 1", [ $diagram_relationship_id ]);
        if( count( $buffer_lock ) > 0 ) {
            $date_lock = DateTime::createFromFormat("Y-m-d H:i:s",$buffer_lock[0]["lock_time"]);
            $now = new DateTime();
            if( $date_lock > $now ) {
                return $buffer_lock[0];
            } 
        }
        return null;
    }

    public function lock_map( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        if( $this->has_lock($post_data["parameters"]["diagram_relationship_id"]) != null ){
            return [];
        }
        $date = new DateTime(); //now
        
        $date = $date->add(new DateInterval('PT60M'));//add 60 min / 1 hour
        
        $sql = "INSERT INTO diagram_relationship_lock (id, diagram_relationship_id, person_id, lock_time) values(?, ?, ?, ?)";
        $valores = [ $post_data["parameters"]["diagram_relationship_id"] . $date->format('Y-m-d H:i:s') ,$post_data["parameters"]["diagram_relationship_id"], $user->id, $date->format('Y-m-d H:i:s') ];
        $mysql->ExecuteNoQuery($sql, $valores);
        $buffer  = $mysql->DataTable("SELECT drl.lock_time, per.username FROM diagram_relationship_lock as drl inner join person as per on drl.person_id = per.id where diagram_relationship_id = ? order by lock_time DESC LIMIT 5", [ $post_data["parameters"]["diagram_relationship_id"] ]);
        return $buffer;
    } 

    public function unlock_map( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        #$buffer_diagram_lock =  $mysql->DataTable("SELECT * from diagram_relationship_lock where person_id = ? and diagram_relationship_id = ? order by lock_time DESC", [ $user->id, $post_data["parameters"]["id"] ])[0];
        $sql = "delete from diagram_relationship_lock where person_id = ? and diagram_relationship_id = ?";
        $valores = [ $user->id ,$post_data["parameters"]["diagram_relationship_id"] ];
        return count($mysql->DataTable($sql, $valores) ) > 0;
    } 

    public function exists( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        $sql = "SELECT * FROM diagram_relationship WHERE id <> ? and name = ?";
        $valores = [$post_data["parameters"]["id"], $post_data["parameters"]["name"]];
        return count($mysql->DataTable($sql, $valores) ) > 0;
    } 

    public function search( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        $sql = "SELECT dr.*, pe.username FROM diagram_relationship as dr inner join person as pe on pe.id = dr.person_id WHERE LOWER(dr.name) LIKE LOWER( ? )";
        $valores = [ $post_data["parameters"]["name"]];
        return $mysql->DataTable($sql, $valores);
    }

    public function search_entity( $ip, $user, $post_data ) {
        $mysql = new Mysql("");
        $sql = "SELECT * FROM entity  where etype <> 'link' and LOWER(text_label) LIKE LOWER( ? )";
        $valores = [ $post_data["parameters"]["name"]];
        $entitys = $mysql->DataTable($sql, $valores);
        for($i = 0; $i < count($entitys); $i++){
            $sql = "SELECT * FROM entity  where etype <> 'link' and LOWER(text_label) LIKE LOWER( ? )";
            $entitys[$i]["references"] = $mysql->DataTable("select * from  diagram_relationship_element_reference where entity_id = ?", [ $entitys[$i]["id"] ]);
        }
        return $entitys;
    }
    
    public function save($ip, $user, $post_data ){
        $mysql = new Mysql("");
        $sqls = array();
        $valuess = array();

        $lock = $this->has_lock($post_data["parameters"]["id"]);
        if( $lock != null ){
            if( $lock["person_id"] != $user->id ) {
                return false;
            }
        }
        array_push($sqls,  "INSERT INTO diagram_relationship (id, name, keyword, person_id) VALUES( ?,?,?,? ) ON DUPLICATE KEY UPDATE name = ?, keyword = ?" );
        array_push( $valuess, [ $post_data["parameters"]["id"], $post_data["parameters"]["name"], $post_data["parameters"]["keyword"], $user->id, $post_data["parameters"]["name"], $post_data["parameters"]["keyword"] ] );

        for($i = 0; $i < count($post_data["parameters"]["elements"]); $i++) {
            $element = $post_data["parameters"]["elements"][$i];

            array_push($sqls, "INSERT INTO entity (id, text_label, description, data_extra, etype) VALUES(?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE text_label = ?, description =?, data_extra = ?, etype =?");
            array_push( $valuess,[ $element["entity_id"], $element["text"], $element["full_description"], $element["data_extra"], $element["etype"], $element["text"], $element["full_description"], $element["data_extra"], $element["etype"] ]);
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
