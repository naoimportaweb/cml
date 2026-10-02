"""Wayback Machine (CDX): primeira e ultima captura e as URLs historicas de um dominio. A data da
primeira captura de cada URL vira start_date do vinculo — aparece na timeline."""

import os, sys, inspect, re;
from urllib.parse import urlparse;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA;
from transform import _osint as o;

CDX = "https://web.archive.org/cdx/search/cdx";
MAX_URLS = 40;


def _cdx(http, params):
    resp = http.get(CDX, params=dict(params, output="json"), timeout=60);
    try:
        linhas = resp.json();
    except ValueError:
        return [];
    return linhas[1:] if linhas else [];       # a 1a linha e o cabecalho


class TransformWayback(Transform):
    def executar(self, entrada, ctx):
        http = ctx.http();
        dom = o.exigir(o.dominio_da_entrada(entrada), "um domínio ou URL", entrada);
        r = Resultado();
        base = {"url": dom, "matchType": "domain"};

        primeira = _cdx(http, dict(base, fl="timestamp", limit=1));
        if not primeira:
            r.aviso("O Wayback Machine não tem capturas de %s." % dom);
            return r;
        ultima = _cdx(http, dict(base, fl="timestamp", limit=-1));
        ini, fim = o.data_iso(primeira[0][0]), o.data_iso(ultima[0][0]) if ultima else None;
        ref = ctx.ref("Wayback Machine: capturas de " + dom, "https://web.archive.org/web/*/" + dom);
        r.entidade("arquivo", "Wayback Machine – " + dom, etype="other", sub_etype="arquivo web",
                   description="Capturas públicas de %s entre %s e %s." % (dom, ini, fim), referencias=[ref]);
        r.vinculo(ENTRADA, "arquivo", "foi arquivado em", start_date=ini, end_date=fim, referencias=[ref]);

        linhas = _cdx(http, dict(base, fl="timestamp,original,statuscode,mimetype", collapse="urlkey",
                                 filter="statuscode:200", limit=400));
        vistas = set();
        for ts, original, _st, mime in linhas:
            url = re.sub(r":80(/|$)", r"\1", str(original)).strip();
            p = urlparse(url);
            if p.path.lower().endswith(o.SUFIXOS_ESTATICOS) or "html" not in str(mime) or len(url) > 200 or "%" in p.path:
                continue;
            if url in vistas:
                continue;
            vistas.add(url);
            if len(vistas) > MAX_URLS:
                r.aviso("Cortado em %d URLs históricas." % MAX_URLS);
                break;
            chave = "url_%d" % len(vistas);
            cap = ctx.ref("Captura de " + o.corta(url, 80), "https://web.archive.org/web/%s/%s" % (ts, url));
            r.entidade(chave, o.corta(url, 240), etype="other", sub_etype="url",
                       description="Página de %s vista no Wayback Machine desde %s." % (dom, o.data_iso(ts)), referencias=[cap]);
            r.vinculo(ENTRADA, chave, "teve a página", start_date=o.data_iso(ts), referencias=[cap]);
        return r;
