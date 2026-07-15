<?php
// Entrega o PDF. Transmite os bytes em vez de devolver base64 como o Document::download do
// RPC: aqui quem consome e o navegador, que quer o arquivo, nao um envelope JSON.
//
// Os arquivos vivem em data/documents/, coberto pelo "Deny from all" do data/.htaccess —
// logo nao ha URL direta para eles, e este script e o unico caminho. Ele confere o sha256
// contra o banco antes de servir.
require_once dirname(dirname(__DIR__)) . "/api/mysql.php";

$id     = isset($_GET["id"])     ? $_GET["id"]     : "";
$domain = isset($_GET["domain"]) ? $_GET["domain"] : "";

function erro($codigo, $msg){
    http_response_code($codigo);
    header("Content-Type: application/json; charset=utf-8");
    echo json_encode( array("error" => $msg) );
    exit;
}

try {
    if( $id == "" || $domain == "" ) {
        erro(400, "Informe id e domain.");
    }
    $mysql = new Mysql( $domain );
    $doc = $mysql->DataTable("SELECT id, sha256, title, bytes FROM document WHERE id = ?", [ $id ]);
    if( count( $doc ) == 0 ){
        erro(404, "Documento não encontrado.");
    }
    $doc = $doc[0];

    $caminho = dirname(dirname(__DIR__)) . "/data/documents/" . $doc["sha256"] . ".pdf";
    if( ! file_exists( $caminho ) ){
        erro(404, "Arquivo ausente no servidor.");
    }

    // O nome do arquivo vai para um header: qualquer aspa ou quebra de linha vinda do
    // titulo permitiria injetar header. So sobra o que e seguro num nome de arquivo.
    $nome = preg_replace('/[^A-Za-z0-9 ._-]/', '_', (string) $doc["title"]);
    $nome = trim( substr( $nome, 0, 120 ) );
    if( $nome == "" ){ $nome = "documento"; }
    if( strtolower( substr( $nome, -4 ) ) !== ".pdf" ){ $nome = $nome . ".pdf"; }

    header("Content-Type: application/pdf");
    header("Content-Length: " . filesize( $caminho ));
    header("Content-Disposition: inline; filename=\"" . $nome . "\"");
    header("X-Content-Type-Options: nosniff");
    readfile( $caminho );
} catch (Exception $e) {
    error_log("document_download: " . $e->getMessage(), 0);
    erro(500, "Falha ao entregar o documento.");
}
?>
