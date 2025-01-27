<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";
require_once dirname(dirname(dirname(__DIR__))) . "/api/json.php";

class EntityBox{
    private $id = null;
    private $entity_id = null;
    private $etype = null;
    private $mapa = null;
    private $domain = null;
    private $x = null;
    private $y = null;
    private $h = null;
    private $w = null;
    private $center_x = null;
    private $center_y = null;
    private $text_label = null;
    private $data_extra = null;
    private $full_description = null;
    private $wikipedia = null;
    private $references = null;
    private $to_entity = [];
    private $from_entity = [];

    function __construct($mapa, $domain) {
        $this->domain = $domain; 
        $this->mapa = $mapa;
    }

    public function subtractX($min_x){
        $this->x = $this->x - $min_x + 5;
        $this->center_x =   $this->x + intval($this->w);
    }
    public function subtractY($min_y){
        $this->y = $this->y - $min_y + 5;
        $this->center_y =   $this->y + intval($this->h);
    }

    public function toJson(){
        $buffer = array("id" => $this->id, "entity_id" => $this->entity_id, "etype" => $this->etype, "x" => $this->x, "y" => $this->y, "h" => $this->h, "w" => $this->w, "text_label" => $this->text_label, "full_description" => $this->full_description, "wikipedia" => $this->wikipedia, "references" => $this->references, "to" => [], "from" => [], "center_x" => $this->center_x, "center_y" => $this->center_y);

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
        $this->w            = strlen( $data_table["text_label"] ) * 5;
        $buffer = strlen( $data_table["text_label"] ) * 5; 
        $this->center_x =   $this->x + intval($buffer  / 2);
        $this->center_y =   $this->y - intval($this->h / 2);
        $this->text_label   = $data_table["text_label"];
        $this->data_extra   = $data_table["data_extra"];
        $this->full_description = $data_table["full_description"];
        $this->wikipedia        = $data_table["wikipedia"];
    }

    public function loadReferences(){
        $mysql = new Mysql( $this->domain );
        $this->references = $mysql->DataTable("SELECT drer.id, drer.title, drer.link1, drer.link2, drer.link3 FROM diagram_relationship_element_reference AS drer where drer.entity_id = ?", [ $this->entity_id]);
    }

    public function loadLinks(){
        $mysql = new Mysql( $this->domain );
        if( $this->etype == "link" ){
            $buffer_elements_from = $mysql->DataTable("SELECT drl.diagram_relationship_element_id as id FROM diagram_relationship_link AS drl where drl.diagram_relationship_element_id_reference = ? and ltype = 1", [ $this->id ]);
            $buffer_elements_to = $mysql->DataTable("SELECT drl.diagram_relationship_element_id as id FROM diagram_relationship_link AS drl where drl.diagram_relationship_element_id_reference = ? and ltype = 2", [ $this->id ]);
        
            foreach( $buffer_elements_from  as $_from ){
                $buffer_from = $this->mapa->getElementById( $_from["id"] );
                if( $buffer_from != null) {
                    array_push( $this->from_entity, $buffer_from );
                }
            }
            foreach( $buffer_elements_to    as $_to   ){
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

    public function getW(){
        $this->w            = strlen( $this->text_label ) * 10;
        return $this->w;
    }

    public function getH(){
        return $this->h;
    }

}



?>