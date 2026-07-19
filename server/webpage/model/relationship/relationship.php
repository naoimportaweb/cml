<?php


require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";
require_once dirname(dirname(dirname(__DIR__))) . "/api/json.php";
require_once __DIR__ . "/entity_box.php";

class Relationship{
    private $id = null;
    private $domain = null;
    private $keyword = null;
    private $name = null;
    private $elements = [];
    private $elements_por_id = [];
    private $elements_loaded = false;
    private $width = 0;
    private $height = 0;
    private $show_face = 0;

    function __construct($id, $domain) {
        $this->domain = $domain;
        $this->id = $id;
        $this->load($id);
        $this->loadElements();
    }

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

    public function recalculateFrame(){
        if( count( $this->elements ) == 0 ){
            return;
        }
        $min_x = null;
        $min_y = null;
        foreach($this->elements as $element){
            if( $min_x === null || $element->getX() < $min_x ){
                $min_x = $element->getX();
            }
            if( $min_y === null || $element->getY() < $min_y ){
                $min_y = $element->getY();
            }
        }
        foreach($this->elements as $element){
            $element->subtract($min_x, $min_y);
        }
        // As coordenadas mudaram; sem zerar aqui o getWidth/getHeight devolveria a
        // moldura calculada antes do deslocamento.
        $this->width  = 0;
        $this->height = 0;
    }

    public function load($id) {
        $mysql = new Mysql( $this->domain );
        $data_table = $mysql->DataTable( "SELECT * FROM diagram_relationship as drl WHERE drl.id = ?", [$id] );
        return $this->loadData( $data_table );
    }

    public function loadElements(){
        // Sem esta guarda uma segunda chamada empilha os mesmos elementos de novo, porque
        // loadData faz array_push no array existente.
        if( $this->elements_loaded ){
            return count( $this->elements );
        }
        $mysql = new Mysql( $this->domain );
        $buffer_elements =  $mysql->DataTable("SELECT ent.wikipedia as wikipedia, dre.id as id, ent.id as entity_id, ent.data_extra as data_extra, ent.text_label as text_label, ent.description as full_description, ent.etype, dre.x, dre.y, dre.w, dre.h  FROM entity as ent inner join diagram_relationship_element as dre on ent.id = dre.entity_id where dre.diagram_relationship_id = ? order by dre.creation_time asc", [  $this->id  ]);

        for($i = 0; $i < count( $buffer_elements ); $i++) {
            $buffer = new EntityBox($this, $this->domain);
            $buffer->loadData( $buffer_elements[$i] );
            array_push( $this->elements, $buffer );
            // Indice montado no mesmo laco: sem ele o getElementById varre a lista inteira
            // a cada linha de link, e loadLinksAll chama duas vezes por linha.
            $this->elements_por_id[ $buffer->getId() ] = $buffer;
        }

        // Antes cada elemento disparava 3 queries próprias (2 de link + 1 de referência),
        // e cada Mysql->DataTable abre uma conexão nova: num mapa de 272 elementos isso
        // eram ~800 conexões. Agora são 2 queries para o mapa inteiro.
        $this->loadLinksAll( $mysql );
        $this->loadReferencesAll( $mysql );
        // So carrega os rostos (base64 grande) quando o mapa esta com "Exibir PNG de rosto".
        if( $this->show_face ){
            $this->loadFacesAll( $mysql );
        }

        $this->elements_loaded = true;
        return count( $this->elements );
    }

    private function loadFacesAll($mysql){
        // Rosto proprio (entity_face) e rosto default do subtipo (sub_etype.face_default),
        // por entidade. Mesma resolucao do cliente desktop: proprio substitui a caixa, o do
        // subtipo vira badge. Uma query so para o mapa inteiro.
        $buffer = $mysql->DataTable("SELECT dre.entity_id as entity_id, ef.png_base64 as face, se.face_default as subtype_face
            FROM diagram_relationship_element as dre
            LEFT JOIN entity_face as ef ON ef.entity_id = dre.entity_id
            LEFT JOIN entity as ent ON ent.id = dre.entity_id
            LEFT JOIN sub_etype as se ON se.id = ent.sub_etype_id
            WHERE dre.diagram_relationship_id = ?", [ $this->id ]);
        $por_entidade = [];
        foreach( $buffer as $linha ){
            $por_entidade[ $linha["entity_id"] ] = $linha;
        }
        foreach( $this->elements as $element ){
            $eid = $element->getEntityId();
            if( ! isset( $por_entidade[ $eid ] ) ){
                continue;
            }
            $element->setFace( $por_entidade[ $eid ]["face"] );
            $element->setSubtypeFace( $por_entidade[ $eid ]["subtype_face"] );
        }
    }

    private function loadLinksAll($mysql){
        $buffer = $mysql->DataTable("SELECT drl.diagram_relationship_element_id as element_id, drl.diagram_relationship_element_id_reference as link_id, drl.ltype as ltype FROM diagram_relationship_link AS drl INNER JOIN diagram_relationship_element AS dre ON dre.id = drl.diagram_relationship_element_id_reference WHERE dre.diagram_relationship_id = ?", [ $this->id ]);
        foreach( $buffer as $linha ){
            $caixa_link  = $this->getElementById( $linha["link_id"] );
            $caixa_ponta = $this->getElementById( $linha["element_id"] );
            if( $caixa_link == null || $caixa_ponta == null ){
                continue;
            }
            if( $linha["ltype"] == 1 ){
                $caixa_link->addFrom( $caixa_ponta );
            } else if( $linha["ltype"] == 2 ){
                $caixa_link->addTo( $caixa_ponta );
            }
        }
    }

    private function loadReferencesAll($mysql){
        // As referências pertencem à entidade, não à caixa: duas caixas do mesmo mapa
        // podem apontar para a mesma entidade e compartilham a lista.
        $buffer = $mysql->DataTable("SELECT drer.entity_id as entity_id, drer.id as id, drer.title as title, drer.link1 as link1, drer.link2 as link2, drer.link3 as link3, drer.description as descricao FROM diagram_relationship_element_reference AS drer WHERE drer.entity_id IN (SELECT dre.entity_id FROM diagram_relationship_element AS dre WHERE dre.diagram_relationship_id = ?) ORDER BY drer.title", [ $this->id ]);

        $por_entidade = [];
        foreach( $buffer as $linha ){
            $entity_id = $linha["entity_id"];
            if( ! isset( $por_entidade[ $entity_id ] ) ){
                $por_entidade[ $entity_id ] = [];
            }
            array_push( $por_entidade[ $entity_id ], $linha );
        }
        foreach( $this->elements as $element ){
            $entity_id = $element->getEntityId();
            $element->setReferences( isset( $por_entidade[ $entity_id ] ) ? $por_entidade[ $entity_id ] : [] );
        }
    }

    private function loadData( $data_table ){
        if( count( $data_table ) == 0 ){
            throw new Exception("Mapa não encontrado.");
        }
        $this->id       = $data_table[0]["id"];
        $this->keyword  = $data_table[0]["keyword"];
        $this->name     = $data_table[0]["name"];
        $this->show_face = isset( $data_table[0]["show_face"] ) ? intval( $data_table[0]["show_face"] ) : 0;
    }

    public function toJson(){
        $buffer = array( "id" => $this->id, "keyword" => $this->keyword, "name" => $this->name , "show_face" => $this->show_face, "elements" => [], "width" => $this->getWidth(), "height" => $this->getHeight() );
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

    public function getId(){
        return $this->id;
    }

    public function getKeyword(){
        return $this->keyword;
    }

    public function getElementById($id){
        return isset( $this->elements_por_id[ $id ] ) ? $this->elements_por_id[ $id ] : null;
    }

}



?>
