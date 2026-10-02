"""Resolucao DNS por DNS-over-HTTPS (Cloudflare, com Google de reserva). NUNCA pelo resolvedor
local: sob Tor ele vazaria a consulta — pelo ctx.http() o DNS sai pela mesma rota do resto."""

import os, sys, inspect, re;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA;
from transform import _osint as o;

SERVIDORES = [("https://cloudflare-dns.com/dns-query", "Cloudflare"), ("https://dns.google/resolve", "Google")];
TIPOS = {"A": 1, "AAAA": 28, "CNAME": 5, "MX": 15, "NS": 2, "TXT": 16};
MAX_POR_TIPO = 12;


def consultar(http, nome, tipo):
    ultimo = None;
    for url, _quem in SERVIDORES:
        try:
            d = http.json(url, params={"name": nome, "type": tipo}, headers={"Accept": "application/dns-json"});
            return [a for a in (d.get("Answer") or []) if a.get("type") == TIPOS[tipo]];
        except ErroTransform as e:
            ultimo = e;
    raise ultimo;


class TransformDns(Transform):
    def executar(self, entrada, ctx):
        dom = o.exigir(o.dominio_da_entrada(entrada), "um domínio", entrada);
        http = ctx.http();
        r = Resultado();
        ref = ctx.ref("Consulta DNS (DoH) de " + dom, "https://dns.google/resolve?name=" + dom);
        vistos = set();

        def novo(chave, nome, sub, desc):
            if chave in vistos:
                return chave;
            vistos.add(chave);
            r.entidade(chave, nome, etype="other", sub_etype=sub, description=desc, referencias=[ref]);
            return chave;

        for tipo in ("A", "AAAA"):
            for a in consultar(http, dom, tipo)[:MAX_POR_TIPO]:
                ip = a.get("data", "");
                if o.ip_de_texto(ip):
                    novo("ip_" + ip, ip, "ip", "Endereço IP resolvido para " + dom + ".");
                    r.vinculo(ENTRADA, "ip_" + ip, "resolve para", referencias=[ref]);
        for a in consultar(http, dom, "CNAME")[:MAX_POR_TIPO]:
            alvo = str(a.get("data", "")).rstrip(".").lower();
            if o.RE_DOMINIO.match(alvo):
                novo(o.nome_chave("dom", alvo), alvo, "domínio", "Alvo de CNAME de " + dom + ".");
                r.vinculo(ENTRADA, o.nome_chave("dom", alvo), "é alias de", referencias=[ref]);
        for a in consultar(http, dom, "MX")[:MAX_POR_TIPO]:
            partes = str(a.get("data", "")).split();
            alvo = partes[-1].rstrip(".").lower() if partes else "";
            if o.RE_DOMINIO.match(alvo):
                novo(o.nome_chave("dom", alvo), alvo, "domínio", "Servidor de e-mail (MX) de " + dom + ".");
                r.vinculo(ENTRADA, o.nome_chave("dom", alvo), "recebe e-mail em", referencias=[ref]);
        for a in consultar(http, dom, "NS")[:MAX_POR_TIPO]:
            alvo = str(a.get("data", "")).rstrip(".").lower();
            if o.RE_DOMINIO.match(alvo):
                novo(o.nome_chave("dom", alvo), alvo, "domínio", "Servidor de nomes (NS) de " + dom + ".");
                r.vinculo(ENTRADA, o.nome_chave("dom", alvo), "usa servidor de nomes", referencias=[ref]);
        # SPF: os "include:" dizem quem pode mandar e-mail em nome do dominio.
        for a in consultar(http, dom, "TXT")[:MAX_POR_TIPO]:
            txt = str(a.get("data", "")).strip('"');
            if txt.lower().startswith("v=spf1"):
                for inc in re.findall(r"include:([A-Za-z0-9._-]+)", txt)[:MAX_POR_TIPO]:
                    inc = inc.lower();
                    if o.RE_DOMINIO.match(inc):
                        novo(o.nome_chave("dom", inc), inc, "domínio", "Autorizado no SPF de " + dom + ".");
                        r.vinculo(ENTRADA, o.nome_chave("dom", inc), "autoriza e-mail via SPF", referencias=[ref]);
        if not r.entidades:
            r.aviso("Nenhum registro encontrado (domínio inexistente ou sem registros).");
        return r;
