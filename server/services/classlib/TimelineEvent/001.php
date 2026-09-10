<?php

//error_reporting(E_ALL);

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

/*
 * Eventos que o analista MARCA numa timeline (diagram_timeline_event).
 *
 * Endpoint proprio, e nao dentro do Timeline.save: marcar um evento grava na hora — como o
 * Entity.save_images faz com as imagens. Passar pelo save do documento mandaria a lista
 * inteira de volta a cada evento novo.
 */
class TimelineEvent
{
    public function save( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $p = $post_data["parameters"];
        // entity_id vazio tem que virar NULL de verdade: "" quebraria a FK de entity.
        $entity_id = ( isset($p["entity_id"]) && trim(strval($p["entity_id"])) != "" ) ? $p["entity_id"] : null;
        $sql = "INSERT INTO diagram_timeline_event (id, diagram_timeline_id, entity_id, person_id, text_label, description, start_date, end_date, format_date) "
             . "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?) "
             . "ON DUPLICATE KEY UPDATE entity_id=?, text_label=?, description=?, start_date=?, end_date=?, format_date=?";
        $valores = [ $p["id"], $p["diagram_timeline_id"], $entity_id, $user->id, $p["text_label"], $p["description"], $p["start_date"], $p["end_date"], $p["format_date"],
                     $entity_id, $p["text_label"], $p["description"], $p["start_date"], $p["end_date"], $p["format_date"] ];
        return $mysql->ExecuteNoQuery($sql, $valores) > 0;
    }

    public function delete( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        // O diagram_timeline_id entra no WHERE como trava: um cliente com o id de um evento
        // de outra timeline nao apaga nada.
        $sql = "DELETE FROM diagram_timeline_event WHERE id = ? AND diagram_timeline_id = ?";
        return $mysql->ExecuteNoQuery($sql, [ $post_data["parameters"]["id"], $post_data["parameters"]["diagram_timeline_id"] ]) > 0;
    }
}

?>
