<?php
// Linha do tempo para o site publico (somente leitura).
//
// ⚠️ DUPLICACAO CONSCIENTE, como no organograma: a projecao das datas e o desenho existem duas
// vezes -- aqui e em app/classlib/timeline/. No desktop a timeline nao guarda geometria
// nenhuma (a posicao de um evento E a data dele) e a coleta roda sobre o mapa carregado no
// cliente; nao ha o que reusar. Decisao do dono em 2026-10-06, caminho A do SPEC.md §11.
//
// As SEIS ORIGENS e a ordem de prioridade do dedup sao as mesmas do
// app/classlib/timeline/timeline_event.py. Mudou la, muda aqui -- e e por isso que os nomes
// das origens foram mantidos identicos, para a comparacao lado a lado ser possivel.
//
// Enquanto o desktop varre o mapa JA CARREGADO, aqui a coleta e em SQL: uma consulta por
// origem, todas presas ao mapa de origem da timeline. O caminho obvio -- carregar o mapa
// inteiro e varrer em PHP -- repetiria o trabalho do relationship.php sem ganhar nada.

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class Timeline{
    private $id = null;
    private $domain = null;
    private $name = null;
    private $keyword = null;
    private $mapa_id = null;
    private $mapa_nome = null;
    private $eventos = [];

    // Mesma ordem de PRIORIDADE_ORIGEM do timeline_event.py: quando duas origens dizem a
    // mesma coisa, fica a mais especifica. O que o analista marcou a mao ganha de qualquer
    // projecao.
    private static $PRIORIDADE = ["evento", "referencia", "vinculo", "classificacao",
                                  "entidade", "elemento"];

    function __construct($id, $domain) {
        $this->domain = $domain;
        $this->id = $id;
        $this->load();
    }

    // Publicos e estaticos de proposito: sao a parte que o app/test/web_timeline.py compara
    // com o desktop. Logica que nao da para chamar de fora nao da para vigiar.
    public static function data_limpa($valor){
        // Tolerante de proposito, como o parse_data do desktop: o mesmo campo chega como null,
        // "", "0000-00-00" (zero date do MySQL) ou com hora junto. Data ruim vira null e o
        // evento simplesmente nao entra -- um mapa mal cadastrado nao pode derrubar o desenho.
        if( $valor === null ){ return null; }
        $texto = trim( (string)$valor );
        if( $texto === "" || substr($texto, 0, 4) === "0000" ){ return null; }
        $texto = explode(" ", explode("T", $texto)[0])[0];
        if( ! preg_match('/^\d{4}-\d{2}-\d{2}$/', $texto) ){ return null; }
        return $texto;
    }

    public static function normalizar($origem, $titulo, $detalhe, $inicio, $fim){
        $inicio = self::data_limpa( $inicio );
        $fim    = self::data_limpa( $fim );
        if( $inicio === null && $fim === null ){
            return null;   // sem data nao ha evento: a timeline nao inventa data
        }
        if( $inicio === null ){ $inicio = $fim; $fim = null; }
        if( $fim !== null && $fim < $inicio ){
            // Periodo invertido e erro de cadastro, nao motivo para sumir com o evento.
            $troca = $inicio; $inicio = $fim; $fim = $troca;
        }
        return array( "origem" => $origem, "titulo" => trim((string)$titulo),
                      "detalhe" => trim((string)$detalhe),
                      "inicio" => $inicio, "fim" => $fim );
    }

    private function load(){
        $mysql = new Mysql( $this->domain );
        $cab = $mysql->DataTable(
            "SELECT dt.id, dt.text_label, dt.keyword, dt.diagram_relationship_id, dr.name AS mapa_nome
               FROM diagram_timeline AS dt
               LEFT JOIN diagram_relationship AS dr ON dr.id = dt.diagram_relationship_id
              WHERE dt.id = ?", [ $this->id ] );
        if( count( $cab ) == 0 ){
            throw new Exception("Linha do tempo não encontrada.");
        }
        $this->name      = $cab[0]["text_label"];
        $this->keyword   = $cab[0]["keyword"];
        $this->mapa_id   = $cab[0]["diagram_relationship_id"];
        $this->mapa_nome = $cab[0]["mapa_nome"];

        $brutos = [];

        // 1) Eventos marcados. Pertencem a TIMELINE, nao ao mapa -- existem mesmo numa
        //    timeline solta.
        foreach( $mysql->DataTable(
            "SELECT dte.text_label, dte.start_date, dte.end_date, ent.text_label AS entidade
               FROM diagram_timeline_event AS dte
               LEFT JOIN entity AS ent ON ent.id = dte.entity_id
              WHERE dte.diagram_timeline_id = ?", [ $this->id ] ) as $r ){
            array_push( $brutos, self::normalizar("evento", $r["text_label"], $r["entidade"],
                                               $r["start_date"], $r["end_date"]) );
        }

        // As outras cinco sao PROJECAO do mapa de origem. Sem mapa, a timeline so tem os
        // eventos marcados -- e isso e legitimo, nao falta de dado.
        if( $this->mapa_id !== null && $this->mapa_id !== "" ){
            $brutos = array_merge( $brutos, $this->projetar( $mysql ) );
        }

        $this->eventos = self::consolidar( $brutos );
    }

    public static function consolidar($brutos){
        // Dedup por (titulo, inicio, fim), ficando a origem de maior prioridade: a data da
        // entidade costuma estar repetida na caixa do mapa.
        $escolhidos = [];
        foreach( $brutos as $e ){
            if( $e === null ){ continue; }
            $chave = $e["titulo"] . "|" . $e["inicio"] . "|" . (string)$e["fim"];
            $atual = isset( $escolhidos[$chave] ) ? $escolhidos[$chave] : null;
            if( $atual === null || self::prioridade($e) < self::prioridade($atual) ){
                $escolhidos[$chave] = $e;
            }
        }
        $saida = array_values( $escolhidos );
        // Mesma ordem de leitura do desktop: por inicio, depois o mais curto, depois alfabetica.
        usort( $saida, function($a, $b){
            if( $a["inicio"] !== $b["inicio"] ){ return strcmp($a["inicio"], $b["inicio"]); }
            $fa = $a["fim"] === null ? $a["inicio"] : $a["fim"];
            $fb = $b["fim"] === null ? $b["inicio"] : $b["fim"];
            if( $fa !== $fb ){ return strcmp($fa, $fb); }
            return strcmp($a["titulo"], $b["titulo"]);
        } );
        return $saida;
    }

    private static function prioridade($evento){
        $i = array_search( $evento["origem"], self::$PRIORIDADE );
        return $i === false ? count(self::$PRIORIDADE) : $i;
    }

    private function projetar($mysql){
        $saida = [];
        $mapa = $this->mapa_id;

        // 2) Caixa no mapa.
        foreach( $mysql->DataTable(
            "SELECT ent.text_label AS nome, dre.start_date, dre.end_date
               FROM diagram_relationship_element AS dre
               LEFT JOIN entity AS ent ON ent.id = dre.entity_id
              WHERE dre.diagram_relationship_id = ? AND ent.etype <> 'link'", [ $mapa ] ) as $r ){
            array_push( $saida, self::normalizar("elemento", $r["nome"], "no mapa",
                                              $r["start_date"], $r["end_date"]) );
        }

        // 3) Entidade global.
        foreach( $mysql->DataTable(
            "SELECT DISTINCT ent.text_label AS nome, ent.start_date, ent.end_date
               FROM diagram_relationship_element AS dre
               INNER JOIN entity AS ent ON ent.id = dre.entity_id
              WHERE dre.diagram_relationship_id = ? AND ent.etype <> 'link'", [ $mapa ] ) as $r ){
            array_push( $saida, self::normalizar("entidade", $r["nome"], "",
                                              $r["start_date"], $r["end_date"]) );
        }

        // 4) Classificacao datada.
        foreach( $mysql->DataTable(
            "SELECT ent.text_label AS nome, cl.text_label AS classificacao,
                    ci.text_label AS escolha, eci.start_date, eci.end_date
               FROM diagram_relationship_element AS dre
               INNER JOIN entity AS ent ON ent.id = dre.entity_id
               INNER JOIN entity_classification_item AS eci ON eci.entity_id = ent.id
               LEFT  JOIN classification_item AS ci ON ci.id = eci.classification_item_id
               LEFT  JOIN classification AS cl ON cl.id = ci.classification_id
              WHERE dre.diagram_relationship_id = ?", [ $mapa ] ) as $r ){
            $titulo = $r["nome"] . " — " . (string)$r["classificacao"] . ": " . (string)$r["escolha"];
            array_push( $saida, self::normalizar("classificacao", $titulo, $r["nome"],
                                              $r["start_date"], $r["end_date"]) );
        }

        // 5) Referencia com data = acontecimento. Vale para entidade E para vinculo.
        foreach( $mysql->DataTable(
            "SELECT DISTINCT drer.title AS titulo, ent.text_label AS nome,
                    drer.start_date, drer.end_date
               FROM diagram_relationship_element AS dre
               INNER JOIN entity AS ent ON ent.id = dre.entity_id
               INNER JOIN diagram_relationship_element_reference AS drer ON drer.entity_id = ent.id
              WHERE dre.diagram_relationship_id = ?", [ $mapa ] ) as $r ){
            array_push( $saida, self::normalizar("referencia", $r["titulo"], $r["nome"],
                                              $r["start_date"], $r["end_date"]) );
        }

        // 6) Vinculo: UM EVENTO POR PONTA DATADA. As duas pontas podem ter periodos
        //    diferentes (A entrou em 1998, B saiu em 2003) e achatar isso perderia dado.
        //    O rotulo e "origens → destinos", montado depois para nao fazer N+1 aqui.
        // ATENCAO ao sentido das duas colunas, que e contraintuitivo e ja me pegou:
        //   diagram_relationship_element_id_reference = a caixa do VINCULO
        //   diagram_relationship_element_id           = a caixa da PONTA (a entidade)
        // E ltype: 1 = ponta "de", 2 = ponta "para". E a convencao do MapRelationship/001.php
        // e do relationship.php desta mesma pasta; inverter isso faz o rotulo sair vazio de um
        // lado e com tudo do outro, sem erro nenhum aparecer.
        $pontas = $mysql->DataTable(
            "SELECT dre_link.id                         AS link_element_id,
                    ent_link.text_label                 AS verbo,
                    ent_ponta.text_label                AS ponta,
                    drl.ltype                           AS ltype,
                    drl.start_date, drl.end_date
               FROM diagram_relationship_link AS drl
               INNER JOIN diagram_relationship_element AS dre_link
                       ON dre_link.id = drl.diagram_relationship_element_id_reference
               LEFT  JOIN entity AS ent_link  ON ent_link.id  = dre_link.entity_id
               INNER JOIN diagram_relationship_element AS dre_ponta
                       ON dre_ponta.id = drl.diagram_relationship_element_id
               LEFT  JOIN entity AS ent_ponta ON ent_ponta.id = dre_ponta.entity_id
              WHERE dre_link.diagram_relationship_id = ?", [ $mapa ] );

        // ltype separa as duas pontas (de um lado e do outro); o rotulo junta as duas listas.
        $por_link = [];
        foreach( $pontas as $p ){
            $chave = $p["link_element_id"];
            if( ! isset($por_link[$chave]) ){
                $por_link[$chave] = array("verbo" => $p["verbo"], "a" => [], "b" => [], "linhas" => []);
            }
            $lado = ( intval($p["ltype"]) == 1 ) ? "a" : "b";   // 1 = de, 2 = para
            array_push( $por_link[$chave][$lado], (string)$p["ponta"] );
            array_push( $por_link[$chave]["linhas"], $p );
        }
        foreach( $por_link as $link ){
            $rotulo = implode(", ", array_filter($link["a"])) . " → " . implode(", ", array_filter($link["b"]));
            foreach( $link["linhas"] as $p ){
                array_push( $saida, self::normalizar("vinculo", (string)$link["verbo"], $rotulo,
                                                  $p["start_date"], $p["end_date"]) );
            }
        }
        return $saida;
    }

    public function toJson(){
        return array( "id" => $this->id, "name" => $this->name, "keyword" => $this->keyword,
                      "mapa_id" => $this->mapa_id, "mapa_nome" => $this->mapa_nome,
                      "eventos" => $this->eventos );
    }
}

?>
