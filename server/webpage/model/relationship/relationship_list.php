<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class RelationshipList{
    private $domain = null;
    private $mapas = [];

    function __construct($domain) {
        $this->domain = $domain;
        $this->load();
    }

    public function load(){
        $mysql = new Mysql( $this->domain );

        // Uma query so para a lista inteira. As duas contagens sao subconsultas correlatas:
        // com dezenas de mapas isso e barato, e evita as N+1 que o resto desta camada ja
        // teve. Se a base crescer para milhares de mapas, paginar aqui.
        $sql = "SELECT dr.id                AS id,
                       dr.name              AS name,
                       dr.keyword           AS keyword,
                       dr.creation_time     AS creation_time,
                       dr.modification_time AS modification_time,
                       pe.username          AS username,
                       ( SELECT COUNT(*) FROM diagram_relationship_element AS dre
                          WHERE dre.diagram_relationship_id = dr.id ) AS elementos,
                       ( SELECT COUNT(DISTINCT drer.id)
                           FROM diagram_relationship_element_reference AS drer
                          WHERE drer.entity_id IN ( SELECT dre2.entity_id
                                                      FROM diagram_relationship_element AS dre2
                                                     WHERE dre2.diagram_relationship_id = dr.id ) ) AS referencias
                  FROM diagram_relationship AS dr
                  LEFT JOIN person AS pe ON pe.id = dr.person_id
                 ORDER BY dr.name";
        // LEFT JOIN e nao INNER: um mapa cujo autor sumiu ainda deve aparecer na lista.
        $this->mapas = $mysql->DataTable( $sql, [] );
        return count( $this->mapas );
    }

    public function toJson(){
        $saida = [];
        foreach( $this->mapas as $m ){
            array_push( $saida, array(
                "id"                => $m["id"],
                "name"              => $m["name"],
                "keyword"           => $m["keyword"],
                "username"          => $m["username"],
                "creation_time"     => $m["creation_time"],
                "modification_time" => $m["modification_time"],
                "elementos"         => intval( $m["elementos"] ),
                "referencias"       => intval( $m["referencias"] )
            ) );
        }
        return array( "mapas" => $saida, "total" => count( $saida ) );
    }

    public function getMapas(){
        return $this->mapas;
    }
}

?>
