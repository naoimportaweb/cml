#!/usr/bin/env python3
"""Servidor MCP — acesso ao servidor da Hostinger onde vive o CML.

Não é um shell cru exposto por JSON-RPC: as regras do DEPLOY.md estão embutidas, e são elas
que justificam a existência deste arquivo. O que se ganha, em ordem de quanto já custou:

- `php` usa o binário 8.5 (/opt/alt/php85), não o `php` do PATH — que no SSH é 7.4. Lintar
  ou testar com o do PATH exercita um runtime que NÃO é o de produção;
- `flag_confirmar` é a regra que vem antes de qualquer envio: sem a flag na raiz, o destino
  está errado e publicar é proibido (a conta é compartilhada, o rsync escreve recursivo);
- `deploy` já vai com --exclude data/ e SEM --delete: o data/ do servidor guarda config.json
  e certificados que o pacote local não tem, e espelhar o vazio derruba a instalação;
- `log_ref` fecha o ciclo do erro de banco: a mensagem que chega ao usuário traz só o código
  e uma ref., e o SQL correspondente fica no error_log do servidor com a mesma ref.;
- `ler_arquivo` recusa .env, chaves, certificado e o data/config.json (que tem a senha do
  MySQL em claro); `env_chaves` devolve só os NOMES das variáveis.

Credenciais vêm do ~/.env da estação, nunca do .mcp.json (que é versionado). A senha não
passa por argv: vai por SSHPASS no ambiente, ou por SSH_ASKPASS quando não há sshpass na
máquina — este mesmo arquivo responde à pergunta do ssh quando chamado com --askpass.

O esquema do ~/.env é multi-projeto (CML_PROJECTS, <PROJETO>_DEPLOY_DIR, <PROJETO>_DB_*),
então toda ferramenta aceita `projeto`; sem ele, vale o primeiro de CML_PROJECTS.

Transporte: stdio, JSON-RPC 2.0. Só stdlib.
"""

import contextlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

ENV_ESTACAO = os.path.expanduser("~/.env")
RAIZ_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMITE_SAIDA = 60_000          # bytes devolvidos por chamada
TIMEOUT_PADRAO = 60
TIMEOUT_MAXIMO = 300

# Caminhos que este servidor nunca lê: o conteúdo é segredo. O data/config.json entra na
# lista porque guarda usuário e senha do MySQL de produção em claro.
NEGADOS_LEITURA = re.compile(
    r"(^|/)\.env(\.|$)|\.(pem|key|p12|pfx)$|(^|/)id_(rsa|ed25519|ecdsa)(\.|$)"
    r"|(^|/)data/config\.json$|(^|/)cml\.pem$",
    re.IGNORECASE,
)

# Comandos obviamente destrutivos. Não é sandbox — é rede de proteção contra engano, não
# contra intenção.
NEGADOS_COMANDO = [
    re.compile(r"\brm\s+(-[a-zA-Z]*\s+)*-?[a-zA-Z]*[rf][a-zA-Z]*\s+(/|~|\$HOME)\s*$"),
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bdd\s+if="),
    re.compile(r":\(\)\s*\{.*\};\s*:"),
    re.compile(r"\bchmod\s+-R\s+777\s+(/|~)"),
    re.compile(r"(>|>>)\s*~?/?\.env\b"),
    re.compile(r"\brm\b[^|;&]*\.env\b"),
    re.compile(r"\bcrontab\s+-r\b"),
    # o data/ do servidor é a fronteira entre código e segredo: não se apaga por aqui
    re.compile(r"\brm\b[^|;&]*/cml/data\b"),
    re.compile(r"\brsync\b[^|;&]*--delete"),
]

# SQL que muda o mundo de forma difícil de desfazer. Vale mesmo com escrita=true: para isso
# existe o terminal, conscientemente.
NEGADOS_SQL = [
    (re.compile(r"\bdrop\s+(database|schema|table|user)\b", re.I), "DROP de banco/tabela/usuário"),
    (re.compile(r"\btruncate\b", re.I), "TRUNCATE"),
    (re.compile(r"\b(grant|revoke)\b", re.I), "GRANT/REVOKE"),
    (re.compile(r"\bcreate\s+user\b", re.I), "CREATE USER"),
    (re.compile(r"\bset\s+password\b", re.I), "SET PASSWORD"),
    (re.compile(r"\bdelete\s+from\b(?!.*\bwhere\b)", re.I | re.S), "DELETE sem WHERE"),
    (re.compile(r"\bupdate\b(?!.*\bwhere\b)", re.I | re.S), "UPDATE sem WHERE"),
]
SO_LEITURA = re.compile(r"^\s*(select|show|describe|desc|explain|with)\b", re.I)


# --------------------------------------------------------------------------
# ~/.env da estação
# --------------------------------------------------------------------------
def env_local(chave: str) -> str:
    """Lê UMA variável do ~/.env sem dar source no arquivo — ele tem valores não-quotados
    com ';' e '&', que o shell executaria."""
    try:
        with open(ENV_ESTACAO, "r", encoding="utf-8", errors="replace") as f:
            for linha in f:
                if linha.startswith(chave + "="):
                    return linha.split("=", 1)[1].strip()
    except FileNotFoundError:
        raise RuntimeError(f"{ENV_ESTACAO} não encontrado na estação")
    return ""


def projetos() -> list:
    bruto = env_local("CML_PROJECTS")
    return [p.strip() for p in re.split(r"[,\s]+", bruto) if p.strip()]


def projeto_padrao(args: dict) -> str:
    escolhido = (args or {}).get("projeto") or ""
    escolhido = escolhido.strip().upper()
    disponiveis = projetos()
    if escolhido:
        if disponiveis and escolhido not in disponiveis:
            raise RuntimeError(f"projeto '{escolhido}' não está em CML_PROJECTS ({', '.join(disponiveis)})")
        return escolhido
    if not disponiveis:
        raise RuntimeError("CML_PROJECTS vazio no ~/.env — informe 'projeto' na chamada")
    return disponiveis[0]


def var_projeto(projeto: str, sufixo: str) -> str:
    valor = env_local(f"{projeto}_{sufixo}")
    if not valor:
        raise RuntimeError(f"{projeto}_{sufixo} ausente no ~/.env")
    return valor


def conexao() -> dict:
    dados = {
        "ip": env_local("SSH_HOSTINGER_IP"),
        "porta": env_local("SSH_HOSTINGER_PORT") or "22",
        "usuario": env_local("SSH_HOSTINGER_USER"),
        "senha": env_local("SSH_HOSTINGER_PASSWORD"),
    }
    faltando = [k for k in ("ip", "usuario", "senha") if not dados[k]]
    if faltando:
        raise RuntimeError("faltam no ~/.env: " + ", ".join("SSH_HOSTINGER_" + k.upper() for k in faltando))
    return dados


def raiz_deploy(projeto: str) -> str:
    return var_projeto(projeto, "DEPLOY_DIR").rstrip("/")


def flag_nome(projeto: str) -> str:
    return var_projeto(projeto, "DEPLOY_FLAG")


# --------------------------------------------------------------------------
# SSH — sshpass quando existe, SSH_ASKPASS quando não
# --------------------------------------------------------------------------
@contextlib.contextmanager
def askpass_temporario():
    """Wrapper 0700 que devolve a senha ao ssh. O arquivo NÃO contém a senha: ele chama este
    mesmo script com --askpass, que a lê do ~/.env na hora."""
    fd, caminho = tempfile.mkstemp(prefix="cml-askpass-", suffix=".sh")
    try:
        with os.fdopen(fd, "w") as f:
            f.write("#!/bin/sh\nexec %s %s --askpass\n" % (
                shlex.quote(sys.executable), shlex.quote(os.path.abspath(__file__))))
        os.chmod(caminho, 0o700)
        yield caminho
    finally:
        try:
            os.unlink(caminho)
        except OSError:
            pass


def _truncar(saida: str, retorno: int) -> str:
    if len(saida) > LIMITE_SAIDA:
        saida = saida[:LIMITE_SAIDA] + f"\n[... truncado em {LIMITE_SAIDA} bytes]"
    if retorno != 0 and not saida.strip():
        saida = f"[sem saída; código de retorno {retorno}]"
    return saida


def _rodar(argv, ambiente, timeout, entrada):
    # stdin=DEVNULL quando nao ha entrada: sem isto o processo filho herda o stdin DESTE
    # servidor, que e o pipe do JSON-RPC — o ssh leria as mensagens do protocolo e o cliente
    # MCP travaria esperando resposta de uma requisicao que sumiu.
    try:
        if entrada is None:
            p = subprocess.run(argv, capture_output=True, text=True, env=ambiente,
                               stdin=subprocess.DEVNULL,
                               timeout=min(max(int(timeout), 5), TIMEOUT_MAXIMO))
        else:
            p = subprocess.run(argv, capture_output=True, text=True, env=ambiente,
                               input=entrada, timeout=min(max(int(timeout), 5), TIMEOUT_MAXIMO))
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"tempo esgotado ({timeout}s) no servidor")
    return _truncar((p.stdout or "") + (p.stderr or ""), p.returncode)


def _opcoes_ssh(porta: str) -> list:
    return [
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=25",
        # a conta recusa chave (DEPLOY.md, "Autenticação"); forçar senha evita cair em
        # publickey e receber "Permission denied" sem explicação
        "-o", "PubkeyAuthentication=no",
        "-o", "PreferredAuthentications=password",
        "-o", "BatchMode=no",
        "-p", porta,
    ]


def ssh(comando: str, timeout: int = TIMEOUT_PADRAO, entrada: str = None) -> str:
    """Executa um comando no servidor e devolve a saída combinada, truncada."""
    c = conexao()
    destino = f"{c['usuario']}@{c['ip']}"
    opcoes = _opcoes_ssh(c["porta"])
    if shutil.which("sshpass"):
        return _rodar(["sshpass", "-e", "ssh"] + opcoes + [destino, comando],
                      dict(os.environ, SSHPASS=c["senha"]), timeout, entrada)
    with askpass_temporario() as helper:
        ambiente = dict(os.environ, SSH_ASKPASS=helper, SSH_ASKPASS_REQUIRE="force",
                        DISPLAY=os.environ.get("DISPLAY", ":0"))
        return _rodar(["setsid", "-w", "ssh"] + opcoes + [destino, comando],
                      ambiente, timeout, entrada)


def rsync(origem: str, destino_remoto: str, timeout: int = TIMEOUT_MAXIMO) -> str:
    c = conexao()
    opcoes = " ".join(shlex.quote(o) for o in _opcoes_ssh(c["porta"]))
    alvo = f"{c['usuario']}@{c['ip']}:{destino_remoto}"
    # sem --delete e com --exclude data/: ver o cabeçalho deste arquivo e o DEPLOY.md
    base = ["rsync", "-az", "--exclude", "data/", "-e", f"ssh {opcoes}", origem, alvo]
    if shutil.which("sshpass"):
        return _rodar(["sshpass", "-e"] + base, dict(os.environ, SSHPASS=c["senha"]), timeout, None)
    with askpass_temporario() as helper:
        ambiente = dict(os.environ, SSH_ASKPASS=helper, SSH_ASKPASS_REQUIRE="force",
                        DISPLAY=os.environ.get("DISPLAY", ":0"))
        return _rodar(["setsid", "-w"] + base, ambiente, timeout, None)


# --------------------------------------------------------------------------
# Ferramentas
# --------------------------------------------------------------------------
def t_projetos(_args: dict) -> str:
    lista = projetos()
    if not lista:
        return "CML_PROJECTS vazio no ~/.env."
    linhas = ["projetos em CML_PROJECTS: " + ", ".join(lista), ""]
    for p in lista:
        try:
            linhas.append(f"{p}: raiz={raiz_deploy(p)}  flag={'(definida)' if flag_nome(p) else '(AUSENTE)'}")
        except RuntimeError as e:
            linhas.append(f"{p}: {e}")
    return "\n".join(linhas)


def t_flag_confirmar(args: dict) -> str:
    """A regra que vem antes de todas: sem a flag, o diretório não é a raiz do projeto."""
    projeto = projeto_padrao(args)
    raiz, flag = raiz_deploy(projeto), flag_nome(projeto)
    saida = ssh(f"test -f {shlex.quote(raiz + '/' + flag)} && echo ACHOU || echo NAO_ACHOU")
    if "ACHOU" in saida and "NAO_ACHOU" not in saida:
        return f"flag OK — destino confirmado para {projeto}: {raiz}"
    raise RuntimeError(
        f"flag ausente em {raiz} — destino errado ou não preparado para {projeto}. "
        "NÃO publique e NÃO crie a flag para destravar: ela é a verificação."
    )


def t_listar(args: dict) -> str:
    projeto = projeto_padrao(args)
    caminho = args.get("caminho") or raiz_deploy(projeto)
    profundidade = min(int(args.get("profundidade", 1)), 5)
    if profundidade <= 1:
        return ssh(f"ls -la {shlex.quote(caminho)}")
    return ssh(f"find {shlex.quote(caminho)} -maxdepth {profundidade} | head -400")


def t_ler_arquivo(args: dict) -> str:
    caminho = args.get("caminho", "")
    if not caminho:
        raise RuntimeError("caminho é obrigatório")
    if NEGADOS_LEITURA.search(caminho):
        raise RuntimeError(
            "recusado: este arquivo guarda segredo (senha do banco, chave ou certificado). "
            "Para variáveis de ambiente use env_chaves, que devolve só os nomes."
        )
    linhas = min(int(args.get("linhas", 400)), 2000)
    return ssh(f"head -n {linhas} {shlex.quote(caminho)}")


def t_env_chaves(_args: dict) -> str:
    """Nomes das variáveis do ~/.env do SERVIDOR. Nunca os valores."""
    return ssh("grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' ~/.env | sed 's/=$//' | sort")


def t_php(args: dict) -> str:
    """O `php` do PATH é 7.4; produção é 8.5 via LiteSpeed (DEPLOY.md)."""
    versao = str(args.get("versao", "85")).replace(".", "")
    argumentos = args.get("argumentos", "-v")
    cwd = args.get("cwd", "")
    binario = f"/opt/alt/php{versao}/usr/bin/php"
    prefixo = f"cd {shlex.quote(cwd)} && " if cwd else ""
    return ssh(f"{prefixo}{binario} {argumentos}", timeout=int(args.get("timeout", 120)))


def t_php_versoes(args: dict) -> str:
    return ssh(
        "echo '== binarios alt-php:'; ls -d /opt/alt/php* 2>/dev/null | sed 's#.*/##' | tr '\\n' ' '; echo; "
        "echo '== php do PATH:'; php -v 2>&1 | head -1"
    )


def t_lint(args: dict) -> str:
    """php -l com o binário de PRODUÇÃO em todo .php publicado (ou no caminho indicado)."""
    projeto = projeto_padrao(args)
    alvo = args.get("caminho") or (raiz_deploy(projeto) + "/cml")
    versao = str(args.get("versao", "85")).replace(".", "")
    binario = f"/opt/alt/php{versao}/usr/bin/php"
    return ssh(
        f"find {shlex.quote(alvo)} -name '*.php' -type f | sort | while read -r f; do "
        f"  saida=$({binario} -l \"$f\" 2>&1 | tail -1); "
        f"  case \"$saida\" in *'No syntax errors'*) ;; *) echo \"FALHOU: $f -> $saida\";; esac; "
        f"done; echo '--- fim (só falhas são listadas) ---'",
        timeout=int(args.get("timeout", 180)))


def t_deploy(args: dict) -> str:
    """Empacota (script/deploy.sh), confere a flag e envia. As travas do DEPLOY.md ficam aqui
    dentro, para não dependerem de alguém lembrar delas na hora."""
    if not args.get("confirmar"):
        raise RuntimeError("passe confirmar=true: isto publica em produção")
    projeto = projeto_padrao(args)
    passos = []

    empacotar = subprocess.run(["./deploy.sh"], cwd=os.path.join(RAIZ_REPO, "script"),
                               capture_output=True, text=True, timeout=300)
    if empacotar.returncode != 0:
        raise RuntimeError("deploy.sh falhou:\n" + _truncar((empacotar.stdout or "") + (empacotar.stderr or ""), 1))
    if not os.path.isfile("/tmp/server/cml/services/execute.php"):
        raise RuntimeError("pacote incompleto: /tmp/server/cml/services/execute.php não existe")
    passos.append("1) empacotado em /tmp/server/cml/")

    passos.append("2) " + t_flag_confirmar({"projeto": projeto}))

    saida = rsync("/tmp/server/cml/", raiz_deploy(projeto) + "/cml/")
    enviados = [l for l in saida.splitlines() if l.strip()]
    passos.append("3) enviado (--exclude data/, sem --delete): " + (enviados[-1] if enviados else "sem resumo"))
    return "\n".join(passos)


def t_sql(args: dict) -> str:
    """Consulta o MySQL do projeto pelo servidor (o PHP roda junto do banco; o host é o local).
    Leitura por padrão — escrita exige escrita=true e ainda assim recusa o irreversível."""
    consulta = (args.get("sql") or "").strip()
    if not consulta:
        raise RuntimeError("sql é obrigatório")
    for padrao, nome in NEGADOS_SQL:
        if padrao.search(consulta):
            raise RuntimeError(
                f"recusado: {nome}. Isto não se desfaz e não passa por aqui — "
                "se for mesmo necessário, faça pelo terminal, conscientemente."
            )
    if not args.get("escrita") and not SO_LEITURA.match(consulta):
        raise RuntimeError("só leitura por padrão (SELECT/SHOW/DESCRIBE/EXPLAIN). Para DDL/DML passe escrita=true.")

    projeto = projeto_padrao(args)
    usuario = var_projeto(projeto, "DB_USER")
    banco = var_projeto(projeto, "DB_DATABASE")
    senha = var_projeto(projeto, "DB_PASSWORD")
    # A senha vai na PRIMEIRA linha do stdin e é consumida pelo read: nunca em argv (o ps de
    # outro usuário na máquina compartilhada leria). O .cnf nasce com umask 077 e é apagado.
    remoto = (
        'umask 077; CNF=$(mktemp); read -r SENHA; '
        'printf "[client]\\nuser=%s\\npassword=%s\\nhost=127.0.0.1\\n" '
        + shlex.quote(usuario) + ' "$SENHA" > "$CNF"; '
        'mysql --defaults-extra-file="$CNF" -t ' + shlex.quote(banco) + ' 2>&1; '
        'RET=$?; rm -f "$CNF"; exit $RET'
    )
    return ssh(remoto, timeout=int(args.get("timeout", 120)), entrada=senha + "\n" + consulta + "\n")


def t_log_ref(args: dict) -> str:
    """Acha no error_log o SQL por trás de um erro que chegou ao usuário.

    O Mysql do CML não manda mais SQL para o cliente (vazava o schema na tela): a mensagem
    leva código e uma ref., e o detalhe fica no log com a MESMA ref.

    Onde procurar não é óbvio: o php.ini da Hostinger define error_log como caminho RELATIVO,
    então o arquivo nasce no diretório do script que falhou — tipicamente cml/services/ — e
    não num diretório central de logs (~/logs não existe nesta conta). Por isso a busca é um
    find sob a raiz do projeto, e não uma lista fixa de caminhos."""
    projeto = projeto_padrao(args)
    raiz = raiz_deploy(projeto)
    ref = (args.get("ref") or "").strip()
    if ref and not re.fullmatch(r"[0-9a-fA-F]{4,32}", ref):
        raise RuntimeError("ref deve ser hexadecimal (é o que o Mysql gera)")
    linhas = min(int(args.get("linhas", 40)), 200)

    # Um script só: acha os logs, avisa quando não há nenhum (que é diferente de "a ref não
    # apareceu") e só então filtra. O status do grep depois de um pipe é o do último comando,
    # então o "não achei" é decidido contando linhas, não por "||".
    procura = (
        f'LOGS=$(find {shlex.quote(raiz)} -maxdepth 4 -type f -name "error_log" 2>/dev/null); '
        f'if [ -z "$LOGS" ]; then '
        f'  echo "[nenhum error_log sob {raiz} — o PHP grava no diretorio do script que falhou "'
        f'"(cml/services/error_log); sem erro registrado ainda, ou sem permissao de escrita]"; exit 0; fi; '
        f'echo "== arquivos encontrados:"; echo "$LOGS"; echo "== conteudo:"; '
    )
    if ref:
        procura += (
            f'ACHOU=$(echo "$LOGS" | xargs grep -h -F "[{ref}]" 2>/dev/null | tail -n {linhas}); '
            f'if [ -z "$ACHOU" ]; then echo "[nada com a ref {ref} nestes arquivos]"; '
            f'else echo "$ACHOU"; fi'
        )
    else:
        procura += f'echo "$LOGS" | xargs tail -n {linhas} -q 2>/dev/null | tail -n {linhas}'
    return ssh(procura, timeout=int(args.get("timeout", 90)))


def t_smoke(args: dict) -> str:
    """Os testes de ponta a ponta do DEPLOY.md, da estação, por HTTPS: o 403 no config.json,
    o Domain.list e o Session.publickey (que toca banco e exercita o crypto.path)."""
    url = (args.get("url") or "").strip().rstrip("/")
    if not url:
        # O ~/.cml.json guarda a URL base que o cliente usa — mesma coisa que testar.
        try:
            with open(os.path.expanduser("~/.cml.json"), encoding="utf-8") as f:
                url = ((json.load(f).get("login") or {}).get("server") or "").rstrip("/")
        except Exception:
            url = ""
    if not url:
        raise RuntimeError("informe url (ex.: https://site/projeto) — não achei em ~/.cml.json")
    dominio = args.get("domain") or "cyberwar"

    def curl(*extra):
        p = subprocess.run(["curl", "-s", "--max-time", "30", *extra], capture_output=True, text=True, timeout=45)
        return (p.stdout or "") + (p.stderr or "")

    linhas = []
    codigo = curl("-o", "/dev/null", "-w", "%{http_code}", f"{url}/cml/data/config.json")
    linhas.append(f"config.json protegido (esperado 403): {codigo}")
    env = json.dumps({"version": "001", "class": "Domain", "method": "list", "token": "",
                      "domain": dominio, "parameters": "00000000{}", "session": ""})
    resp = curl("-H", "Content-type: application/json", "-X", "POST",
                f"{url}/cml/services/execute.php", "-d", env)
    linhas.append("Domain.list: " + ("ok" if '"status":true' in resp else "FALHOU -> " + resp[:300]))
    env = json.dumps({"version": "001", "class": "Session", "method": "publickey", "token": "",
                      "domain": dominio, "parameters": '00000000{"username":"__smoke__"}', "session": ""})
    resp = curl("-H", "Content-type: application/json", "-X", "POST",
                f"{url}/cml/services/execute.php", "-d", env)
    linhas.append("Session.publickey (toca banco + crypto.path): "
                  + ("ok" if '"status":true' in resp else "FALHOU -> " + resp[:300]))
    return "\n".join(linhas)


def t_executar(args: dict) -> str:
    comando = args.get("comando", "")
    if not comando.strip():
        raise RuntimeError("comando é obrigatório")
    for padrao in NEGADOS_COMANDO:
        if padrao.search(comando):
            raise RuntimeError(
                "recusado por ser destrutivo de forma óbvia. "
                "Se for mesmo necessário, faça pelo terminal, conscientemente."
            )
    return ssh(comando, timeout=int(args.get("timeout", TIMEOUT_PADRAO)))


P_PROJETO = {"type": "string", "description": "nome em CML_PROJECTS; padrão é o primeiro"}

FERRAMENTAS = [
    {"name": "projetos",
     "description": "Lista os projetos de CML_PROJECTS e a raiz de deploy de cada um.",
     "inputSchema": {"type": "object", "properties": {}},
     "handler": t_projetos},
    {"name": "flag_confirmar",
     "description": ("Confirma a raiz de deploy pela flag — o arquivo que só existe na raiz remota. "
                     "Regra que vem antes de qualquer envio (DEPLOY.md). Sem flag, publicar é proibido."),
     "inputSchema": {"type": "object", "properties": {"projeto": P_PROJETO}},
     "handler": t_flag_confirmar},
    {"name": "listar",
     "description": "Lista um diretório no servidor. Sem caminho, lista a raiz de deploy do projeto.",
     "inputSchema": {"type": "object", "properties": {
         "caminho": {"type": "string"}, "profundidade": {"type": "integer", "description": "1 = ls; >1 usa find (máx. 5)"},
         "projeto": P_PROJETO}},
     "handler": t_listar},
    {"name": "ler_arquivo",
     "description": ("Lê o começo de um arquivo do servidor. Recusa .env, chaves, certificados e "
                     "data/config.json (senha do MySQL em claro)."),
     "inputSchema": {"type": "object", "properties": {
         "caminho": {"type": "string"}, "linhas": {"type": "integer", "description": "padrão 400, máx. 2000"}},
         "required": ["caminho"]},
     "handler": t_ler_arquivo},
    {"name": "env_chaves",
     "description": "Nomes das variáveis do ~/.env do servidor. NUNCA devolve valores.",
     "inputSchema": {"type": "object", "properties": {}},
     "handler": t_env_chaves},
    {"name": "php",
     "description": ("Executa o PHP da versão indicada (padrão 85 = 8.5). Use sempre isto em vez de "
                     "'php' solto: o php do PATH no SSH é 7.4 e não é o runtime de produção."),
     "inputSchema": {"type": "object", "properties": {
         "argumentos": {"type": "string", "description": "ex.: '-l arquivo.php' ou '-v'"},
         "versao": {"type": "string", "description": "80..85 — padrão 85"},
         "cwd": {"type": "string"}, "timeout": {"type": "integer"}}},
     "handler": t_php},
    {"name": "php_versoes",
     "description": "Binários alt-php disponíveis e a versão do php do PATH.",
     "inputSchema": {"type": "object", "properties": {}},
     "handler": t_php_versoes},
    {"name": "lint",
     "description": "php -l com o binário de PRODUÇÃO em todo .php publicado. Lista só o que falhou.",
     "inputSchema": {"type": "object", "properties": {
         "caminho": {"type": "string", "description": "padrão: <raiz>/cml"},
         "versao": {"type": "string"}, "timeout": {"type": "integer"}, "projeto": P_PROJETO}},
     "handler": t_lint},
    {"name": "deploy",
     "description": ("Publica: roda script/deploy.sh, confere a flag e envia com --exclude data/ e "
                     "SEM --delete. Exige confirmar=true. Não envia data/ (config e certificados são do servidor)."),
     "inputSchema": {"type": "object", "properties": {
         "confirmar": {"type": "boolean", "description": "obrigatório true — publica em produção"},
         "projeto": P_PROJETO}, "required": ["confirmar"]},
     "handler": t_deploy},
    {"name": "sql",
     "description": ("Consulta o MySQL do projeto. Leitura por padrão; escrita=true libera DDL/DML, "
                     "mas DROP/TRUNCATE/GRANT e DELETE|UPDATE sem WHERE são sempre recusados. "
                     "A senha vai por stdin, nunca em argv."),
     "inputSchema": {"type": "object", "properties": {
         "sql": {"type": "string"}, "escrita": {"type": "boolean"},
         "timeout": {"type": "integer"}, "projeto": P_PROJETO}, "required": ["sql"]},
     "handler": t_sql},
    {"name": "log_ref",
     "description": ("Procura no error_log a ref. de um erro de banco (a mensagem que chega ao usuário "
                     "traz código + ref.; o SQL fica no log). Sem ref, mostra o fim dos logs."),
     "inputSchema": {"type": "object", "properties": {
         "ref": {"type": "string", "description": "hex que apareceu na mensagem"},
         "linhas": {"type": "integer"}, "projeto": P_PROJETO}},
     "handler": t_log_ref},
    {"name": "smoke",
     "description": ("Testes de ponta a ponta por HTTPS (DEPLOY.md): 403 no config.json, Domain.list e "
                     "Session.publickey. Sem url, usa a do ~/.cml.json."),
     "inputSchema": {"type": "object", "properties": {
         "url": {"type": "string"}, "domain": {"type": "string"}}},
     "handler": t_smoke},
    {"name": "executar",
     "description": ("Executa um comando no servidor. Recusa o obviamente destrutivo e mexer no data/. "
                     "Não é sandbox: é rede de proteção contra engano, não contra intenção."),
     "inputSchema": {"type": "object", "properties": {
         "comando": {"type": "string"},
         "timeout": {"type": "integer", "description": f"segundos; padrão {TIMEOUT_PADRAO}, máx. {TIMEOUT_MAXIMO}"}},
         "required": ["comando"]},
     "handler": t_executar},
]


# --------------------------------------------------------------------------
# JSON-RPC / MCP sobre stdio
# --------------------------------------------------------------------------
def responder(id_, resultado=None, erro=None) -> None:
    msg = {"jsonrpc": "2.0", "id": id_}
    if erro is not None:
        msg["error"] = erro
    else:
        msg["result"] = resultado
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def principal() -> int:
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        try:
            req = json.loads(linha)
        except json.JSONDecodeError:
            continue

        metodo = req.get("method")
        id_ = req.get("id")

        if metodo == "initialize":
            versao = (req.get("params") or {}).get("protocolVersion") or "2025-06-18"
            responder(id_, {
                "protocolVersion": versao,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "cml-remoto", "version": "0.1.0"},
            })
        elif metodo in ("notifications/initialized", "initialized"):
            continue  # notificação: não se responde
        elif metodo == "ping":
            responder(id_, {})
        elif metodo == "tools/list":
            responder(id_, {"tools": [{k: f[k] for k in ("name", "description", "inputSchema")}
                                      for f in FERRAMENTAS]})
        elif metodo == "tools/call":
            params = req.get("params") or {}
            nome = params.get("name")
            args = params.get("arguments") or {}
            alvo = next((f for f in FERRAMENTAS if f["name"] == nome), None)
            if alvo is None:
                responder(id_, erro={"code": -32602, "message": f"ferramenta desconhecida: {nome}"})
                continue
            try:
                texto = alvo["handler"](args)
                responder(id_, {"content": [{"type": "text", "text": texto}]})
            except Exception as e:  # erro de ferramenta, não do protocolo
                responder(id_, {"content": [{"type": "text", "text": f"ERRO: {e}"}], "isError": True})
        elif id_ is not None:
            responder(id_, erro={"code": -32601, "message": f"método não suportado: {metodo}"})
    return 0


if __name__ == "__main__":
    # Chamado pelo ssh como SSH_ASKPASS: responde a pergunta da senha e sai. A senha sai do
    # ~/.env neste instante — não fica em arquivo nem em variável exportada de antemão.
    if len(sys.argv) > 1 and sys.argv[1] == "--askpass":
        sys.stdout.write(env_local("SSH_HOSTINGER_PASSWORD") + "\n")
        sys.exit(0)
    sys.exit(principal())
