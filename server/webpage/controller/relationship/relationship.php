<?php
require_once dirname(dirname(__DIR__)) . "/model/relationship/relationship.php";

class RelationshipController{
    private $mapa = null;
    private $loaded = false;
    function __construct($id, $domain) { 
        $this->mapa = new Relationship( $id , $domain );
        $this->mapa->recalculateFrame();
    }

    public function getMapa(){
        return $this->mapa;
    }

    public function getWidth(){
        return $this->mapa->getWidth();
    }

    public function getHeight(){
        return $this->mapa->getHeight();
    }

    public function getId(){
        return $this->mapa->getId();
    }

    public function getElements(){
        if( ! $this->loaded ) {
            $carregado = $this->mapa->loadElements() > 0;
            $this->mapa->recalculateFrame();
            $this->loaded = $carregado ; 
        }
        return $this->mapa->getElements();
    }

    public function toJson(){
        return $this->mapa->toJson();
    }
}

?>