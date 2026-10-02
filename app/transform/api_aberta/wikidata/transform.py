"""Wikidata: acha o item da entidade (pelo link da Wikipedia, se houver, senao pelo nome) e traz
as relacoes estruturadas: empregador, membro de, cargos, filiacao, sede, pais, subsidiarias...
Datas de inicio/fim (P580/P582) viram start_date/end_date do vinculo — alimentam a timeline."""

import os, sys, inspect, re;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA, norm;
from transform import _osint as o;

API = "https://www.wikidata.org/w/api.php";
IDIOMAS = {"pt-BR": "pt", "pt": "pt", "en": "en", "es": "es"};
POR_PAGINA = 10;

# propriedade -> (verbo, sentido, etype padrao, sub_etype). sentido "d": ENTRADA -> alvo;
# "i": alvo -> ENTRADA (a propriedade descreve o alvo em relacao a entrada).
PROPS = {
    "P108": ("trabalha para",       "d", "organization", ""),
    "P463": ("é membro de",         "d", "organization", ""),
    "P102": ("é filiado a",         "d", "organization", ""),
    "P69":  ("estudou em",          "d", "organization", ""),
    "P749": ("é subsidiária de",    "d", "organization", ""),
    "P355": ("tem subsidiária",     "d", "organization", ""),
    "P127": ("é controlada por",    "d", "organization", ""),
    "P169": ("é CEO de",            "i", "person",       ""),
    "P488": ("preside",             "i", "person",       ""),
    "P112": ("fundou",              "i", "person",       ""),
    "P26":  ("é cônjuge de",        "d", "person",       ""),
    "P159": ("tem sede em",         "d", "other",        "local"),
    "P17":  ("localiza-se em",      "d", "other",        "país"),
    "P27":  ("é cidadão de",        "d", "other",        "país"),
    "P39":  ("ocupa o cargo de",    "d", "other",        "cargo"),
};
Q_HUMANO = "Q5";


def _valores(claims, prop):
    out = [];
    # os mais recentes: a lista de claims vem em ordem cronologica
    for c in (claims.get(prop) or [])[-POR_PAGINA:]:
        dv = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value");
        if isinstance(dv, dict) and str(dv.get("id", "")).startswith("Q"):
            q = c.get("qualifiers") or {};
            def data(p):
                try:
                    return o.data_iso(q[p][0]["datavalue"]["value"]["time"]);
                except Exception:
                    return None;
            out.append((dv["id"], data("P580"), data("P582")));
    return out;


class TransformWikidata(Transform):
    def executar(self, entrada, ctx):
        nome = str(entrada.get("text_label") or "").strip();
        lang = IDIOMAS.get(entrada.get("idioma") or "", "en");
        http = ctx.http();
        r = Resultado();

        qid = self.__resolver__(entrada, nome, lang, http, r);
        if not qid:
            raise ErroTransform("Nenhum item do Wikidata encontrado para '%s'." % o.corta(nome, 60));

        langs = lang + "|en";
        dados = http.json(API, params={"action": "wbgetentities", "ids": qid, "props": "claims|labels|descriptions",
                                       "languages": langs, "format": "json"});
        item = (dados.get("entities") or {}).get(qid) or {};
        claims = item.get("claims") or {};
        url_item = "https://www.wikidata.org/wiki/" + qid;
        ref_item = ctx.ref("Wikidata " + qid, url_item);

        alvos = {};         # qid -> lista de (prop, ini, fim)
        for prop in PROPS:
            for (q, ini, fim) in _valores(claims, prop):
                alvos.setdefault(q, []).append((prop, ini, fim));
        if not alvos:
            r.aviso("O item %s existe, mas não tem relações nas propriedades consultadas." % qid);
            return r;

        ids = list(alvos.keys())[:45];
        det = http.json(API, params={"action": "wbgetentities", "ids": "|".join(ids), "props": "labels|descriptions|claims",
                                     "languages": langs, "format": "json"}).get("entities") or {};
        for q in ids:
            e = det.get(q) or {};
            rotulos = e.get("labels") or {};
            rot = (rotulos.get(lang) or rotulos.get("en") or {}).get("value");
            if not rot:
                continue;
            desc = ((e.get("descriptions") or {}).get(lang) or (e.get("descriptions") or {}).get("en") or {}).get("value", "");
            humano = any(((c.get("mainsnak") or {}).get("datavalue") or {}).get("value", {}).get("id") == Q_HUMANO
                         for c in (e.get("claims") or {}).get("P31", []) if isinstance(((c.get("mainsnak") or {}).get("datavalue") or {}).get("value"), dict));
            chave = "wd_" + q;
            primeiro = PROPS[alvos[q][0][0]];
            etype = "person" if humano else primeiro[2];
            ref = ctx.ref("Wikidata " + q, "https://www.wikidata.org/wiki/" + q);
            r.entidade(chave, rot, etype=etype, sub_etype=("" if humano else primeiro[3]),
                       description=o.corta(desc, 300), referencias=[ref]);
            for (prop, ini, fim) in alvos[q]:
                verbo, sentido, _t, _s = PROPS[prop];
                de, para = (ENTRADA, chave) if sentido == "d" else (chave, ENTRADA);
                r.vinculo(de, para, verbo, start_date=ini, end_date=fim, referencias=[ref_item]);
        return r;

    def __resolver__(self, entrada, nome, lang, http, r):
        # 1) link da Wikipedia na entidade -> item exato, sem adivinhar por nome.
        for u in [entrada.get("wikipedia")] + list(entrada.get("urls") or []):
            m = re.match(r"^https?://([a-z\-]+)\.wikipedia\.org/wiki/([^#?]+)", str(u or ""));
            if m:
                from urllib.parse import unquote;
                d = http.json("https://%s.wikipedia.org/w/api.php" % m.group(1),
                              params={"action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
                                      "titles": unquote(m.group(2)), "redirects": 1, "format": "json"});
                for p in (d.get("query", {}).get("pages") or {}).values():
                    q = (p.get("pageprops") or {}).get("wikibase_item");
                    if q:
                        return q;
        # 2) busca pelo nome; prefere rotulo identico, senao o primeiro (com aviso).
        if nome == "":
            return None;
        d = http.json(API, params={"action": "wbsearchentities", "search": nome, "language": lang, "uselang": lang,
                                   "format": "json", "limit": 5});
        achados = d.get("search") or [];
        for a in achados:
            if norm(a.get("label")) == norm(nome):
                return a["id"];
        if achados:
            a = achados[0];
            r.aviso("Sem item de rótulo idêntico; usado o mais provável: %s (%s) — %s. Confira antes de aceitar." %
                    (a.get("label"), a["id"], a.get("description", "sem descrição")));
            return a["id"];
        return None;
