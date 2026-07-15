<?php
require_once dirname(dirname(__DIR__)) . "/model/relationship/relationship_list.php";

class RelationshipListController{
    private $lista = null;

    function __construct($domain) {
        $this->lista = new RelationshipList( $domain );
    }

    public function getLista(){
        return $this->lista;
    }

    public function toJson(){
        return $this->lista->toJson();
    }
}

?>
