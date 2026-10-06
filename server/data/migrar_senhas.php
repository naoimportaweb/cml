<?php
// Converte a coluna `person.password` do formato antigo (o valor que o cliente envia, guardado
// cru) para password_hash(). Ver o bloco de migracao no fim de create.sql.
//
// A conversao e calculavel a partir da PROPRIA coluna: como o guardado era exatamente o que o
// cliente manda, basta reescrever cada linha com o bcrypt dela mesma. Ninguem precisa saber,
// trocar ou redefinir senha, e nenhum cliente precisa ser atualizado.
//
//     php server/data/migrar_senhas.php <domain>
//
// Roda quantas vezes quiser: linha ja em bcrypt e pulada.

require_once __DIR__ . "/../api/mysql.php";

$domain = isset($argv[1]) ? $argv[1] : null;
if ($domain === null) {
    fwrite(STDERR, "uso: php migrar_senhas.php <domain>\n");
    exit(1);
}

$mysql = new Mysql($domain);
$pessoas = $mysql->DataTable("SELECT id, username, password FROM person", []);

$migradas = 0; $puladas = 0; $vazias = 0;
foreach ($pessoas as $pessoa) {
    $guardado = (string)$pessoa["password"];
    if ($guardado === "") {
        $vazias++;                       // conta sem senha definida: nada a converter
        continue;
    }
    if (password_get_info($guardado)["algo"]) {
        $puladas++;                      // ja esta em bcrypt
        continue;
    }
    $mysql->ExecuteNoQuery(
        ["UPDATE person SET password=? WHERE id=?"],
        [[ password_hash($guardado, PASSWORD_DEFAULT), $pessoa["id"] ]]);
    $migradas++;
    echo "migrada: " . $pessoa["username"] . "\n";
}

echo "\n";
echo "migradas: $migradas | ja estavam: $puladas | sem senha: $vazias\n";
echo $migradas > 0
    ? "Pronto. O valor antigo da coluna nao vale mais como credencial.\n"
    : "Nada a fazer.\n";
