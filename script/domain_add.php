<?php
/*
 * Inclui um domain (tenant) no data/config.json de uma instalação já implantada.
 *
 * Roda NO SERVIDOR, com o php de linha de comando (7.4 serve — não toca runtime web):
 *
 *   printf '%s\n' "$SENHA_DO_BANCO" | php domain_add.php <config.json> <domain> <banco> <usuario> [restricted=1] [host=127.0.0.1]
 *
 * A senha do banco vem pela PRIMEIRA linha do stdin, nunca por argumento: numa máquina
 * compartilhada o `ps` de outro usuário enxerga a linha de comando (ver DEPLOY.md).
 *
 * O que ele garante:
 *   - não repete domain (aborta se já existir em `domains` ou `connections`);
 *   - não altera `default`, `federation` nem `crypto` — só acrescenta;
 *   - guarda um backup `config.json.bak-<data>` antes de escrever;
 *   - grava por arquivo temporário + rename (atômico) e com permissão 0600.
 *
 * A porta é sempre 3306 e `federation` nasce vazia — o mesmo formato do DEPLOY.md (Passo 4).
 * O banco precisa existir e já ter o schema; isto aqui só ensina o endpoint a enxergá-lo.
 */

function falhar($msg){ fwrite(STDERR, "domain_add: " . $msg . "\n"); exit(1); }

if( $argc < 5 ){
    falhar("uso: printf '%s\\n' \"\$SENHA\" | php domain_add.php <config.json> <domain> <banco> <usuario> [restricted=1] [host=127.0.0.1]");
}
$caminho    = $argv[1];
$domain     = $argv[2];
$banco      = $argv[3];
$usuario    = $argv[4];
$restricted = isset($argv[5]) ? (bool) intval($argv[5]) : true;
$host       = isset($argv[6]) ? $argv[6] : "127.0.0.1";

if( !preg_match('/^[a-z0-9_]+$/', $domain) ){
    falhar("nome de domain inválido '" . $domain . "': só minúsculas, dígitos e _ (vai em URL e em nome de arquivo).");
}

$senha = fgets(STDIN);
if( $senha === false ){ falhar("senha do banco não veio pelo stdin."); }
$senha = rtrim($senha, "\r\n");
if( $senha === "" ){ falhar("senha do banco vazia."); }

if( !is_readable($caminho) ){ falhar("não consigo ler " . $caminho); }
$bruto = file_get_contents($caminho);
// Decodifica como objeto (não como array assoc.): um `federation: {}` vazio precisa continuar
// `{}` ao regravar — como array vazio o json_encode escreveria `[]`.
$json  = json_decode($bruto, false);
if( !is_object($json) || !isset($json->domains) || !isset($json->connections) ){
    falhar("config.json sem 'domains'/'connections' — não parece o arquivo certo, nada foi alterado.");
}
if( in_array($domain, $json->domains, true) || isset($json->connections->{$domain}) ){
    falhar("o domain '" . $domain . "' já existe no config.json — nada foi alterado.");
}

$json->domains[] = $domain;
$json->connections->{$domain} = (object) array(
    "host"       => $host,
    "user"       => $usuario,
    "password"   => $senha,
    "name"       => $banco,
    "port"       => 3306,
    "restricted" => $restricted,
    "federation" => array(),
);

$novo = json_encode($json, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
if( $novo === false ){ falhar("falha ao serializar o JSON: " . json_last_error_msg()); }

$backup = $caminho . ".bak-" . date("Ymd-His");
if( !copy($caminho, $backup) ){ falhar("não consegui gravar o backup " . $backup . " — nada foi alterado."); }
chmod($backup, 0600);

$tmp = $caminho . ".tmp-" . getmypid();
umask(0077);
if( file_put_contents($tmp, $novo . "\n") === false ){ falhar("não consegui escrever " . $tmp); }
chmod($tmp, 0600);
if( !rename($tmp, $caminho) ){ @unlink($tmp); falhar("rename falhou; o original está intacto e o backup em " . $backup); }

// Confere lendo de volta pelo mesmo caminho que o Mysql::domains() usa.
$conferido = json_decode(file_get_contents($caminho), true);
if( !is_array($conferido) || !in_array($domain, $conferido["domains"], true) ){ falhar("gravei mas não reli o domain — restaure do backup " . $backup); }

echo "domain '" . $domain . "' incluído: banco=" . $banco . " user=" . $usuario . " host=" . $host
   . " restricted=" . ($restricted ? "true" : "false") . "\n"
   . "domains agora: " . implode(", ", $conferido["domains"]) . " (default continua '" . $conferido["default"] . "')\n"
   . "backup: " . $backup . "\n";
