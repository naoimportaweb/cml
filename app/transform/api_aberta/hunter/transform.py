"""Hunter.io domain-search (chave gratuita: 25 buscas/mes): e-mails publicos do dominio e, quando
conhecidos, nome e cargo. Chave: CML_TX_HUNTER_KEY. A chave vai na query-string (exigencia do
Hunter); a URL de referencia criada para o mapa NAO leva a chave."""

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA, env;
from transform import _osint as o;

MAX_EMAILS = 30;


class TransformHunter(Transform):
    def executar(self, entrada, ctx):
        chave = env("CML_TX_HUNTER_KEY");
        if not chave:
            raise ErroTransform("falta CML_TX_HUNTER_KEY no ~/.env.");
        dom = o.exigir(o.dominio_da_entrada(entrada), "um domínio", entrada);
        d = ctx.http().json("https://api.hunter.io/v2/domain-search", params={"domain": dom, "limit": MAX_EMAILS, "api_key": chave}).get("data") or {};
        ref = ctx.ref("Hunter.io: " + dom, "https://hunter.io/search/" + dom);
        r = Resultado();
        if d.get("organization"):
            r.aviso("Organização segundo o Hunter: " + str(d["organization"]));
        for i, e in enumerate((d.get("emails") or [])[:MAX_EMAILS]):
            mail = str(e.get("value") or "").lower();
            if not mail:
                continue;
            c = "em_%d" % i;
            r.entidade(c, mail, etype="other", sub_etype="e-mail",
                       description="E-mail público de %s (confiança %s%%, tipo %s)." % (dom, e.get("confidence", "?"), e.get("type", "?")), referencias=[ref]);
            r.vinculo(ENTRADA, c, "usa o e-mail", referencias=[ref]);
            nome = " ".join(x for x in (e.get("first_name"), e.get("last_name")) if x);
            if nome:
                p = "pe_%d" % i;
                r.entidade(p, nome, etype="person", description=o.corta("%s em %s." % (e.get("position") or "Cargo não informado", dom), 200), referencias=[ref]);
                r.vinculo(p, c, "usa o e-mail", referencias=[ref]);
        if not r.entidades:
            r.aviso("O Hunter não tem e-mails públicos de %s." % dom);
        return r;
