<?php

//error_reporting(E_ALL);

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";
require_once dirname(__DIR__) . "/Entity/001.php";

class MapRelationship
{
    private $id = null;
    private $name = "";
    private $keyword = "";
    private $person_id = "";

    public function load( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $buffer_diagram =  $mysql->DataTable("SELECT * from diagram_relationship where id = ?", [ $post_data["parameters"]["id"] ])[0];
        $buffer_diagram["elements"] = array();
        $buffer_diagram["lock"] = array();

        $buffer_elements =  $mysql->DataTable("SELECT ent.default_url as default_url, ent.start_date as entity_start_date, ent.end_date as entity_end_date, ent.format_date as entity_format_date, dre.start_date as element_start_date, dre.end_date as element_end_date, dre.format_date as element_format_date,  ent.small_label as small_label, ent.wikipedia as wikipedia, dre.id as id, ent.id as entity_id, ent.data_extra as data_extra, ent.text_label as text_label, ent.description as full_description, ent.etype, dre.x, dre.y, dre.w, dre.h  FROM entity as ent inner join diagram_relationship_element as dre on ent.id = dre.entity_id where dre.diagram_relationship_id = ? order by dre.creation_time asc", [$post_data["parameters"]["id"]]);

        for($i = 0; $i < count($buffer_elements); $i++ ) {
            
            $buffer_elements[$i]["references"] = $mysql->DataTable("SELECT drer.id, drer.title, drer.link1, drer.link2, drer.link3, drer.description as descricao FROM diagram_relationship_element_reference AS drer where drer.entity_id = ?", [$buffer_elements[$i]["entity_id"]]);

            $buffer_elements[$i]["classification"] = $mysql->DataTable("select eci.format_date as format_date, eci.entity_id as entity_id, eci.start_date as start_date, eci.end_date as end_date, eci.id as id, clsi.text_label as text_label_choice, cls.text_label as text_label, clsi.id as classification_item_id from entity_classification_item as eci inner join classification_item as clsi on eci.classification_item_id = clsi.id inner join classification as cls on clsi.classification_id = cls.id where eci.entity_id = ?", [$buffer_elements[$i]["entity_id"]]);

            if( $buffer_elements[$i]["etype"] == "link" ){
                $buffer_elements[$i]["from"] = $mysql->DataTable("SELECT drl.diagram_relationship_element_id as id, drl.start_date as start_date, drl.end_date as end_date, drl.format_date as format_date FROM diagram_relationship_link AS drl where drl.diagram_relationship_element_id_reference = ? and ltype = 1", [   $buffer_elements[$i]["id"]  ]);
                $buffer_elements[$i]["to"] = $mysql->DataTable("SELECT drl.diagram_relationship_element_id as id, drl.start_date as start_date, drl.end_date as end_date, drl.format_date as format_date  FROM diagram_relationship_link AS drl where drl.diagram_relationship_element_id_reference = ? and ltype = 2", [   $buffer_elements[$i]["id"]  ]);
            }
        }

        $buffer_diagram["lock"] = $mysql->DataTable("SELECT drl.lock_time, per.username FROM diagram_relationship_lock as drl inner join person as per on drl.person_id = per.id where diagram_relationship_id = ? order by lock_time DESC LIMIT 5", [ $post_data["parameters"]["id"] ]);
        
        $buffer_diagram["locked"] = false;
        $lock = $this->has_lock($post_data["parameters"]["id"], $domain);
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

    public function create( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $this->id = $post_data["parameters"]["id"];
        $this->name = $post_data["parameters"]["name"];
        $this->keyword = $post_data["parameters"]["keyword"];
        $this->person_id = $user->id;
        $sql = "INSERT INTO diagram_relationship (id, person_id, name, keyword) values(?, ?, ?, ?)";
        $valores = [$this->id, $this->person_id  ,$this->name, $this->keyword];
        return $mysql->ExecuteNoQuery($sql, $valores);
    }    

    public function has_lock($diagram_relationship_id, $domain){
        $mysql = new Mysql( $domain );
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

    public function lock_map( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        if( $this->has_lock($post_data["parameters"]["diagram_relationship_id"], $domain) != null ){
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

    public function unlock_map( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $sql = "delete from diagram_relationship_lock where person_id = ? and diagram_relationship_id = ?";
        $valores = [ $user->id ,$post_data["parameters"]["diagram_relationship_id"] ];
        return count($mysql->DataTable($sql, $valores) ) > 0;
    } 

    public function exists( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $sql = "SELECT * FROM diagram_relationship WHERE id <> ? and name = ?";
        $valores = [$post_data["parameters"]["id"], $post_data["parameters"]["name"]];
        return count($mysql->DataTable($sql, $valores) ) > 0;
    } 



    public function search_entity( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $sql = "SELECT * FROM entity  where etype <> 'link' and LOWER(text_label) LIKE LOWER( ? )";
        $valores = [ $post_data["parameters"]["name"]];
        $entitys = $mysql->DataTable($sql, $valores);
        for($i = 0; $i < count($entitys); $i++){
            $entitys[$i] = Entity::appendData($entitys[$i], $domain );
            //$sql = "SELECT * FROM entity  where etype <> 'link' and LOWER(text_label) LIKE LOWER( ? )";
            //$entitys[$i]["references"] = $mysql->DataTable("select * from  diagram_relationship_element_reference where entity_id = ?", [ $entitys[$i]["id"] ]);
        }
        return $entitys;
    }
    
    public function save($ip, $user, $post_data, $domain ){
        $mysql = new Mysql( $domain );
        $sqls = array();
        $valuess = array();

        $lock = $this->has_lock($post_data["parameters"]["id"], $domain);
        if( $lock != null ){
            if( $lock["person_id"] != $user->id ) {
                return false;
            }
        }
        array_push($sqls,  "INSERT INTO diagram_relationship (id, name, keyword, person_id) VALUES( ?,?,?,? ) ON DUPLICATE KEY UPDATE name = ?, keyword = ?" );
        array_push( $valuess, [ $post_data["parameters"]["id"], $post_data["parameters"]["name"], $post_data["parameters"]["keyword"], $user->id, $post_data["parameters"]["name"], $post_data["parameters"]["keyword"] ] );

        for($i = 0; $i < count($post_data["parameters"]["elements"]); $i++) {
            $element = $post_data["parameters"]["elements"][$i];
//
            array_push($sqls, "INSERT INTO entity (id, text_label, description, data_extra, etype, wikipedia, small_label, default_url, start_date, end_date, format_date) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE text_label = ?, description =?, data_extra = ?, etype =?, wikipedia = ?, small_label = ?, default_url = ?, start_date = ?, end_date = ?, format_date =?");
            array_push( $valuess,[ $element["entity_id"], $element["text"], $element["full_description"], $element["data_extra"], $element["etype"], $element["wikipedia"], $element["small_label"], $element["default_url"], $element["entity_start_date"], $element["entity_end_date"], $element["entity_format_date"], $element["text"], $element["full_description"], $element["data_extra"], $element["etype"], $element["wikipedia"], $element["small_label"], $element["default_url"], $element["entity_start_date"], $element["entity_end_date"], $element["entity_format_date"] ]);
            // relacionamento
            array_push($sqls,  "INSERT INTO diagram_relationship_element (id, diagram_relationship_id, entity_id, x, y, w, h, start_date, end_date, format_date) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE x=?, y=?, w=?, h=?, start_date = ?, end_date = ?, format_date =?" );
            array_push( $valuess, [ $element["id"], $post_data["parameters"]["id"], $element["entity_id"], $element["x"], $element["y"], $element["w"], $element["h"], $element["start_date"], $element["end_date"], $element["format_date"], $element["x"], $element["y"], $element["w"], $element["h"], $element["start_date"], $element["end_date"], $element["format_date"]  ] );
            // referencia
            for($j = 0; $j < count($element["references"]); $j++){
                $reference = $element["references"][$j];
                array_push($sqls, "INSERT INTO diagram_relationship_element_reference (id, entity_id, title, link1, link2, link3, description ) VALUES(?, ?, ?, ?, ?, ?, ? )  ON DUPLICATE KEY UPDATE  title=?, link1=?, link2=?, link3=?, description=?");
                array_push( $valuess, [ $reference["id"], $reference["entity_id"], $reference["title"], $reference["link1"], $reference["link2"], $reference["link3"], $reference["description"], $reference["title"], $reference["link1"], $reference["link2"], $reference["link3"], $reference["description"] ] );
            }
            if( array_key_exists("classification", $element) ) {
                for($j = 0; $j < count($element["classification"]); $j++){
                    array_push($sqls, "INSERT INTO entity_classification_item(id, classification_item_id, entity_id, start_date, end_date, format_date) values( ?, ?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE  start_date=?, end_date=?, format_date=? ");
                    array_push($valuess, [ $element["classification"][$j]["id"], $element["classification"][$j]["classification_item_id"], $element["classification"][$j]["entity_id"], $element["classification"][$j]["start_date"], $element["classification"][$j]["end_date"], $element["classification"][$j]["format_date"]  , $element["classification"][$j]["start_date"], $element["classification"][$j]["end_date"],  $element["classification"][$j]["format_date"] ] );
                }
            }
        }

        for($i = 0; $i < count($post_data["parameters"]["elements"]); $i++) {
            $element = $post_data["parameters"]["elements"][$i];
            if( $element["etype"] != "link"){
                continue;
            }
            for($j = 0; $j < count($element["to"]); $j++) {
                
                array_push($sqls, "INSERT INTO diagram_relationship_link (id, diagram_relationship_element_id, ltype, diagram_relationship_element_id_reference, start_date, end_date, format_date) values(?, ?, ?, ?, ?, ?, ?)  ON DUPLICATE KEY UPDATE start_date = ?, end_date = ?, format_date = ?");
                array_push( $valuess,  [ $element["to"][$j]["id"], $element["to"][$j]["element_id"] ,2, $element["id"], $element["to"][$j]["start_date"], $element["to"][$j]["end_date"] , $element["to"][$j]["format_date"] , $element["to"][$j]["start_date"], $element["to"][$j]["end_date"], $element["to"][$j]["format_date"] ]);
            }
            for($j = 0; $j < count($element["from"]); $j++) {
                array_push($sqls, "INSERT INTO diagram_relationship_link (id, diagram_relationship_element_id, ltype, diagram_relationship_element_id_reference, start_date, end_date, format_date) values(?, ?, ?, ?, ?, ?, ?)  ON DUPLICATE KEY UPDATE start_date = ?, end_date = ?, format_date = ?");
                array_push( $valuess, [ $element["from"][$j]["id"], $element["from"][$j]["element_id"], 1, $element["id"], $element["from"][$j]["start_date"], $element["from"][$j]["end_date"] , $element["from"][$j]["format_date"] ,$element["from"][$j]["start_date"], $element["from"][$j]["end_date"], $element["from"][$j]["format_date"] ]);
            }
        }
        // LIMPEZAS DE DADOS QUE NAO QUEREMOS MAIS, EXCLUIDOS PELO USU[ARIO]
        // Assim nao tem performance, mas estou envitando ijeçao de sql tal como pode ser feito em NOT IN()
        // se fosse garantido NOT IN() contra injeçao de sql eu faria com notint mais performatico e mais fáci.
        for($i = 0; $i < count($post_data["parameters"]["elements"]); $i++) {
            $element = $post_data["parameters"]["elements"][$i];
            if( $element["etype"] != "link"){
                continue;
            }
            $buffer_links = $mysql->DataTable("select * from diagram_relationship_link where diagram_relationship_element_id_reference = ?", [$element["id"]]);
            for($j = 0; $j < count($buffer_links); $j++) {
                $existe = false;
                for($k = 0; $k < count($element["to"]); $k++) {
                    if( $buffer_links[$j]["id"] ==  $element["to"][$k]["id"]) {
                        $existe = true;
                        break;
                    }
                }
                if( ! $existe ){
                    for($k = 0; $k < count($element["from"]); $k++) {
                        if( $buffer_links[$j]["id"] ==  $element["from"][$k]["id"]) {
                            $existe = true;
                            break;
                        }
                    }
                }
                if( ! $existe ){
                    array_push($sqls, "DELETE FROM diagram_relationship_link WHERE id = ?");
                    array_push($valuess, [ $buffer_links[$j]["id"] ]);
                }
            }
        }

        for($i = 0; $i < count($post_data["parameters"]["elements"]); $i++) {
            $element = $post_data["parameters"]["elements"][$i];
            $buffer_references = $mysql->DataTable("SELECT * FROM diagram_relationship_element_reference WHERE entity_id = ? ", [$element["entity_id"]]) ;
            for($j = 0; $j < count($buffer_references); $j++){
                $existe = false;
                for($k = 0; $k < count($element["references"]); $k++){
                    $reference = $element["references"][$k];
                    if( $reference["id"] == $buffer_references[$j]["id"]){
                        $existe = true;
                        break;
                    }
                }
                if( ! $existe ){
                    array_push($sqls, "DELETE FROM diagram_relationship_element_reference WHERE id = ?");
                    array_push($valuess, [ $buffer_references[$j]["id"] ]);
                }
            }
        }

        $buffer_elements = $mysql->DataTable("SELECT * FROM diagram_relationship_element WHERE  diagram_relationship_id = ? ", [$post_data["parameters"]["id"]]) ;
        for($i = 0; $i < count($buffer_elements); $i++){
            $existe = false;
            for($k = 0; $k < count($post_data["parameters"]["elements"]); $k++) {
                if($post_data["parameters"]["elements"][$k]["id"] == $buffer_elements[$i]["id"]){
                    $existe = true;
                    break;
                }
            }
            if( ! $existe ){
                array_push($sqls, "DELETE FROM diagram_relationship_element WHERE id = ?");
                array_push($valuess, [ $buffer_elements[$i]["id"] ]);
            }
        }

        for($i = 0; $i < count($post_data["parameters"]["elements"]); $i++) {
            $element = $post_data["parameters"]["elements"][$i];
            $buffer_classification = $mysql->DataTable("SELECT * FROM entity_classification_item WHERE entity_id = ? ", [$element["entity_id"]]) ;
            for($j = 0; $j < count($buffer_classification); $j++){
                $existe = false;
                for($k = 0; $k < count($element["classification"]); $k++){
                    $classification = $element["classification"][$k];
                    if( $classification["id"] == $buffer_classification[$j]["id"]){
                        $existe = true;
                        break;
                    }
                }
                if( ! $existe ){
                    array_push($sqls, "DELETE FROM entity_classification_item WHERE id = ?");
                    array_push($valuess, [ $buffer_classification[$j]["id"] ]);
                }
            }
        }


        array_push( $sqls ,"INSERT INTO diagram_relationship_history(id, person_id, diagram_relationship_id, json) values(?, ?, ?, ?)");
        array_push($valuess, [ $mysql->gen_uuid(), $user->id, $post_data["parameters"]["id"], json_encode($post_data["parameters"]) ]);


        
        return ( $mysql->ExecuteNoQuery($sqls, $valuess) > 0 );
    }

}

?>
