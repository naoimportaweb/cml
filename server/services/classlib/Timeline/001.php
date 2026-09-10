<?php

//error_reporting(E_ALL);

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

/*
 * Timeline: o terceiro tipo de diagrama.
 *
 * E um documento como o mapa e o organograma (create/load/save, aparece no Map.search), mas
 * nao guarda geometria: a posicao de um evento e a data dele. O que se persiste e o nome, o
 * mapa de origem (opcional) e os eventos marcados a mao.
 *
 * Com diagram_relationship_id preenchido a timeline PROJETA aquele mapa — quem faz a
 * projecao e o cliente, que ja carrega o mapa inteiro pelo MapRelationship.load e tem todas
 * as datas em maos. Duplicar aqui a leitura do mapa so criaria uma segunda verdade.
 */
class Timeline
{
    public function create( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $p = $post_data["parameters"];
        $mapa = ( isset($p["diagram_relationship_id"]) && trim(strval($p["diagram_relationship_id"])) != "" ) ? $p["diagram_relationship_id"] : null;
        $sql = "INSERT INTO diagram_timeline (id, text_label, keyword, diagram_relationship_id, person_id) values(?, ?, ?, ?, ?)";
        return $mysql->ExecuteNoQuery($sql, [ $p["id"], $p["text_label"], $p["keyword"], $mapa, $user->id ]) > 0;
    }

    public function exists( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $linhas = $mysql->DataTable("SELECT id FROM diagram_timeline WHERE LOWER(text_label) = LOWER(?) AND id <> ?",
            [ $post_data["parameters"]["text_label"], $post_data["parameters"]["id"] ]);
        return count($linhas) > 0;
    }

    public function load( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $linhas = $mysql->DataTable("SELECT * FROM diagram_timeline WHERE id = ?", [ $post_data["parameters"]["id"] ]);
        if( count($linhas) == 0 ) {
            return null;
        }
        $timeline = $linhas[0];
        // O nome da entidade vem junto (LEFT JOIN: entity_id e opcional) para a timeline
        // desenhar o subtitulo sem uma segunda ida ao servidor por evento.
        $timeline["events"] = $mysql->DataTable(
            "SELECT dte.id, dte.diagram_timeline_id, dte.entity_id, dte.text_label, dte.description, "
          . "dte.start_date, dte.end_date, dte.format_date, ent.text_label as entity_text_label "
          . "FROM diagram_timeline_event AS dte "
          . "LEFT JOIN entity AS ent ON ent.id = dte.entity_id "
          . "WHERE dte.diagram_timeline_id = ? ORDER BY dte.start_date ASC, dte.text_label ASC",
            [ $post_data["parameters"]["id"] ]);
        return $timeline;
    }

    public function save( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $p = $post_data["parameters"];
        $mapa = ( isset($p["diagram_relationship_id"]) && trim(strval($p["diagram_relationship_id"])) != "" ) ? $p["diagram_relationship_id"] : null;
        $sql = "INSERT INTO diagram_timeline (id, text_label, keyword, diagram_relationship_id, person_id) values(?, ?, ?, ?, ?) "
             . "ON DUPLICATE KEY UPDATE text_label = ?, keyword = ?, diagram_relationship_id = ?";
        $valores = [ $p["id"], $p["text_label"], $p["keyword"], $mapa, $user->id,
                     $p["text_label"], $p["keyword"], $mapa ];
        return $mysql->ExecuteNoQuery($sql, $valores) > 0;
    }

    public function delete( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        // Os eventos saem antes: a FK de diagram_timeline_event impede apagar o documento
        // com evento pendurado, e nao ha cascata em lugar nenhum deste schema.
        $sqls = [ "DELETE FROM diagram_timeline_event WHERE diagram_timeline_id = ?",
                  "DELETE FROM diagram_timeline WHERE id = ?" ];
        $valores = [ [ $post_data["parameters"]["id"] ], [ $post_data["parameters"]["id"] ] ];
        return $mysql->ExecuteNoQuery($sqls, $valores) > 0;
    }
}

?>
