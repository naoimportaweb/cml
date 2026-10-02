"""Contexto entregue a cada transform: HTTP (UA de Firefox, rota direta/tor), LLM (rolhama ou
ollama), craudiowebot, consulta a base do CML e log. E a unica porta dos transforms para o
mundo — assim rota, canal e chaves ficam num lugar so."""

import os, sys, json, socket, time, inspect;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( CURRENTDIR ) );

from transform.nucleo import env, rota_efetiva, backend_llm, ErroTransform;

# Firefox corrente (release 157 em 2026-09-29; ciclo de 4 semanas). Regra do dono: todo acesso
# a site externo sai com UA de Firefox atualizado. CML_TX_USER_AGENT sobrescreve sem editar codigo.
UA = env("CML_TX_USER_AGENT", "Mozilla/5.0 (X11; Linux x86_64; rv:157.0) Gecko/20100101 Firefox/157.0");

TIMEOUT_HTTP = 25;
CANAL_LLM = "cml/entidades";     # 510: mesma natureza do bot de entidades (decisao do dono)


class Http:
    """requests com UA fixo e a rota do transform. Rota 'tor' usa o proxy SOCKS5 (socks5h: o
    DNS tambem sai pelo Tor, senao vaza); 'direta' usa o proxy opcional CML_TX_PROXY_DIRETA."""

    def __init__(self, rota, cancelado):
        import requests;
        self.rota = rota;
        self.cancelado = cancelado;
        self.s = requests.Session();
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"});
        proxy = None;
        if rota == "tor":
            proxy = env("CML_TX_PROXY_TOR", "socks5h://127.0.0.1:9050");
        elif rota == "direta":
            proxy = env("CML_TX_PROXY_DIRETA");
        if proxy:
            self.s.proxies.update({"http": proxy, "https": proxy});

    def get(self, url, params=None, headers=None, timeout=TIMEOUT_HTTP):
        if self.cancelado():
            raise ErroTransform("cancelado");
        try:
            r = self.s.get(url, params=params, headers=headers, timeout=timeout);
        except Exception as e:
            if "SOCKS" in type(e).__name__.upper() or "socks" in str(e).lower() or "missing dependencies" in str(e).lower():
                raise ErroTransform("rota Tor indisponível (proxy SOCKS ou PySocks ausente): " + str(e)[:160]);
            raise ErroTransform("falha de rede em " + url.split("?")[0] + ": " + type(e).__name__);
        if r.status_code != 200:
            raise ErroTransform("HTTP %d em %s" % (r.status_code, url.split("?")[0]));
        return r;

    def json(self, url, **kw):
        r = self.get(url, **kw);
        try:
            return r.json();
        except Exception:
            raise ErroTransform("resposta não é JSON em " + url.split("?")[0]);


class LLM:
    """Backend de LLM selecionavel. `rolhama` (padrao) e a lei do workspace: canal 510, E2E, fila
    global. `ollama` e opt-in (CML_LLM_BACKEND=ollama + CML_OLLAMA_URL) e perde o E2E."""

    def __init__(self, cfg, cancelado):
        self.backend = backend_llm(cfg);
        self.cancelado = cancelado;

    def gerar(self, prompt, formato=None, idioma_instrucao=None, espera_total=900):
        from classlib.report import MODELO;
        if self.backend == "rolhama":
            from classlib.rolhama import Rolhama;
            return Rolhama(projeto=CANAL_LLM).gerar(prompt, model=MODELO, formato=formato,
                                                   espera_total=espera_total, idioma_instrucao=idioma_instrucao);
        if self.backend == "ollama":
            import requests;
            url = env("CML_OLLAMA_URL");
            if not url:
                raise ErroTransform("CML_OLLAMA_URL não configurada no ~/.env");
            if idioma_instrucao:
                prompt = prompt.rstrip() + "\n\n" + idioma_instrucao;
            corpo = {"model": env("CML_OLLAMA_MODELO", MODELO), "prompt": prompt, "stream": False};
            if formato:
                corpo["format"] = formato;
            try:
                r = requests.post(url.rstrip("/") + "/api/generate", json=corpo, timeout=espera_total);
                r.raise_for_status();
                return r.json().get("response", "");
            except Exception as e:
                raise ErroTransform("Ollama direto falhou: " + type(e).__name__ + " " + str(e)[:120]);
        raise ErroTransform("backend de LLM desconhecido: " + str(self.backend));


class Craudio:
    """Cliente NDJSON do craudiowebot --servir (127.0.0.1, porta CML_CRAUDIO_PORTA, padrao 8765)."""

    def __init__(self, cancelado):
        self.porta = int(env("CML_CRAUDIO_PORTA", "8765"));
        self.cancelado = cancelado;

    def lote(self, acoes, espera=120):
        try:
            s = socket.create_connection(("127.0.0.1", self.porta), timeout=10);
        except Exception:
            raise ErroTransform("craudiowebot não está respondendo em 127.0.0.1:%d (suba com 'python3 browser.py --servir')." % self.porta);
        try:
            s.settimeout(espera);
            s.sendall((json.dumps({"actions": acoes}) + "\n").encode("utf-8"));
            buf = b"";
            while b"\n" not in buf:
                if self.cancelado():
                    raise ErroTransform("cancelado");
                parte = s.recv(1 << 20);
                if not parte:
                    break;
                buf += parte;
            resp = json.loads(buf.split(b"\n")[0].decode("utf-8", errors="replace"));
        except ErroTransform:
            raise;
        except Exception as e:
            raise ErroTransform("falha no craudiowebot: " + type(e).__name__);
        finally:
            s.close();
        if not resp.get("ok"):
            raise ErroTransform("craudiowebot recusou: " + str(resp.get("erro")));
        return resp.get("resultados") or [];

    def html(self, url, espera_pagina=4):
        res = self.lote([{"type": "navigate", "value": url}, {"type": "sleep", "value": espera_pagina},
                         {"type": "html", "id": "pagina"}]);
        for r in res:
            if r.get("type") == "html":
                return r.get("html") or "";
        raise ErroTransform("craudiowebot não devolveu o HTML da página");


class Base:
    """Consultas a base do CML pelo servidor (mesmo JSON-RPC do app). Pode rodar em thread."""

    def buscar(self, texto, etypes="person,organization,other"):
        from classlib.entity import Entity;
        return Entity.search(etypes, texto);

    def associadas(self, entity_id):
        from classlib.connectobject import ConnectObject;
        js = ConnectObject().__execute__("Entity", "associations", {"id": entity_id});
        if not js.get("status"):
            raise ErroTransform("servidor sem Entity.associations (faça o deploy do servidor): " + str(js.get("error"))[:120]);
        return js.get("return") or [];


class Contexto:
    def __init__(self, cfg, cancelado=lambda: False):
        self.cfg = cfg;
        self.cancelado = cancelado;
        self.rota = rota_efetiva(cfg);
        self._http = None;

    def http(self):
        if self._http == None:
            self._http = Http(self.rota, self.cancelado);
        return self._http;

    def llm(self):
        return LLM(self.cfg, self.cancelado);

    def craudio(self):
        return Craudio(self.cancelado);

    def base(self):
        return Base();

    def ref(self, title, url, descricao=""):
        # Toda informacao gerada leva a fonte e a data de COLETA. A data de coleta vai na
        # descricao, NAO em start_date: referencia com data vira acontecimento na timeline.
        return {"title": title, "link1": url,
                "descricao": ((descricao + " ") if descricao else "") + "Coletado em " + time.strftime("%Y-%m-%d") + " por transform " + str(self.cfg.get("id"))};
