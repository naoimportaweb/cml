<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

/**
 * Fila de geracao de report pelo rolhama.
 *
 * A trava e GLOBAL porque o CML tem um unico canal no rolhama (507): dois reports em
 * paralelo colidiriam la, e um poderia ler a resposta do outro. Quem garante e o indice
 * UNIQUE sobre a coluna gerada lock_global — nao ha "verifica e depois insere" na
 * aplicacao, que teria janela de corrida entre dois clientes.
 */
class ReportJob
{
    // Uma geracao longa (50 referencias, prefill em CPU) leva minutos. Passado isto sem
    // nenhum sinal de vida, o dono provavelmente morreu — senao um crash de cliente
    // travaria o recurso para todos, para sempre.
    const EXPIRA_SEGUNDOS = 2700;   // 45 min

    /**
     * Solta travas cujo dono sumiu. Roda antes de qualquer tentativa de aquisicao: e o
     * que impede um cliente morto de bloquear o resto indefinidamente.
     */
    private static function expirar($mysql){
        return $mysql->ExecuteNoQuery(
            "UPDATE report_job
                SET status = 'falhou',
                    erro = CONCAT('Expirou: sem sinal do cliente por mais de ', ?, 's.')
              WHERE status = 'executando'
                AND modification_time < DATE_SUB(NOW(), INTERVAL ? SECOND)",
            [ self::EXPIRA_SEGUNDOS, self::EXPIRA_SEGUNDOS ]);
    }

    /** O job em andamento, ou null. parameters: {} */
    public function current( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        self::expirar( $mysql );
        $r = $mysql->DataTable(
            "SELECT rj.*, dr.name AS mapa_name, pe.username AS username
               FROM report_job AS rj
               LEFT JOIN diagram_relationship AS dr ON dr.id = rj.diagram_relationship_id
               LEFT JOIN person AS pe ON pe.id = rj.person_id
              WHERE rj.status = 'executando' LIMIT 1", []);
        return count( $r ) > 0 ? $r[0] : null;
    }

    /**
     * Tenta pegar a trava. parameters: { diagram_relationship_id, canal, referencias_total }
     * Devolve {ok:true, id} ou {ok:false, ocupado_por:{...}} — nunca lanca por concorrencia:
     * "ja tem alguem gerando" e resposta normal, nao erro.
     */
    public function start( $ip, $user, $post_data, $domain ) {
        $p = $post_data["parameters"];
        $mysql = new Mysql( $domain );
        self::expirar( $mysql );

        $id = $mysql->gen_uuid();
        try {
            $mysql->ExecuteNoQuery(
                "INSERT INTO report_job(id, diagram_relationship_id, person_id, canal, status, progresso, referencias_total)
                 VALUES (?,?,?,?, 'executando', 'Iniciando…', ?)",
                [ $id, $p["diagram_relationship_id"], ($user != null ? $user->id : null),
                  isset($p["canal"]) ? $p["canal"] : null,
                  isset($p["referencias_total"]) ? $p["referencias_total"] : 0 ]);
        } catch (Exception $e) {
            // 1062 = o UNIQUE de lock_global barrou: ja existe um 'executando'. E o
            // caminho esperado quando dois clientes disputam, nao uma falha.
            if( strpos( $e->getMessage(), "1062" ) !== false || stripos( $e->getMessage(), "Duplicate" ) !== false ){
                $atual = $this->current( $ip, $user, $post_data, $domain );
                return array( "ok" => false, "ocupado_por" => $atual );
            }
            throw $e;
        }
        return array( "ok" => true, "id" => $id );
    }

    /**
     * Sinal de vida + progresso. parameters: { id, progresso }
     * Alem de alimentar a tela, o toque em modification_time e o que impede a propria
     * trava de expirar durante uma geracao longa e legitima.
     */
    public function progress( $ip, $user, $post_data, $domain ) {
        $p = $post_data["parameters"];
        $mysql = new Mysql( $domain );
        return $mysql->ExecuteNoQuery(
            "UPDATE report_job SET progresso = ? WHERE id = ? AND status = 'executando'",
            [ substr( (string) $p["progresso"], 0, 255 ), $p["id"] ]);
    }

    /** parameters: { id, document_id, referencias_lidas } */
    public function finish( $ip, $user, $post_data, $domain ) {
        $p = $post_data["parameters"];
        $mysql = new Mysql( $domain );
        $mysql->ExecuteNoQuery(
            "UPDATE report_job
                SET status = 'concluido', document_id = ?, referencias_lidas = ?,
                    progresso = 'Concluído', visto = 0
              WHERE id = ?",
            [ isset($p["document_id"]) ? $p["document_id"] : null,
              isset($p["referencias_lidas"]) ? $p["referencias_lidas"] : 0, $p["id"] ]);
        return array( "ok" => true );
    }

    /** parameters: { id, erro } */
    public function fail( $ip, $user, $post_data, $domain ) {
        $p = $post_data["parameters"];
        $mysql = new Mysql( $domain );
        $mysql->ExecuteNoQuery(
            "UPDATE report_job SET status = 'falhou', erro = ?, progresso = 'Falhou', visto = 0 WHERE id = ?",
            [ substr( (string) $p["erro"], 0, 2000 ), $p["id"] ]);
        return array( "ok" => true );
    }

    /**
     * Jobs terminados que o dono ainda nao viu — e o que alimenta o aviso na GUI.
     * parameters: {}
     */
    public function pending_notices( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        return $mysql->DataTable(
            "SELECT rj.id, rj.status, rj.diagram_relationship_id, rj.document_id, rj.erro,
                    rj.referencias_lidas, rj.referencias_total, rj.modification_time,
                    dr.name AS mapa_name
               FROM report_job AS rj
               LEFT JOIN diagram_relationship AS dr ON dr.id = rj.diagram_relationship_id
              WHERE rj.visto = 0 AND rj.status IN ('concluido','falhou') AND rj.person_id = ?
              ORDER BY rj.modification_time DESC",
            [ ($user != null ? $user->id : null) ]);
    }

    /** parameters: { id } */
    public function mark_seen( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        return $mysql->ExecuteNoQuery("UPDATE report_job SET visto = 1 WHERE id = ?",
                                      [ $post_data["parameters"]["id"] ]);
    }

    /** Historico do mapa. parameters: { diagram_relationship_id } */
    public function list_by_map( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        return $mysql->DataTable(
            "SELECT rj.*, pe.username AS username
               FROM report_job AS rj
               LEFT JOIN person AS pe ON pe.id = rj.person_id
              WHERE rj.diagram_relationship_id = ?
              ORDER BY rj.creation_time DESC LIMIT 20",
            [ $post_data["parameters"]["diagram_relationship_id"] ]);
    }
}

?>
