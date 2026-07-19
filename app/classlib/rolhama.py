"""Cliente do rolhama (Ollama remoto via webapi PHP+MySQL).

Contrato normativo em ~/desenv/rolhama/llm/INTEGRACAO.md e ~/desenv/rolhama/webapi/SPEC.md.
O bdd.py ao lado (cifra ChaCha20-Poly1305 do payload) e o webapi.py (transporte HTTP + MAC
de autenticacao) sao copia LITERAL do rolhama/llm/ — stdlib pura, sem dependencia nova.
Para atualizar, recopie os dois de la; o bdd.py e byte a byte identico ao do worker (senao
a resposta nao decifra).

Pontos do contrato que este cliente respeita:

- **Fila por canal, resposta por job (UUID)**: o POST enfileira um job e devolve o UUID; a
  resposta vem por esse UUID. Nao ha mais 409 nem remove() de pre-limpeza — isso era do
  transporte antigo (bddphp, slots por endereco HKDF), que foi apagado da Hostinger.
- **Um por vez GLOBALMENTE**: o worker e concentrador de thread unica e serializa em toda a
  maquina — canal separa fluxo/projeto, nao da vazao. Uma geracao do CML segura a fila de
  todo mundo (questoes4, descricao4, avaliador4, kdd-bot) enquanto roda; por isso o report
  vai num prompt so, e nao em dezenas de chamadas.
- **Canal FIXO por projeto**: a alocacao dinamica (op "alocar") era do bddphp. No webapi a
  rota REST de alocacao ainda e pendencia (rolhama/llm/CANAIS.md), entao o canal e semeado
  no servidor e fixado aqui. report="cml"->507, bot="cml/entidades"->510 (os canais LLM
  livres da semente; 508=WHISPER e 509=EMBED sao de outro mecanismo). Sobrescrevivel por
  env se o cadastro do servidor mudar.
- **MAC de autenticacao** (K_auth[canal], automatico no webapi.py) barra escrita de terceiro
  nos canais. A cifra E2E (bdd) e o MAC saem ambos de base = sha256(ROLHAMA_BDD_KEY).
- **Teto de 64 MiB por blob** (413 acima) — mas o limite real de quem monta o prompt e a
  janela de contexto do modelo, muito menor.
- A chave le e escreve os canais que ela cobre — mesmo dominio de confianca dos outros
  projetos (isolamento forte por canal e evolucao planejada do rolhama, ainda nao existe).
"""

import os, sys, inspect, json, time;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( CURRENTDIR );

import bdd;
import webapi;

PROJETO      = "cml";        # projeto padrao (o report). O bot de entidades usa o seu.
# Teto do webapi (ROLHAMA_WEBAPI_MAX_BLOB no servidor, default 64 MiB): 413 acima. O que de
# fato limita o prompt e a janela do modelo, nao isto — mas report.py importa como guarda.
BLOB_MAX     = 67108864;     # 64 MiB
POLL_WAIT    = 30;           # o wait maximo por chamada e 60s; o laco cobre esperas maiores
ESPERA_TOTAL = 3600;

# Endereco do webapi. Sem default embutido de infraestrutura no repositorio publico: vem do
# ~/.env, igual a chave. WEBAPI_URL_PADRAO e so o host publico ja documentado do servico.
WEBAPI_URL_PADRAO = "https://wellington.tec.br/rolhama";


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


# Canal FIXO por projeto. O webapi ainda nao tem rota de alocacao (CANAIS.md), entao o
# cadastro e semeado no servidor e o cliente so aponta para o numero certo. Os defaults sao
# os canais historicos do CML; um env por projeto permite mudar sem editar codigo se o
# cadastro do servidor for outro.
# 507 e 510 sao os canais LLM livres da semente do webapi. 508=WHISPER e 509=EMBED tem
# outro mecanismo — mandar texto para la nao gera resposta de LLM.
CANAL_POR_PROJETO = {
    "cml":           int( _env("CML_ROLHAMA_CANAL",           "507") ),
    "cml/entidades": int( _env("CML_ROLHAMA_CANAL_ENTIDADES", "510") ),
};


class Rolhama:
    def __init__(self, projeto=PROJETO):
        # O canal e por PROJETO: dois projetos no mesmo canal decifrariam a resposta um do
        # outro (mesma chave). Por isso o projeto e parametro — o report e "cml", o bot e
        # "cml/entidades".
        self.projeto = projeto;
        chave = _env("ROLHAMA_BDD_KEY");
        if chave == None or chave == "":
            raise Exception("Falta ROLHAMA_BDD_KEY no ~/.env (a mesma chave do worker; veja rolhama/llm/INTEGRACAO.md).");
        # URL do webapi. Aceita ROLHAMA_BDD_URL por compatibilidade com o env antigo, mas a
        # nova (ROLHAMA_WEBAPI_URL) vem na frente; sem nenhuma, o host publico documentado.
        self.url = _env("ROLHAMA_WEBAPI_URL") or _env("ROLHAMA_BDD_URL") or WEBAPI_URL_PADRAO;

        if projeto not in CANAL_POR_PROJETO:
            # Canal desconhecido travaria esperando resposta de um canal que o worker nao
            # atende. Melhor falhar aqui, com o nome do projeto, do que no timeout de 1h.
            raise Exception("Projeto sem canal fixo no rolhama: '" + str(projeto) + "'. Cadastre em CANAL_POR_PROJETO.");
        self.canal = CANAL_POR_PROJETO[projeto];

        # base = sha256(chave): raiz da cifra E2E (bdd) e da autenticacao (k_auth). O
        # webapi.py deriva as duas; o worker faz o mesmo do outro lado.
        self.base = webapi.base_secret(chave);
        self.api  = webapi.ClientAPI(self.url, self.canal, webapi.k_auth(chave, self.canal));

    def alocar(self, uso=None):
        """Compat: no bddphp isto pedia o canal ao worker. No webapi o canal e fixo (semeado
        no servidor), entao so devolve o canal do projeto — nenhuma ida ao servidor. O
        parametro `uso` fica so por compatibilidade de assinatura."""
        return self.canal;

    def __troca__(self, payload_bytes, espera_total=ESPERA_TOTAL):
        """Sela o payload, enfileira o job no canal e espera a resposta pelo UUID. Devolve os
        bytes crus ja decifrados."""
        if len(payload_bytes) > BLOB_MAX:
            raise Exception("Payload tem " + str(len(payload_bytes)) + " bytes; o teto do webapi é " + str(BLOB_MAX) + " (413 acima).");
        # seal/open_blob cifram por (part, canal): a mesma derivacao do worker. O webapi e
        # cego ao conteudo — so ve canal, tamanho e instante.
        blob = bdd.seal( self.base, "request", self.canal, payload_bytes );
        job  = self.api.enqueue( blob );

        limite = time.time() + espera_total;
        while time.time() < limite:
            resp = self.api.response( job, wait=POLL_WAIT );
            if resp != None:
                return bdd.open_blob( self.base, "response", self.canal, resp );
        raise Exception("Sem resposta no canal " + str(self.canal) + " (job " + str(job) + ") após " + str(espera_total) + "s.");

    def gerar(self, prompt, model=None, ctx=None, formato=None, espera_total=ESPERA_TOTAL, idioma_instrucao=None):
        """Manda o prompt para o ollama pelo canal do projeto e devolve o texto cru.

        formato="json" ativa o decoding restrito do ollama: a saida e JSON valido por
        construcao. Sem isso, extrair estrutura de texto livre vira parsing fragil — o
        modelo enfeita com markdown, preambulo e explicacao.

        idioma_instrucao: a cultura/idioma do mapa. Vai como ULTIMA linha do prompt (recencia)
        para o modelo respeitar o idioma na saida. Toda chamada ao rolhama deve passar isto.
        """
        if idioma_instrucao:
            prompt = prompt.rstrip() + "\n\n" + idioma_instrucao;
        if model == None and ctx == None and formato == None:
            payload = prompt.encode("utf-8");   # texto puro: contexto zero, modelo padrao
        else:
            corpo = {"prompt": prompt};
            if model   != None: corpo["model"]  = model;
            if ctx     != None: corpo["ctx"]    = ctx;
            if formato != None: corpo["format"] = formato;
            payload = json.dumps(corpo).encode("utf-8");
        return self.__troca__(payload, espera_total=espera_total).decode("utf-8", errors="replace");
