"""Abre o site oficial da entidade no craudiowebot (navegador real, serve paginas que dependem
de JS) e lista os dominios externos para os quais ele aponta. A rota de rede e a do proprio
browser do craudiowebot, nao a do CML."""

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from urllib.parse import urlparse;
from transform.nucleo import Transform, Resultado, ErroTransform;

MAX_DOMINIOS = 30;

class TransformLinksExternos(Transform):
    def executar(self, entrada, ctx):
        from bs4 import BeautifulSoup;
        url = str(entrada.get("default_url") or "").strip();
        if not url.lower().startswith(("http://", "https://")):
            raise ErroTransform("a entidade não tem site oficial (default_url) http(s)");
        base = (urlparse(url).hostname or "").lower();
        html = ctx.craudio().html(url);
        sopa = BeautifulSoup(html, "html.parser");
        contagem = {};
        for a in sopa.find_all("a", href=True):
            h = a["href"].strip();
            if not h.lower().startswith(("http://", "https://")):
                continue;
            dom = (urlparse(h).hostname or "").lower();
            if dom == "" or dom == base or dom.endswith("." + base) or base.endswith("." + dom):
                continue;
            contagem[dom] = contagem.get(dom, 0) + 1;
        r = Resultado();
        for i, (dom, n) in enumerate(sorted(contagem.items(), key=lambda kv: -kv[1])[:MAX_DOMINIOS]):
            chave = "d" + str(i);
            r.entidade(chave, dom, "other", sub_etype="domínio",
                       referencias=[ctx.ref("Links de " + base, url, "%d link(s) para este domínio." % n)]);
            r.vinculo("ENTRADA", chave, "aponta para");
        if not r.entidades:
            r.aviso("Nenhum link externo encontrado.");
        return r;
