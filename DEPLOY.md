# DEPLOY.md

Procedimento de publicação do CML numa hospedagem compartilhada (Hostinger, LiteSpeed).

> **Cuidado com a versão do PHP: o CLI e o servidor web são diferentes.** No host atual o
> `php` da linha de comando é **7.4**, mas quem atende as requisições é o **PHP 8.5 via
> LiteSpeed**. Testar com `php -r` no SSH exercita um runtime que não é o de produção. Para
> saber a versão real, publique um arquivo com `phpversion() . php_sapi_name()` e acesse por
> HTTP — foi assim que a diferença apareceu.

> **Este arquivo é versionado e o repositório é público.** Nenhum valor concreto mora aqui:
> nem senha, nem host, nem caminho de servidor, nem o nome do arquivo de flag. Tudo vem do
> `~/.env` (fora do repositório, permissão `600`). Ao editar este documento, mantenha a
> regra — referencie a variável, nunca o valor.

## Variáveis usadas (definidas em `~/.env`)

| Variável | Para que serve |
|---|---|
| `SSH_HOSTINGER_IP` | Host do servidor |
| `SSH_HOSTINGER_PORT` | Porta SSH (não é a 22) |
| `SSH_HOSTINGER_USER` | Usuário da conta de hospedagem |
| `SSH_HOSTINGER_PASSWORD` | Senha SSH — hoje é o único método que funciona (ver "Autenticação") |
| `<PROJETO>_DEPLOY_DIR` | Diretório do projeto no servidor (a raiz, um nível acima do `cml/`) |
| `<PROJETO>_DEPLOY_FLAG` | Nome do arquivo de flag que autoriza o deploy (ver abaixo) |
| `<PROJETO>_DB_HOST` | Host do MySQL para o servidor (o PHP roda na mesma máquina) |
| `<PROJETO>_DB_HOST_REMOTO` | Host do MySQL para admin/dev de fora — **não** vai no `config.json` |
| `<PROJETO>_DB_DATABASE` / `_USER` / `_PASSWORD` | Conexão do domain, para o `data/config.json` **do servidor** |

`CML_PROJECTS` lista os projetos; `<PROJETO>` é cada nome de lá (ex.: `CYBERWARFARE`).

Helper para carregar só o necessário, sem dar `source` no `~/.env` inteiro (o arquivo tem
valores não-quotados com `;` e `&`, que o shell executaria):

```bash
env_get() { grep -m1 "^$1=" ~/.env | cut -d= -f2-; }
H=$(env_get SSH_HOSTINGER_IP);   O=$(env_get SSH_HOSTINGER_PORT)
U=$(env_get SSH_HOSTINGER_USER); P=$(env_get SSH_HOSTINGER_PASSWORD)
D=$(env_get CYBERWARFARE_DEPLOY_DIR)
FLAG=$(env_get CYBERWARFARE_DEPLOY_FLAG)
SSH_OPTS="-o PreferredAuthentications=password -o PubkeyAuthentication=no -p $O"
```

## Flag obrigatória — o portão do deploy

Todo diretório de projeto no servidor tem, na **raiz**, um arquivo de flag, cujo nome está
em `<PROJETO>_DEPLOY_FLAG`. Regras, sem exceção:

- **O deploy só pode acontecer se a flag for encontrada na raiz do destino.** Se não estiver
  lá, o destino está errado (ou não foi preparado) — **aborte**. Não crie o diretório, não
  crie a flag, não prossiga "só para testar".
- **A flag não pode ser editada**, renomeada ou apagada. Não faz parte do repositório e nunca
  entra no tarball do deploy.

O motivo é a máquina: é hospedagem compartilhada, com muitos domínios sob a mesma conta, e o
`rsync` do Passo 3 escreve recursivamente. A flag é a prova de que o caminho aponta para o
projeto certo antes de qualquer escrita. Ela fica na raiz (`$<PROJETO>_DEPLOY_DIR`), um nível
**acima** do `cml/` onde o rsync escreve — por isso este procedimento nunca a toca. Um
`rsync --delete` apontado direto à raiz do projeto apagaria a flag: não faça.

## Autenticação

Existe um alias no `~/.ssh/config` apontando para o mesmo host/porta/usuário, com chave
própria. **Essa chave está sendo rejeitada pelo servidor** (`Permission denied
(publickey,password)`): ela existe localmente, mas a pública não está no `authorized_keys`
de lá. Enquanto não for corrigido, o acesso é por senha:

```bash
sshpass -p "$P" ssh $SSH_OPTS "$U@$H"
```

Correção recomendada (dispensa `SSH_HOSTINGER_PASSWORD` no deploy):

```bash
sshpass -p "$P" ssh-copy-id -i ~/.ssh/<a-chave>.pub -p "$O" "$U@$H"
```

## O caminho `/cml` é obrigatório — e como ele casa com o `DEPLOY_DIR`

O cliente monta a URL no código (`app/classlib/connectobject.py`):

```python
url = self.ip + "/cml/services/execute.php";           # __execute__
url = self.ip + "/cml/services/federation_proxy.php";  # __proxy__
```

`self.ip` é a **URL base** que o usuário digita no diálogo de Connect (apesar do nome, não é
um IP). O segmento `/cml/` é fixo, então o diretório no servidor **tem** que se chamar `cml`.
O `federation_proxy.php` também monta `"/cml/services/federation.php"` ao chamar outros
servidores — são 3 pontos fixos no total.

O `<PROJETO>_DEPLOY_DIR` aponta para a raiz do projeto, não para o `cml/`. As duas coisas só
funcionam juntas de uma maneira — o `cml` vai **dentro** do diretório do projeto:

```
$DEPLOY_DIR/cml/services/execute.php
            └── é este "cml" que o cliente exige
```

e o usuário digita a URL base **com o projeto no caminho**:

```
https://<site>/<projeto>          ->  cliente completa com /cml/services/execute.php
```

> **Use `https://` explícito.** Se o host redireciona `http` → `https` (301), o `requests`
> converte o POST em GET e o corpo do envelope se perde; o PHP recebe `php://input` vazio e
> responde um erro de banco sem relação com a causa. O cliente hoje detecta o redirect e
> avisa (`allow_redirects=False`), mas a URL certa evita o problema na origem.

> **Não faça** rsync do conteúdo direto para `$DEPLOY_DIR/` (sem o `cml/` dentro): o
> `execute.php` cairia em `$DEPLOY_DIR/services/execute.php` e nenhum cliente acharia, porque
> não existe URL base capaz de produzir esse caminho.

## Passo 1 — empacotar localmente

```bash
cd script && ./deploy.sh     # precisa rodar de dentro de script/ (usa caminhos ../)
```

Produz `/tmp/server/cml/` com:

- o conteúdo de `server/`;
- `webpage/downloads/client.tar.gz`, o tarball do cliente gerado de `../app` (é o que o
  `app/install.sh` baixa na máquina do usuário final);
- **sem** `data/config.json` nem `data/create.sql` — o script apaga;
- **sem** o `.htaccess` da raiz — o script apaga (ele liga `display_errors`; removê-lo é
  proposital, não deve ir para produção).

> O `rm -r /tmp/server/cml/data/*` do `deploy.sh` usa glob `*`, que não casa com ocultos.
> Então o `data/.htaccess` (`Deny from all`) sobrevive e viaja — que é o desejado.

## Passo 2 — verificar a flag (obrigatório, aborta o deploy)

```bash
if sshpass -p "$P" ssh $SSH_OPTS "$U@$H" "test -f '${D%/}/$FLAG'"; then
    echo "flag OK — destino confirmado: ${D%/}"
else
    echo "ABORTADO: flag ausente em ${D%/} — destino errado ou não preparado" >&2
    exit 1
fi
```

Rode **antes** do Passo 3, sempre. Se abortar, pare e confira o `<PROJETO>_DEPLOY_DIR`; não
crie a flag para "destravar" — ela é a verificação, não uma formalidade.

## Passo 3 — enviar

```bash
sshpass -p "$P" rsync -az --exclude 'data/' -e "ssh $SSH_OPTS" \
  /tmp/server/cml/ "$U@$H:${D%/}/cml/"
```

**Nunca use `--delete` sem `--exclude 'data/'`.** O `deploy.sh` esvazia o `data/` local; um
`--delete` espelharia esse vazio e apagaria o `config.json` e os certificados de produção,
derrubando a instalação.

> **Na primeira instalação o `--exclude 'data/'` trabalha contra você**: como não existe
> `data/` no servidor ainda, nada o cria, e nem o `data/.htaccess` chega. O resultado é um
> `cml/` sem `data/` — o servidor lança exceção em toda requisição, porque o
> `Json::FromFile_v2` não acha o `config.json`. Faça o Passo 4 em seguida, **antes** de
> apontar qualquer cliente para lá.

## Passo 4 — `data/` (só na primeira instalação)

O `data/` nunca é enviado pelo deploy: existe só no servidor e é a fronteira entre o código
(versionado) e os segredos (não versionados). Numa instalação nova, criar lá:

**`data/.htaccess`** — `Order Allow,Deny` / `Deny from all`. Já existe no repositório em
`server/data/.htaccess`; suba com `scp`. É o que impede o `config.json` de ser servido por
HTTP. **Verifique que funciona**, não confie na presença do arquivo — o LiteSpeed precisa
aceitar a sintaxe Apache 2.2:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://<site>/<projeto>/cml/data/config.json  # 403
curl -s -o /dev/null -w '%{http_code}\n' https://<site>/<projeto>/cml/services/execute.php  # 200
```

O segundo é o controle: sem ele, um 403 poderia ser apenas caminho inexistente.

**`data/certs/`** — diretório gravável onde o `services/classlib/session.php` grava o par RSA
(`cml.pem`) na primeira requisição. O `config.json` de exemplo aponta para `/var/certs/`, que
**não é gravável em conta compartilhada**. Colocá-lo dentro do `data/` faz o `Deny from all`
proteger a chave privada de brinde.

**`data/config.json`** — montado direto no servidor a partir das `<PROJETO>_DB_*`, com
`chmod 600`. Formato:

```json
{
    "version": "1",
    "domains": ["<domain>"],
    "default": "<domain>",
    "connections": {
        "<domain>": {
            "host": "127.0.0.1",
            "user": "<PROJETO>_DB_USER",
            "password": "<PROJETO>_DB_PASSWORD",
            "name": "<PROJETO>_DB_DATABASE",
            "port": 3306,
            "restricted": true,
            "federation": []
        }
    },
    "federation": {},
    "crypto": {"path": "<DEPLOY_DIR>/cml/data/certs/"}
}
```

Notas que custaram caro:

- **`host`: use o local (`127.0.0.1`), nunca o `_HOST_REMOTO`.** O remoto serve para
  administrar o banco a partir da sua máquina; o PHP roda junto do MySQL.
- **`domains` deve listar só o domain deste projeto.** O `Mysql::domains()` devolve tudo que
  estiver ali, o `Domain::list()` entrega a lista ao cliente, e o `execute.php` faz
  `new Mysql($domain)` com o que o cliente mandar. Copiar o `config.json` de outra instalação
  transforma este endpoint numa porta de entrada para os bancos dela.
- **`crypto.path` não pode ser compartilhado** com outra instalação, senão as duas passam a
  usar a mesma chave privada.

**Schema** — aplicar `server/data/create.sql` no banco do domain. Se for cópia de um banco
existente, o `mysqldump` já traz os `CREATE TABLE` e dispensa o `create.sql`:

```bash
mysqldump --defaults-extra-file=<cnf-origem> --single-transaction --no-tablespaces \
  --routines --triggers --events <db-origem> | mysql --defaults-extra-file=<cnf-destino> <db-destino>
```

O `--single-transaction` tira snapshot consistente **sem travar tabela**, então a origem
segue atendendo. O `--no-tablespaces` evita o erro de privilégio `PROCESS`, comum em
hospedagem compartilhada. Passe as senhas por `--defaults-extra-file` com `umask 077`, nunca
em `argv` — numa máquina compartilhada o `ps` de outros usuários enxerga a linha de comando.
Apague os `.cnf` ao terminar.

## Diagnóstico rápido

| Sintoma | Causa provável |
|---|---|
| `Access denied for user ''@'localhost'` | `config.json` ausente/ilegível, ou `domain` que não existe em `connections` |
| `Table '<db>.person' doesn't exist` | conexão OK, credenciais OK — falta o schema |
| `Domain inválido: '<x>'` | o domain pedido não está no `connections` do `config.json` |
| Cliente reclama de redirect | `http://` num host que só fala `https` |

O `Session.publickey` é o teste mais barato de ponta a ponta: toca banco (lê `person`) e
exercita o `crypto.path` (gera o `cml.pem`).

## Lacunas / a confirmar

- O `~/.env` descreve um esquema multi-projeto (`CML_PROJECTS`, `<PROJETO>_DB_*`,
  `<PROJETO>_DEPLOY_DIR`), mas **o repositório não lê `.env` em lugar nenhum** — o servidor
  só lê `data/config.json`. A ponte entre os dois é manual.
- A chave SSH do `~/.ssh/config` precisa ser reautorizada no servidor para dispensar a senha.
- Existem outras instalações CML na mesma conta, anteriores a este procedimento. A relação
  entre elas (ambientes distintos, projetos distintos ou legado) não está definida.
