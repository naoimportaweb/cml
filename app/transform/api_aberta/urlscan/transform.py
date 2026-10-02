"""urlscan.io: varreduras publicas do dominio — IPs que o hospedaram, ASNs e paginas. A data da
varredura vira start_date. CML_TX_URLSCAN_KEY (opcional) sobe o limite de consultas."""

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA, env;
from transform import _osint as o;

MAX_RESULTADOS = 50;
MAX_URLS = 15;


class TransformUrlscan(Transform):
    def executar(self, entrada, ctx):
        ip = o.ip_da_entrada(entrada);
        if ip:
            consulta = 'page.ip:"%s"' % ip;
            alvo = ip;
        else:
            alvo = o.exigir(o.dominio_da_entrada(entrada), "um domínio ou IP", entrada);
            consulta = "domain:" + alvo;
        chave = env("CML_TX_URLSCAN_KEY");
        d = ctx.http().json("https://urlscan.io/api/v1/search/", params={"q": consulta, "size": MAX_RESULTADOS},
                            headers={"API-Key": chave} if chave else None);
        r = Resultado();
        ips, asns, urls = {}, {}, {};
        for x in d.get("results") or []:
            pg, tk = x.get("page") or {}, x.get("task") or {}
            quando = o.data_iso(tk.get("time"));
            link = "https://urlscan.io/result/%s/" % x.get("_id");
            if pg.get("ip") and not ip and o.ip_de_texto(pg["ip"]):
                ips.setdefault(pg["ip"], (quando, link));
            if pg.get("asn"):
                asns.setdefault(pg["asn"], (pg.get("asnname") or "", link));
            if tk.get("url") and len(urls) < MAX_URLS:
                urls.setdefault(tk["url"], (quando, link));
        ref = ctx.ref("urlscan.io: " + alvo, "https://urlscan.io/search/#" + consulta);
        for v, (quando, link) in ips.items():
            c = "ip_" + v;
            r.entidade(c, v, etype="other", sub_etype="ip", description="IP visto em varredura pública do urlscan.io.", referencias=[ctx.ref("Varredura urlscan.io", link)]);
            r.vinculo(ENTRADA, c, "já foi hospedado em", start_date=quando, referencias=[ref]);
        for a, (nome, link) in asns.items():
            c = o.nome_chave("asn", a);
            r.entidade(c, "%s – %s" % (a, nome) if nome else str(a), etype="other", sub_etype="asn",
                       description="Sistema autônomo visto em varredura pública.", referencias=[ctx.ref("Varredura urlscan.io", link)]);
            r.vinculo(ENTRADA, c, "é servido pelo ASN", referencias=[ref]);
        for u, (quando, link) in urls.items():
            c = o.nome_chave("url", u);
            r.entidade(c, o.corta(u, 240), etype="other", sub_etype="url", description="URL varrida publicamente no urlscan.io.",
                       referencias=[ctx.ref("Varredura urlscan.io", link)]);
            r.vinculo(ENTRADA, c, "teve a página varrida", start_date=quando, referencias=[ref]);
        if not r.entidades:
            r.aviso("Nenhuma varredura pública de %s no urlscan.io." % alvo);
        return r;
