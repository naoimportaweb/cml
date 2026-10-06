"""Nucleo dos transforms (estilo Maltego): entidade de entrada -> entidades e vinculos propostos.

SEM Qt de proposito (padrao nucleo x casca do fussador): da para testar com python3 puro.
A GUI so chama o Registro (que transforms existem para esta caixa) e o Executor (roda com
cache e log). Contrato completo em ../../SPEC.md, secao 2.
"""

import os, sys, json, hashlib, time, re, unicodedata, inspect, importlib.util, traceback;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
APP = os.path.dirname( CURRENTDIR );
sys.path.append( APP );

ETYPES = ["person", "organization", "other"];
FONTES = ["base-propria", "api-aberta", "ia", "scraping"];
ROTULO_FONTE = {"base-propria": "Base própria", "api-aberta": "APIs abertas", "ia": "IA", "scraping": "Scraping"};
ENTRADA = "ENTRADA";        # chave reservada: a caixa de onde o transform partiu
DIR_CACHE = os.path.expanduser("~/.cml_cache");

# Limites defensivos: um transform com defeito (ou uma fonte hostil) nao pode despejar mil
# caixas no mapa nem um texto de megabytes na proposta.
MAX_ENTIDADES = 200;
MAX_VINCULOS  = 400;
MAX_TEXTO     = 4000;


def env(nome, padrao=None):
    # Mesma leitura do classlib.rolhama._env (ambiente, depois ~/.env sem 'source'), mas sem
    # importar o rolhama (que puxa criptografia) so para ler uma variavel.
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


def norm(s):
    # minusculas, sem acento e sem pontuacao: "OpenAI, Inc." e "openai inc" sao o mesmo nome.
    s = unicodedata.normalize("NFD", str(s or ""));
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower();
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip();


class ErroTransform(Exception):
    """Falha esperada de um transform (fonte fora do ar, entrada invalida). A mensagem vai
    direto para o analista, entao tem que ser legivel."""
    pass;


class Resultado:
    """O que um transform devolve. Tudo em dicts/listas simples (serializavel no cache)."""

    def __init__(self):
        self.entidades = [];
        self.vinculos = [];
        self.avisos = [];

    def entidade(self, chave, text_label, etype="other", sub_etype="", small_label="", description="",
                 referencias=None, id_existente=None):
        self.entidades.append({
            "chave": chave, "text_label": str(text_label or "").strip(), "etype": etype,
            "sub_etype": sub_etype or "", "small_label": small_label or "", "description": description or "",
            "referencias": list(referencias or []), "id": id_existente });
        return chave;

    def vinculo(self, de, para, verbo, start_date=None, end_date=None, referencias=None):
        self.vinculos.append({ "de": de, "para": para, "verbo": str(verbo or "").strip(),
                               "start_date": start_date, "end_date": end_date,
                               "referencias": list(referencias or []) });

    def aviso(self, texto):
        self.avisos.append(str(texto));

    def to_dict(self):
        return {"entidades": self.entidades, "vinculos": self.vinculos, "avisos": self.avisos};

    @staticmethod
    def from_dict(d):
        r = Resultado();
        r.entidades = d.get("entidades") or [];
        r.vinculos = d.get("vinculos") or [];
        r.avisos = d.get("avisos") or [];
        return r;

    def validar(self):
        """Normaliza e descarta o que nao presta, registrando o motivo em `avisos`. Roda no
        Executor, depois de TODO transform: o contrato vale mesmo para transform mal escrito."""
        vistas = {};
        boas = [];
        for e in self.entidades:
            if not isinstance(e, dict):
                continue;
            nome = re.sub(r"\s+", " ", str(e.get("text_label") or "")).strip()[:250];
            chave = str(e.get("chave") or "").strip();
            if nome == "" or chave == "" or chave == ENTRADA:
                self.avisos.append("Entidade descartada (sem nome ou chave inválida): " + repr(e)[:80]);
                continue;
            if chave in vistas:
                self.avisos.append("Chave repetida descartada: " + chave);
                continue;
            if e.get("etype") not in ETYPES:
                e["etype"] = "other";
            e["text_label"] = nome;
            e["chave"] = chave;
            e["description"] = str(e.get("description") or "")[:MAX_TEXTO];
            e["small_label"] = str(e.get("small_label") or "")[:100];
            e["sub_etype"] = str(e.get("sub_etype") or "")[:100];
            e["referencias"] = _refs(e.get("referencias"));
            if not e["referencias"]:
                self.avisos.append("Sem referência de fonte: " + nome);
            vistas[chave] = True;
            boas.append(e);
        if len(boas) > MAX_ENTIDADES:
            self.avisos.append("Resultado cortado: %d entidades (limite %d)." % (len(boas), MAX_ENTIDADES));
            boas = boas[:MAX_ENTIDADES];
            vistas = {e["chave"]: True for e in boas};
        self.entidades = boas;

        ok = [];
        chaves = set(vistas.keys()) | {ENTRADA};
        for v in self.vinculos:
            if not isinstance(v, dict):
                continue;
            verbo = re.sub(r"\s+", " ", str(v.get("verbo") or "")).strip()[:100];
            if verbo == "" or v.get("de") not in chaves or v.get("para") not in chaves or v.get("de") == v.get("para"):
                self.avisos.append("Vínculo descartado: " + repr(v)[:80]);
                continue;
            v["verbo"] = verbo;
            v["referencias"] = _refs(v.get("referencias"));
            ok.append(v);
        if len(ok) > MAX_VINCULOS:
            self.avisos.append("Vínculos cortados em %d." % MAX_VINCULOS);
            ok = ok[:MAX_VINCULOS];
        self.vinculos = ok;
        return self;


def _refs(refs):
    out = [];
    for r in (refs or []):
        if not isinstance(r, dict):
            continue;
        link = str(r.get("link1") or "").strip();
        if link == "":
            continue;
        out.append({ "title": (str(r.get("title") or "").strip() or link)[:250], "link1": link[:2000],
                     "descricao": str(r.get("descricao") or "")[:MAX_TEXTO] });
    return out;


class Transform:
    """Base dos transforms. Subclasse implementa executar(entrada, ctx) -> Resultado."""
    config = None;     # preenchido pelo Registro

    def executar(self, entrada, ctx):
        raise NotImplementedError();


class Registro:
    """Descobre app/transform/<fonte>/<nome>/config.json. Recarrega a cada listagem: transform
    novo aparece sem reiniciar o cliente (e config quebrado nao derruba os outros)."""

    def __init__(self, raiz=CURRENTDIR):
        self.raiz = raiz;
        self.erros = [];

    def todos(self):
        self.erros = [];
        out = [];
        if not os.path.isdir(self.raiz):
            return out;
        for pasta in sorted(os.listdir(self.raiz)):
            base = os.path.join(self.raiz, pasta);
            if not os.path.isdir(base) or pasta.startswith(("_", ".")):
                continue;
            for sub in sorted(os.listdir(base)):
                cfg_path = os.path.join(base, sub, "config.json");
                if not os.path.isfile(cfg_path):
                    continue;
                try:
                    cfg = json.load(open(cfg_path, encoding="utf-8"));
                    for k in ("id", "nome", "entrada", "fonte", "path", "class"):
                        if k not in cfg:
                            raise Exception("falta o campo '" + k + "'");
                    if cfg["fonte"] not in FONTES:
                        raise Exception("fonte inválida: " + str(cfg["fonte"]));
                    cfg["_dir"] = os.path.join(base, sub);
                    out.append(cfg);
                except Exception as e:
                    self.erros.append(cfg_path + ": " + str(e));
        return out;

    def para_entidade(self, etype, sub_etype=""):
        return [c for c in self.todos() if aceita(c, etype, sub_etype)];

    def obter(self, id_):
        for c in self.todos():
            if c["id"] == id_:
                return c;
        return None;

    @staticmethod
    def carregar(cfg):
        caminho = os.path.join(cfg["_dir"], cfg["path"]) if not os.path.isabs(cfg["path"]) else cfg["path"];
        spec = importlib.util.spec_from_file_location("tx_" + re.sub(r"\W", "_", cfg["id"]), caminho);
        modulo = importlib.util.module_from_spec(spec);
        spec.loader.exec_module(modulo);
        inst = getattr(modulo, cfg["class"])();
        inst.config = cfg;
        return inst;


def aceita(cfg, etype, sub_etype=""):
    """`entrada` lista 'etype' ou 'etype:sub_etype' (comparacao sem acento/caixa); '*' = tudo."""
    sub = norm(sub_etype);
    for regra in cfg["entrada"]:
        if regra == "*":
            return True;
        t, _, s = regra.partition(":");
        if t != etype:
            continue;
        if s == "" or norm(s) == sub:
            return True;
    return False;


def indisponivel(cfg, mapa_travado=False):
    """Motivo pelo qual o transform nao pode rodar agora (None = pode). O menu mostra o
    motivo em vez de esconder a opcao: sumir sem explicacao parece defeito."""
    if mapa_travado:
        return "mapa travado (somente leitura)";
    chave = cfg.get("chave_env");
    if chave and not env(chave):
        return "falta " + chave + " no ~/.env";
    if cfg["fonte"] == "ia":
        motivo = motivo_llm();
        if motivo != None:
            return motivo;
    if cfg.get("rede") and cfg["fonte"] in ("api-aberta",) and rota_efetiva(cfg) not in ("direta", "tor"):
        return "rota inválida (use direta ou tor)";
    return None;


def backend_llm(cfg=None):
    # O padrao era "rolhama". O rolhama saiu do ar em 2026-10-05 e nao volta (custava manter
    # ligado), e a lei do workspace passou a ser "LLM e local e sob demanda" -- entao o padrao
    # agora e o Ollama local, e sem CML_OLLAMA_URL simplesmente NAO HA backend. Manter o padrao
    # antigo fazia o app tentar falar com um servico que nao existe e estourar excecao crua.
    escolhido = (cfg or {}).get("llm") or env("CML_LLM_BACKEND", "");
    escolhido = str(escolhido).strip().lower();
    if escolhido != "":
        return escolhido;
    return "ollama" if env("CML_OLLAMA_URL") else "nenhum";


def motivo_llm():
    """Por que o LLM nao esta disponivel agora (None = esta). Um lugar so, para o menu de
    transform, o botao do bot e o botao de report dizerem a MESMA coisa."""
    b = backend_llm();
    if b == "nenhum":
        return ("sem backend de LLM: o rolhama saiu do ar em 2026-10-05. "
                "Defina CML_OLLAMA_URL no ~/.env para usar um Ollama local");
    if b == "ollama":
        return None if env("CML_OLLAMA_URL") else "backend ollama sem CML_OLLAMA_URL no ~/.env";
    if b == "rolhama":
        return ("o rolhama saiu do ar em 2026-10-05 e não volta. "
                "Use CML_LLM_BACKEND=ollama com CML_OLLAMA_URL no ~/.env");
    return "CML_LLM_BACKEND inválido: " + str(b);


def rota_efetiva(cfg):
    r = cfg.get("rota") or env("CML_TX_ROTA_PADRAO", "direta");
    return str(r).strip().lower();


class Executor:
    """Roda um transform com cache e log local (unica trilha de auditoria: a execucao e no
    cliente, nada vai ao servidor)."""

    def __init__(self, dir_cache=DIR_CACHE):
        self.dir_cache = dir_cache;

    def __chave__(self, cfg, entrada):
        base = json.dumps({"i": cfg["id"], "v": cfg.get("versao", "1"),
                           "n": entrada.get("text_label"), "t": entrada.get("etype"), "s": entrada.get("sub_etype"),
                           "u": entrada.get("urls"), "id": entrada.get("id")}, sort_keys=True);
        return hashlib.sha256(base.encode("utf-8")).hexdigest();

    def __arquivo__(self, cfg, chave):
        return os.path.join(self.dir_cache, re.sub(r"[^\w.-]", "_", cfg["id"]), chave + ".json");

    def __ler_cache__(self, cfg, chave):
        ttl = int(cfg.get("ttl", 0) or 0);
        if ttl <= 0:
            return None;
        try:
            arq = self.__arquivo__(cfg, chave);
            if time.time() - os.path.getmtime(arq) > ttl:
                return None;
            return Resultado.from_dict(json.load(open(arq, encoding="utf-8")));
        except Exception:
            return None;

    def __gravar_cache__(self, cfg, chave, resultado):
        if int(cfg.get("ttl", 0) or 0) <= 0:
            return;
        try:
            arq = self.__arquivo__(cfg, chave);
            os.makedirs(os.path.dirname(arq), mode=0o700, exist_ok=True);
            tmp = arq + ".tmp";
            with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
                json.dump(resultado.to_dict(), f, ensure_ascii=False);
            os.replace(tmp, arq);
        except Exception:
            pass;    # cache e otimizacao: falhar em gravar nao pode falhar o transform

    def log(self, cfg, entrada, situacao, n_ent=0, n_vin=0, detalhe="", segundos=0.0):
        try:
            os.makedirs(self.dir_cache, mode=0o700, exist_ok=True);
            linha = {"quando": time.strftime("%Y-%m-%dT%H:%M:%S"), "transform": cfg["id"], "versao": cfg.get("versao", "1"),
                     "entrada": entrada.get("text_label"), "etype": entrada.get("etype"), "situacao": situacao,
                     "entidades": n_ent, "vinculos": n_vin, "segundos": round(segundos, 2), "detalhe": str(detalhe)[:300]};
            if cfg["fonte"] == "ia":
                linha["llm"] = backend_llm(cfg);
            if cfg.get("rede"):
                linha["rota"] = rota_efetiva(cfg);
            fd = os.open(os.path.join(self.dir_cache, "transform.log"), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600);
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                f.write(json.dumps(linha, ensure_ascii=False) + "\n");
        except Exception:
            pass;

    def executar(self, cfg, entrada, ctx_fabrica):
        """`ctx_fabrica(cfg)` cria o Contexto (so se nao houver cache). Devolve (Resultado, do_cache)."""
        inicio = time.time();
        chave = self.__chave__(cfg, entrada);
        r = self.__ler_cache__(cfg, chave);
        if r != None:
            self.log(cfg, entrada, "cache", len(r.entidades), len(r.vinculos), segundos=0);
            return r, True;
        try:
            ctx = ctx_fabrica(cfg);
            inst = Registro.carregar(cfg);
            r = inst.executar(entrada, ctx);
            if not isinstance(r, Resultado):
                raise ErroTransform("o transform não devolveu um Resultado");
            r.validar();
        except ErroTransform as e:
            self.log(cfg, entrada, "erro", detalhe=str(e), segundos=time.time() - inicio);
            raise;
        except Exception as e:
            self.log(cfg, entrada, "falha", detalhe=type(e).__name__ + ": " + str(e), segundos=time.time() - inicio);
            traceback.print_exc();
            raise;
        self.__gravar_cache__(cfg, chave, r);
        self.log(cfg, entrada, "ok", len(r.entidades), len(r.vinculos), segundos=time.time() - inicio);
        return r, False;
