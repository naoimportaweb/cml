"""abuse.ch URLhaus + ThreatFox para um dominio/IP: URLs de malware hospedadas e IOCs da familia
de malware. Desde 2025 as APIs exigem Auth-Key (gratuita, em auth.abuse.ch) — CML_TX_ABUSECH_KEY."""

import os, sys, inspect, json;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA, env;
from transform import _osint as o;

MAX_URLS = 30;
MAX_IOCS = 30;


def _post(http, url, chave, **kw):
    # Http.get so faz GET; reaproveita a sessao (UA e rota) do proprio ctx.http().
    try:
        resp = http.s.post(url, headers={"Auth-Key": chave}, timeout=30, **kw);
    except Exception as e:
        raise ErroTransform("falha de rede em " + url + ": " + type(e).__name__);
    if resp.status_code in (401, 403):
        raise ErroTransform("abuse.ch recusou a Auth-Key (CML_TX_ABUSECH_KEY).");
    if resp.status_code != 200:
        raise ErroTransform("HTTP %d em %s" % (resp.status_code, url));
    try:
        return resp.json();
    except ValueError:
        raise ErroTransform("resposta não é JSON em " + url);


class TransformAbuseCh(Transform):
    def executar(self, entrada, ctx):
        chave = env("CML_TX_ABUSECH_KEY");
        if not chave:
            raise ErroTransform("falta CML_TX_ABUSECH_KEY no ~/.env (gratuita: auth.abuse.ch).");
        alvo = o.ip_da_entrada(entrada) or o.exigir(o.dominio_da_entrada(entrada), "um domínio ou IP", entrada);
        http = ctx.http();
        r = Resultado();

        d = _post(http, "https://urlhaus-api.abuse.ch/v1/host/", chave, data={"host": alvo});
        ref_h = ctx.ref("URLhaus: " + alvo, "https://urlhaus.abuse.ch/host/" + alvo + "/");
        if d.get("query_status") == "ok":
            for i, u in enumerate((d.get("urls") or [])[:MAX_URLS]):
                c = "uh_%d" % i;
                r.entidade(c, o.corta(u.get("url"), 240), etype="other", sub_etype="url",
                           description=o.corta("URL de malware (%s), status %s. Tags: %s." %
                                               (u.get("threat", "?"), u.get("url_status", "?"), ", ".join(u.get("tags") or []) or "—"), 300),
                           referencias=[ctx.ref("URLhaus", u.get("urlhaus_reference") or ref_h["link1"])]);
                r.vinculo(ENTRADA, c, "hospeda URL de malware", start_date=o.data_iso(u.get("date_added")), referencias=[ref_h]);
        elif d.get("query_status") not in ("no_results", "invalid_host"):
            r.aviso("URLhaus: " + str(d.get("query_status")));

        t = _post(http, "https://threatfox-api.abuse.ch/api/v1/", chave, data=json.dumps({"query": "search_ioc", "search_term": alvo}));
        ref_t = ctx.ref("ThreatFox: " + alvo, "https://threatfox.abuse.ch/browse.php?search=ioc%3A" + alvo);
        if t.get("query_status") == "ok":
            for i, ioc in enumerate((t.get("data") or [])[:MAX_IOCS]):
                fam = ioc.get("malware_printable") or ioc.get("malware");
                if not fam or fam == "Unknown malware":
                    continue;
                c = o.nome_chave("mw", fam);
                if not any(e["chave"] == c for e in r.entidades):
                    r.entidade(c, fam, etype="other", sub_etype="malware",
                               description=o.corta("Família de malware (%s) no ThreatFox." % ioc.get("threat_type_desc", ioc.get("threat_type", "?")), 300),
                               referencias=[ref_t]);
                r.vinculo(ENTRADA, c, "é IOC de", start_date=o.data_iso(ioc.get("first_seen_utc") or ioc.get("first_seen")),
                          referencias=[ctx.ref("ThreatFox IOC", ioc.get("reference") or ref_t["link1"])]);
        elif t.get("query_status") not in ("no_result", "no_results"):
            r.aviso("ThreatFox: " + str(t.get("query_status")));
        if not r.entidades:
            r.aviso("Sem registros no URLhaus/ThreatFox para %s." % alvo);
        return r;
