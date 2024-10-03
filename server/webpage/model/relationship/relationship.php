<?php


require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";
require_once dirname(dirname(dirname(__DIR__))) . "/api/json.php";
require_once __DIR__ . "/entity_box.php";

class Relationship{
    private $id = null;
    private $keyword = null;
    private $name = null;
    private $elements = [];
    private $width = 0;
    private $height = 0;

    public function getWidth(){
        if( $this->width == 0 ){
            foreach($this->elements as $element){
                if( $element->getX()  + $element->getW() > $this->width  ) {
                    $this->width  = $element->getX()  + $element->getW();
                }
            }
        }
        return $this->width + 10;
    }

    public function getHeight(){
        if( $this->height == 0 ){
            foreach($this->elements as $element){
                if( $element->getY() + $element->getH() > $this->height  ) {
                    $this->height  = $element->getY() + $element->getH();
                }
            }
        }
        return $this->height + 10;
    }

    function __construct($id) { 
        $this->id = $id;
        $this->load($id);
        $this->loadElements();
    }

    public function recalculateFrame(){
        $min_x = 1500000;
        $min_y = 1500000;
        
        

        foreach($this->elements as $element){
            if($element->getX()  < $min_x){
                $min_x = $element->getX() ;
            }
            if($element->getY()  < $min_y){
                $min_y = $element->getY() ;
            }
        }
        foreach($this->elements as $element){
            $element->subtractX($min_x);
            $element->subtractY($min_y);
        }
        

    }
    public function load($id) {
        $mysql = new Mysql("");
        $data_table = $mysql->DataTable( "SELECT * FROM diagram_relationship as drl WHERE drl.id = ?", [$id] );
        return $this->loadData( $data_table );
    }

    public function loadElements(){
        $mysql = new Mysql("");
        $buffer_elements =  $mysql->DataTable("SELECT ent.wikipedia as wikipedia, dre.id as id, ent.id as entity_id, ent.data_extra as data_extra, ent.text_label as text_label, ent.description as full_description, ent.etype, dre.x, dre.y, dre.w, dre.h  FROM entity as ent inner join diagram_relationship_element as dre on ent.id = dre.entity_id where dre.diagram_relationship_id = ? order by dre.creation_time asc", [  $this->id  ]);
        
        for($i = 0; $i < count( $buffer_elements ); $i++) {
            $buffer = new EntityBox($this);
            $buffer->loadData( $buffer_elements[$i] );
            array_push( $this->elements, $buffer );
        }

        for($i = 0; $i < count( $this->elements ); $i++) {
            $this->elements[$i]->loadLinks();
            $this->elements[$i]->loadReferences();
        }
        
        return count( $this->elements );
    }

    private function loadData( $data_table ){
        $this->id       = $data_table[0]["id"];
        $this->keyword  = $data_table[0]["keyword"];
        $this->name     = $data_table[0]["name"];
    }

    public function toJson(){
        $buffer = array( "id" => $this->id, "keyword" => $this->keyword, "name" => $this->name , "elements" => [], "width" => $this->getWidth(), "height" => $this->getHeight() );
        for($i = 0; $i < count( $this->elements ); $i++) {
            array_push( $buffer["elements"], $this->elements[$i]->toJson() );
        }
        return $buffer;
    }

    public function getElements(){
        return $this->elements;
    }

    public function getName(){
        return $this->name;
    }

    public function getKeyword(){
        return $this->keyword;
    }

    public function getElementById($id){
        for($i = 0; $i < count( $this->elements ); $i++) {
            if( $this->elements[$i]->getId() == $id ) {
                return $this->elements[$i];
            }
        }
        return null;
    }

}



?>