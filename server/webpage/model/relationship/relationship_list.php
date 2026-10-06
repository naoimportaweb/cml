<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class RelationshipList{
    private $domain = null;
    private $mapas = [];
    private $organogramas = [];
    private $timelines = [];

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

        // Organogramas. LEFT JOIN em person e em entity: organograma cujo autor sumiu, ou cuja
        // organizacao foi apagada, ainda deve aparecer -- some-lo da lista esconderia trabalho
        // feito. (O Map/001.php do desktop usa INNER e por isso some com eles.)
        $this->organogramas = $mysql->DataTable(
            "SELECT oc.id                AS id,
                    oc.text_label        AS name,
                    oc.creation_time     AS creation_time,
                    oc.modification_time AS modification_time,
                    pe.username          AS username,
                    ent.text_label       AS organizacao,
                    ( SELECT COUNT(*) FROM organization_chart_item AS oci
                       WHERE oci.organization_chart_id = oc.id ) AS itens
               FROM organization_chart AS oc
               LEFT JOIN person AS pe  ON pe.id  = oc.person_id
               LEFT JOIN entity AS ent ON ent.id = oc.organization_id
              ORDER BY oc.text_label", [] );

        // Timelines. O mapa de origem e OPCIONAL (timeline solta), por isso LEFT JOIN nele.
        $this->timelines = $mysql->DataTable(
            "SELECT dt.id                AS id,
                    dt.text_label        AS name,
                    dt.keyword           AS keyword,
                    dt.creation_time     AS creation_time,
                    dt.modification_time AS modification_time,
                    pe.username          AS username,
                    dt.diagram_relationship_id AS diagram_relationship_id,
                    dr.name              AS mapa_origem,
                    ( SELECT COUNT(*) FROM diagram_timeline_event AS dte
                       WHERE dte.diagram_timeline_id = dt.id ) AS eventos
               FROM diagram_timeline AS dt
               LEFT JOIN person AS pe ON pe.id = dt.person_id
               LEFT JOIN diagram_relationship AS dr ON dr.id = dt.diagram_relationship_id
              ORDER BY dt.text_label", [] );

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
        $orgs = [];
        foreach( $this->organogramas as $o ){
            array_push( $orgs, array(
                "id"                => $o["id"],
                "name"              => $o["name"],
                "organizacao"       => $o["organizacao"],
                "username"          => $o["username"],
                "creation_time"     => $o["creation_time"],
                "modification_time" => $o["modification_time"],
                "itens"             => intval( $o["itens"] )
            ) );
        }
        $tls = [];
        foreach( $this->timelines as $t ){
            array_push( $tls, array(
                "id"                => $t["id"],
                "name"              => $t["name"],
                "keyword"           => $t["keyword"],
                "mapa_origem"       => $t["mapa_origem"],
                "diagram_relationship_id" => $t["diagram_relationship_id"],
                "username"          => $t["username"],
                "creation_time"     => $t["creation_time"],
                "modification_time" => $t["modification_time"],
                "eventos"           => intval( $t["eventos"] )
            ) );
        }
        return array( "mapas" => $saida, "organogramas" => $orgs, "timelines" => $tls,
                      "total" => count( $saida ) + count( $orgs ) + count( $tls ) );
    }

    public function getOrganogramas(){
        return $this->organogramas;
    }

    public function getTimelines(){
        return $this->timelines;
    }

    public function getMapas(){
        return $this->mapas;
    }
}

?>
