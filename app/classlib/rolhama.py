"""Cliente do rolhama (Ollama remoto via cofre-cego bddphp).

Contrato normativo em ~/desenv/rolhama/SPEC.md; a parte pratica em INTEGRACAO.md. O
bdd.py ao lado e copia literal do rolhama (stdlib pura, sem dependencia nova) — o
projeto hacker faz o mesmo em rotinas/api/bdd.py.

Pontos do contrato que este cliente respeita:

- **Um por um por canal**: manda a request, le a response, so entao a proxima. O worker
  e um concentrador de thread unica e serializa GLOBALMENTE — canal separa fluxo/projeto,
  nao da vazao. Uma geracao do CML segura a fila de todo mundo (questoes4, descricao4,
  avaliador4, kdd-bot) enquanto roda; por isso o report vai num prompt so, e nao em
  dezenas de chamadas.
- **Canal por API, nunca fixo**: {"op":"alocar","projeto":"cml"} no canal 500, idempotente.
  Escolher numero na mao foi o que colocou o kdd-bot e o ajuste_questao.py no mesmo 505.
- **Teto de 1 MiB por blob** (413 acima): quem monta o prompt tem que caber nisso.
- A chave le e escreve TODOS os canais — mesmo dominio de confianca dos outros projetos.
"""

import os, sys, inspect, json, hashlib, time;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( CURRENTDIR );

import bdd;

CANAL_OPS    = 500;      # reservado para testes e ops de catalogo; nunca e alocado
PROJETO      = "cml";        # projeto padrao (o report). O bot de entidades usa o seu.
BLOB_MAX     = 1048576;  # 1 MiB; acima disso o cofre devolve 413
POLL_WAIT    = 30;       # o wait maximo por chamada e 60s; o laco cobre esperas maiores
ESPERA_TOTAL = 3600;


def _env(nome, padrao=None):
    # Le do ambiente e, se faltar, do ~/.env — que e onde as chaves deste usuario moram.
    # Nao usa 'source': o arquivo tem valores nao-quotados com ';' e '&' que o shell
    # executaria.
    v = os.environ.get(nome);
    if v != None and v.strip() != "":
        return v.strip();
    caminho = os.path.expanduser("~/.env");
    if os.path.exists(caminho):
        try:
            for linha in open(caminho, "r", errors="replace"):
                linha = linha.strip();
                if linha == "" or linha.startswith("#") or "=" not in linha:
                    continue;
                k, val = linha.split("=", 1);
                if k.strip() == nome:
                    return val.strip().strip('"').strip("'");
        except Exception:
            pass;
    return padrao;


class Rolhama:
    def __init__(self, projeto=PROJETO):
        # O canal e alocado POR PROJETO e e idempotente: dois consumidores com o mesmo
        # nome recebem o mesmo canal e colidiriam entre si. Por isso o projeto e
        # parametro, e nao constante — o report e "cml", o bot e "cml/entidades".
        self.projeto = projeto;
        chave = _env("ROLHAMA_BDD_KEY");
        if chave == None or chave == "":
            raise Exception("Falta ROLHAMA_BDD_KEY no ~/.env (a mesma chave do worker; veja rolhama/INTEGRACAO.md).");
        # Sem default embutido: este repositorio e publico, e o endereco do cofre e
        # infraestrutura. Vem do ~/.env, igual a chave.
        self.url = _env("ROLHAMA_BDD_URL");
        if self.url == None or self.url == "":
            raise Exception("Falta ROLHAMA_BDD_URL no ~/.env (a URL base do cofre bddphp).");
        self.secret = hashlib.sha256(chave.encode()).digest();
        self.client = bdd.Client(self.url, self.secret);
        self.canal  = None;

    def __troca__(self, canal, payload, espera_total=ESPERA_TOTAL):
        """Sela o payload no canal, espera a resposta e devolve os bytes crus."""
        if len(payload) > BLOB_MAX:
            raise Exception("Payload tem " + str(len(payload)) + " bytes; o teto do cofre é " + str(BLOB_MAX) + " (413 acima).");
        # Limpa os slots antes: um resto de execucao anterior faria o PUT bater 409 e a
        # leitura devolver resposta alheia. E o que o avaliador4.py do hacker faz.
        self.client.remove("request", canal);
        self.client.remove("response", canal);

        status = self.client.send("request", canal, payload);
        if status != 201:
            raise Exception("PUT no canal " + str(canal) + " devolveu " + str(status) + " (409 = canal ocupado).");

        limite = time.time() + espera_total;
        while time.time() < limite:
            resp = self.client.receive("response", canal, wait=POLL_WAIT);
            if resp != None:
                return resp;
        raise Exception("Sem resposta no canal " + str(canal) + " após " + str(espera_total) + "s.");

    def alocar(self, uso="Report em PDF de mapa de vínculos"):
        """Pede o canal do projeto ao worker. Idempotente: sempre devolve o mesmo."""
        if self.canal != None:
            return self.canal;
        pedido = json.dumps({"op": "alocar", "projeto": self.projeto, "uso": uso}).encode("utf-8");
        # Op nao passa pelo ollama: a resposta e rapida, so espera a vez na varredura.
        resposta = self.__troca__(CANAL_OPS, pedido, espera_total=180);
        js = json.loads(resposta.decode("utf-8", errors="replace"));
        if not js.get("ok"):
            raise Exception("O worker recusou alocar canal: " + str(js.get("erro")));
        self.canal = int(js["canal"]);
        return self.canal;

    def canais(self):
        resposta = self.__troca__(CANAL_OPS, json.dumps({"op": "canais"}).encode("utf-8"), espera_total=180);
        return json.loads(resposta.decode("utf-8", errors="replace"));

    def gerar(self, prompt, model=None, ctx=None, formato=None, espera_total=ESPERA_TOTAL):
        """Manda o prompt para o ollama pelo canal do projeto e devolve o texto cru.

        formato="json" ativa o decoding restrito do ollama: a saida e JSON valido por
        construcao. Sem isso, extrair estrutura de texto livre vira parsing fragil — o
        modelo enfeita com markdown, preambulo e explicacao.
        """
        canal = self.alocar();
        if model == None and ctx == None and formato == None:
            payload = prompt.encode("utf-8");   # texto puro: contexto zero, modelo padrao
        else:
            corpo = {"prompt": prompt};
            if model   != None: corpo["model"]  = model;
            if ctx     != None: corpo["ctx"]    = ctx;
            if formato != None: corpo["format"] = formato;
            payload = json.dumps(corpo).encode("utf-8");
        return self.__troca__(canal, payload, espera_total=espera_total).decode("utf-8", errors="replace");
