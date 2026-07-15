<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";
require_once dirname(dirname(dirname(__DIR__))) . "/api/json.php";

/**
 * Documentos (PDF de report) anexados a mapas.
 *
 * Os bytes NAO ficam no banco: vao para data/documents/<sha256>.pdf, coberto pelo
 * "Deny from all" do data/.htaccess. O banco guarda o hash, o tamanho e os vinculos.
 * Isso mantem o mysqldump da copia entre bases leve e evita inchar o envelope RPC.
 *
 * O sha256 e a chave de deduplicacao: o mesmo PDF anexado a varios mapas grava o
 * arquivo uma vez e cria uma linha em document_map por mapa.
 */
class Document
{
    const MAX_BYTES = 33554432;   // 32 MiB — o post_max_size do host e 256M, mas o
                                  // envelope vem em base64 (+33%) e passa por json_decode.

    private static function pasta(){
        return dirname(dirname(dirname(__DIR__))) . "/data/documents";
    }

    private static function caminho($sha256){
        return self::pasta() . "/" . $sha256 . ".pdf";
    }

    /**
     * Recebe o PDF em base64, grava se ainda nao existir e vincula ao mapa.
     * parameters: { diagram_relationship_id, title, description, origem, base64 }
     */
    public function upload( $ip, $user, $post_data, $domain ) {
        $p = $post_data["parameters"];

        $mapa_id = isset($p["diagram_relationship_id"]) ? $p["diagram_relationship_id"] : "";
        $b64     = isset($p["base64"]) ? $p["base64"] : "";
        if( $mapa_id == "" || $b64 == "" ){
            throw new Exception("Informe diagram_relationship_id e base64.");
        }

        $bytes = base64_decode( $b64, true );
        if( $bytes === false ){
            throw new Exception("base64 inválido.");
        }
        if( strlen( $bytes ) == 0 || strlen( $bytes ) > self::MAX_BYTES ){
            throw new Exception("Tamanho inválido: " . strlen( $bytes ) . " bytes (limite " . self::MAX_BYTES . ").");
        }
        // Confere a assinatura em vez de confiar na extensao ou no que o cliente diz.
        if( substr( $bytes, 0, 5 ) !== "%PDF-" ){
            throw new Exception("O arquivo não é um PDF.");
        }

        $mysql = new Mysql( $domain );
        if( count( $mysql->DataTable("SELECT id FROM diagram_relationship WHERE id = ?", [ $mapa_id ]) ) == 0 ){
            throw new Exception("Mapa não encontrado.");
        }

        $sha256 = hash( "sha256", $bytes );

        $pasta = self::pasta();
        if( ! is_dir( $pasta ) ){
            if( ! mkdir( $pasta, 0755, true ) ){
                throw new Exception("Não foi possível criar data/documents.");
            }
        }

        $sqls = [];
        $values = [];

        $existe = $mysql->DataTable("SELECT id FROM document WHERE sha256 = ?", [ $sha256 ]);
        if( count( $existe ) > 0 ){
            // Mesmo conteudo ja cadastrado: nao regrava o arquivo nem duplica a linha.
            $document_id = $existe[0]["id"];
        } else {
            $document_id = $mysql->gen_uuid();
            if( file_put_contents( self::caminho( $sha256 ), $bytes ) === false ){
                throw new Exception("Não foi possível gravar o arquivo.");
            }
            array_push($sqls, "INSERT INTO document(id, sha256, person_id, title, description, bytes, origem) values(?,?,?,?,?,?,?)");
            array_push($values, [ $document_id, $sha256, ($user != null ? $user->id : null),
                                  isset($p["title"]) ? $p["title"] : "(sem título)",
                                  isset($p["description"]) ? $p["description"] : null,
                                  strlen( $bytes ),
                                  isset($p["origem"]) ? $p["origem"] : "upload" ]);
        }

        // ON DUPLICATE KEY: reanexar o mesmo PDF no mesmo mapa nao pode explodir na UNIQUE.
        array_push($sqls, "INSERT INTO document_map(id, document_id, diagram_relationship_id, person_id) values(?,?,?,?) ON DUPLICATE KEY UPDATE document_id = document_id");
        array_push($values, [ $mysql->gen_uuid(), $document_id, $mapa_id, ($user != null ? $user->id : null) ]);

        $mysql->ExecuteNoQuery( $sqls, $values );

        return array( "id" => $document_id, "sha256" => $sha256, "bytes" => strlen( $bytes ),
                      "ja_existia" => count( $existe ) > 0 );
    }

    /** parameters: { diagram_relationship_id } */
    public function list_by_map( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $sql = "SELECT d.id, d.sha256, d.title, d.description, d.bytes, d.origem, d.creation_time,
                       pe.username AS username,
                       ( SELECT COUNT(*) FROM document_map dm2 WHERE dm2.document_id = d.id ) AS mapas
                  FROM document_map AS dm
                  INNER JOIN document AS d ON d.id = dm.document_id
                  LEFT JOIN person AS pe ON pe.id = d.person_id
                 WHERE dm.diagram_relationship_id = ?
                 ORDER BY d.creation_time DESC";
        // 'mapas' mostra em quantos mapas o documento esta — e o que torna o
        // compartilhamento visivel para quem for desanexar.
        return $mysql->DataTable( $sql, [ $post_data["parameters"]["diagram_relationship_id"] ] );
    }

    /**
     * Devolve o PDF em base64. parameters: { document_id }
     *
     * Vai pelo execute.php de proposito: ele ja resolve a sessao em pessoa antes de
     * despachar. Um script de download proprio teria de repetir essa validacao — e um
     * caminho de auth paralelo e onde se erra. O custo e o base64 (+33%); um report tem
     * centenas de KB, longe do post_max_size de 256M do host.
     */
    public function download( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $doc = $mysql->DataTable("SELECT id, sha256, title, bytes FROM document WHERE id = ?",
                                 [ $post_data["parameters"]["document_id"] ]);
        if( count( $doc ) == 0 ){
            throw new Exception("Documento não encontrado.");
        }
        $caminho = self::caminho( $doc[0]["sha256"] );
        if( ! file_exists( $caminho ) ){
            throw new Exception("Arquivo ausente no servidor (sha256 " . $doc[0]["sha256"] . ").");
        }
        $bytes = file_get_contents( $caminho );
        // Confere o hash na leitura: se o arquivo em disco divergir do que o banco
        // registrou, e corrupcao ou troca — melhor falhar que entregar calado.
        if( hash( "sha256", $bytes ) !== $doc[0]["sha256"] ){
            throw new Exception("Arquivo corrompido: o sha256 não confere.");
        }
        return array( "title" => $doc[0]["title"], "bytes" => strlen( $bytes ),
                      "base64" => base64_encode( $bytes ) );
    }

    /** Anexa um documento que ja existe a outro mapa. parameters: { document_id, diagram_relationship_id } */
    public function link_map( $ip, $user, $post_data, $domain ) {
        $p = $post_data["parameters"];
        $mysql = new Mysql( $domain );
        if( count( $mysql->DataTable("SELECT id FROM document WHERE id = ?", [ $p["document_id"] ]) ) == 0 ){
            throw new Exception("Documento não encontrado.");
        }
        $sql = "INSERT INTO document_map(id, document_id, diagram_relationship_id, person_id) values(?,?,?,?) ON DUPLICATE KEY UPDATE document_id = document_id";
        return $mysql->ExecuteNoQuery( $sql, [ $mysql->gen_uuid(), $p["document_id"], $p["diagram_relationship_id"], ($user != null ? $user->id : null) ] );
    }

    /** Desanexa de um mapa. O arquivo so morre quando nenhum mapa aponta mais para ele. */
    public function unlink_map( $ip, $user, $post_data, $domain ) {
        $p = $post_data["parameters"];
        $mysql = new Mysql( $domain );

        $doc = $mysql->DataTable("SELECT sha256 FROM document WHERE id = ?", [ $p["document_id"] ]);
        if( count( $doc ) == 0 ){
            throw new Exception("Documento não encontrado.");
        }

        $mysql->ExecuteNoQuery("DELETE FROM document_map WHERE document_id = ? AND diagram_relationship_id = ?",
                               [ $p["document_id"], $p["diagram_relationship_id"] ]);

        $restantes = $mysql->DataTable("SELECT COUNT(*) AS n FROM document_map WHERE document_id = ?", [ $p["document_id"] ])[0]["n"];
        if( intval( $restantes ) > 0 ){
            return array( "removido" => false, "mapas_restantes" => intval( $restantes ) );
        }
        // Orfao: sai do banco e do disco. Apagar o arquivo antes de zerar as referencias
        // deixaria linha apontando para arquivo inexistente.
        $mysql->ExecuteNoQuery("DELETE FROM document WHERE id = ?", [ $p["document_id"] ]);
        $caminho = self::caminho( $doc[0]["sha256"] );
        if( file_exists( $caminho ) ){
            unlink( $caminho );
        }
        return array( "removido" => true, "mapas_restantes" => 0 );
    }
}

?>
