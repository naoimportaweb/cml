"""Gravatar: o hash MD5 do e-mail abre o perfil publico que a pessoa escolheu expor (nome de
exibicao, contas verificadas, sites, local). So o hash sai da maquina, nunca o e-mail."""

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA;
from transform import _osint as o;

MAX_CONTAS = 15;


class TransformGravatar(Transform):
    def executar(self, entrada, ctx):
        email = o.exigir(o.email_da_entrada(entrada), "um e-mail", entrada);
        url = "https://gravatar.com/%s.json" % o.md5_hex(email);
        r = Resultado();
        try:
            d = ctx.http().json(url);
        except ErroTransform as e:
            if "HTTP 404" in str(e):
                r.aviso("Esse e-mail não tem perfil público no Gravatar.");
                return r;
            raise;
        ref = ctx.ref("Perfil Gravatar (hash MD5 do e-mail)", url);
        ent = (d.get("entry") or [{}])[0];
        nome = ent.get("displayName") or ent.get("preferredUsername");
        if nome:
            r.entidade("titular", nome, etype="person", description=o.corta(ent.get("aboutMe") or "Titular do perfil Gravatar deste e-mail.", 300), referencias=[ref]);
            r.vinculo("titular", ENTRADA, "é o titular de", referencias=[ref]);
        alvo = "titular" if nome else ENTRADA;
        for i, a in enumerate((ent.get("accounts") or [])[:MAX_CONTAS]):
            if not a.get("url"):
                continue;
            c = "conta_%d" % i;
            r.entidade(c, "%s: %s" % (a.get("name") or a.get("shortname") or "conta", a.get("username") or a.get("display") or a["url"]),
                       etype="other", sub_etype="perfil", description="Conta vinculada no Gravatar" + (" (verificada)." if a.get("verified") else "."),
                       referencias=[ctx.ref("Conta vinculada ao Gravatar", a["url"])]);
            r.vinculo(alvo, c, "tem conta", referencias=[ref]);
        for i, u in enumerate((ent.get("urls") or [])[:5]):
            host = o.host_de_texto(u.get("value"));
            if host:
                c = "site_%d" % i;
                r.entidade(c, host, etype="other", sub_etype="domínio", description="Site listado no perfil do Gravatar.", referencias=[ref]);
                r.vinculo(alvo, c, "lista o site", referencias=[ref]);
        loc = ent.get("currentLocation");
        if loc:
            r.entidade("local", loc, etype="other", sub_etype="local", description="Localização declarada (texto livre) no Gravatar.", referencias=[ref]);
            r.vinculo(alvo, "local", "declara estar em", referencias=[ref]);
        return r;
