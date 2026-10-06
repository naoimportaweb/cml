<?php
// Organograma para o site publico (somente leitura).
//
// ⚠️ DUPLICACAO CONSCIENTE. O layout e o desenho do organograma existem DUAS VEZES no projeto:
// aqui (PHP+JS, para a web) e no desktop (app/classlib/organization_chart/). O desktop calcula
// o layout no cliente e o banco guarda so o `x` -- entao nao ha geometria para a web reusar, e
// mostrar o organograma aqui exige recalcular tudo.
//
// Isto foi decidido pelo dono em 2026-10-06, sabendo do custo: TODA mudanca no desenho ou no
// layout do organograma do desktop tem de ser espelhada aqui a mao, senao os dois divergem
// calados. Quem mexer em organization_chart_item.py e nao mexer aqui deixa a web mentindo.
// As duas alternativas recusadas estao no SPEC.md §12.
//
// O que ESTE arquivo faz e so trazer a arvore do banco; o layout roda no JS da view, que e
// onde ha metrica de fonte para medir a caixa.

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class OrganizationChart{
    private $id = null;
    private $domain = null;
    private $name = null;
    private $organizacao = null;
    private $itens = [];

    function __construct($id, $domain) {
        $this->domain = $domain;
        $this->id = $id;
        $this->load();
    }

    private function load(){
        $mysql = new Mysql( $this->domain );
        $cabecalho = $mysql->DataTable(
            "SELECT oc.id, oc.text_label, ent.text_label AS organizacao
               FROM organization_chart AS oc
               LEFT JOIN entity AS ent ON ent.id = oc.organization_id
              WHERE oc.id = ?", [ $this->id ] );
        if( count( $cabecalho ) == 0 ){
            throw new Exception("Organograma não encontrado.");
        }
        $this->name = $cabecalho[0]["text_label"];
        $this->organizacao = $cabecalho[0]["organizacao"];

        // Os itens em UMA consulta, e as entidades de todos eles em OUTRA. O caminho obvio --
        // um SELECT de entidades por item -- e um N+1 que esta camada ja pagou antes.
        $this->itens = $mysql->DataTable(
            "SELECT id, text_label, etype, x, organization_chart_item_parent_id
               FROM organization_chart_item
              WHERE organization_chart_id = ?
              ORDER BY organization_chart_item_parent_id, id", [ $this->id ] );

        $entidades = $mysql->DataTable(
            "SELECT ocie.organization_chart_item_id AS item_id,
                    ent.text_label                  AS nome,
                    ent.etype                       AS etype,
                    ocie.start_date                 AS start_date,
                    ocie.end_date                   AS end_date
               FROM organization_chart_item_entity AS ocie
               INNER JOIN organization_chart_item AS oci ON oci.id = ocie.organization_chart_item_id
               LEFT  JOIN entity AS ent ON ent.id = ocie.entity_id
              WHERE oci.organization_chart_id = ?
              ORDER BY ocie.creation_time", [ $this->id ] );

        $por_item = [];
        foreach( $entidades as $e ){
            $chave = $e["item_id"];
            if( ! isset( $por_item[ $chave ] ) ){
                $por_item[ $chave ] = [];
            }
            // Entidade apagada deixa o LEFT JOIN com nome nulo: nao vira linha fantasma.
            if( $e["nome"] === null || trim($e["nome"]) === "" ){
                continue;
            }
            array_push( $por_item[ $chave ], array(
                "nome"       => $e["nome"],
                "etype"      => $e["etype"],
                "start_date" => $e["start_date"],
                "end_date"   => $e["end_date"] ) );
        }
        for( $i = 0; $i < count( $this->itens ); $i++ ){
            $chave = $this->itens[$i]["id"];
            $this->itens[$i]["entidades"] = isset( $por_item[ $chave ] ) ? $por_item[ $chave ] : [];
        }
    }

    public function getId(){ return $this->id; }
    public function getName(){ return $this->name; }

    public function toJson(){
        $saida = [];
        foreach( $this->itens as $item ){
            array_push( $saida, array(
                "id"        => $item["id"],
                "pai"       => $item["organization_chart_item_parent_id"],
                "texto"     => $item["text_label"],
                "etype"     => $item["etype"],
                "entidades" => $item["entidades"] ) );
        }
        return array( "id" => $this->id, "name" => $this->name,
                      "organizacao" => $this->organizacao, "itens" => $saida );
    }
}

?>
