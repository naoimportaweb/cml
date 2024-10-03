<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";
require_once dirname(dirname(dirname(__DIR__))) . "/api/json.php";

class EntityBox{
    private $id = null;
    private $entity_id = null;
    private $etype = null;
    private $mapa = null;
    private $x = null;
    private $y = null;
    private $h = null;
    private $w = null;
    private $text_label = null;
    private $data_extra = null;
    private $full_description = null;
    private $wikipedia = null;
    private $references = null;
    private $to_entity = [];
    private $from_entity = [];

    function __construct($mapa) { 
        $this->mapa = $mapa;
    }

    public function subtractX($min_x){
        $this->x = $this->x - $min_x + 5;
    }
    public function subtractY($min_y){
        $this->y = $this->y - $min_y + 5;
    }

    public function toJson(){
        $buffer = array("id" => $this->id, "entity_id" => $this->entity_id, "etype" => $this->etype, "x" => $this->x, "y" => $this->y, "h" => $this->h, "w" => $this->w, "text_label" => $this->text_label, "full_description" => $this->full_description, "wikipedia" => $this->wikipedia, "references" => $this->references, "to" => [], "from" => []);

        //foreach( $this->references as $reference) {
        //    array_push($buffer["references"], $reference );
        //}

        if( $this->etype == "link") {
            foreach( $this->to_entity as $_to ) {
                array_push($buffer["to"], $_to->toJson() );
            }
            foreach( $this->from_entity as $_from ) {
                array_push($buffer["from"], $_from->toJson() );
            }
        }

        return $buffer;
    }

    public function loadData($data_table){
        $this->id           = $data_table["id"];
        $this->entity_id    = $data_table["entity_id"];
        $this->etype        = $data_table["etype"];
        $this->x            = $data_table["x"];
        $this->y            = $data_table["y"];
        $this->h            = $data_table["h"];
        $this->w            = $data_table["w"];
        $this->text_label   = $data_table["text_label"];
        $this->data_extra   = $data_table["data_extra"];
        $this->full_description = $data_table["full_description"];
        $this->wikipedia        = $data_table["wikipedia"];
    }

    public function loadReferences(){
        $mysql = new Mysql("");
        $this->references = $mysql->DataTable("SELECT drer.id, drer.title, drer.link1, drer.link2, drer.link3 FROM diagram_relationship_element_reference AS drer where drer.entity_id = ?", [ $this->entity_id]);
    }

    public function loadLinks(){
        $mysql = new Mysql("");
        if( $this->etype == "link" ){
            $buffer_elements_from = $mysql->DataTable("SELECT drl.diagram_relationship_element_id as id FROM diagram_relationship_link AS drl where drl.diagram_relationship_element_id_reference = ? and ltype = 1", [ $this->id ]);
            $buffer_elements_to = $mysql->DataTable("SELECT drl.diagram_relationship_element_id as id FROM diagram_relationship_link AS drl where drl.diagram_relationship_element_id_reference = ? and ltype = 2", [ $this->id ]);
        
            foreach( $buffer_elements_from  as $_from ){
                error_log("From: " . $_from["id"], 0);
                $buffer_from = $this->mapa->getElementById( $_from["id"] );
                if( $buffer_from != null) {
                    array_push( $this->from_entity, $buffer_from );
                }
            }
            foreach( $buffer_elements_to    as $_to   ){
                error_log("TO: " . $_to["id"], 0);
                $buffer_to   = $this->mapa->getElementById( $_to["id"] );
                if( $buffer_to != null) {
                    array_push( $this->to_entity, $buffer_to );
                }
            }
        }
    }


    public function getId(){
        return $this->id;
    }

    public function getX(){
        return $this->x;
    }

    public function getY(){
        return $this->y;
    }

}



?>