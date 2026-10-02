"""RDAP (sucessor do whois, JSON): quem registrou o dominio / quem recebeu o bloco de IP / o ASN.
O rdap.org redireciona ao registro certo (Verisign, ARIN, RIPE, registro.br...)."""

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA;
from transform import _osint as o;

MAX_NS = 10;


def _fn(ent):
    try:
        for campo in ent["vcardArray"][1]:
            if campo[0] == "fn":
                return str(campo[3]).strip();
    except Exception:
        pass;
    return "";


def _email(ent):
    try:
        for campo in ent["vcardArray"][1]:
            if campo[0] == "email":
                return str(campo[3]).strip().lower();
    except Exception:
        pass;
    return "";


def _entidades(dados, achatadas=None):
    achatadas = [] if achatadas == None else achatadas;
    for e in dados.get("entities") or []:
        achatadas.append(e);
        _entidades(e, achatadas);
    return achatadas;


class TransformRdap(Transform):
    def executar(self, entrada, ctx):
        http = ctx.http();
        ip = o.ip_da_entrada(entrada);
        asn = None if ip else o.asn_da_entrada(entrada);
        dom = None if (ip or asn) else o.exigir(o.dominio_da_entrada(entrada), "um domínio, IP ou ASN", entrada);
        if ip:
            alvo, tipo = ip, "ip";
        elif asn:
            alvo, tipo = str(asn), "autnum";
        else:
            alvo, tipo = dom, "domain";
        url = "https://rdap.org/%s/%s" % (tipo, alvo);
        d = o.com_tentativas(lambda: http.json(url, headers={"Accept": "application/rdap+json"}), tentativas=2);
        ref = ctx.ref("RDAP de " + alvo, url);
        r = Resultado();

        # papeis -> (verbo, etype). Registrante/titular costuma vir mascarado (privacidade): so entra o que tem nome.
        papeis = {"registrar": ("registrado por", "organization"), "registrant": ("registrado em nome de", "organization"),
                  "technical": ("tem contato técnico", "other"), "abuse": ("tem contato de abuso", "other")};
        vistos = set();
        for e in _entidades(d):
            nome = _fn(e);
            for p in e.get("roles") or []:
                if p not in papeis:
                    continue;
                verbo, etype = papeis[p];
                if p == "abuse":
                    mail = _email(e);
                    if mail == "" or mail in vistos:
                        continue;
                    vistos.add(mail);
                    r.entidade("em_" + mail, mail, etype="other", sub_etype="e-mail",
                               description="Contato de abuso do registro de " + alvo + ".", referencias=[ref]);
                    r.vinculo(ENTRADA, "em_" + mail, verbo, referencias=[ref]);
                    continue;
                if nome == "" or "redacted" in nome.lower() or "privacy" in nome.lower() or o.norm(nome) in vistos:
                    continue;
                vistos.add(o.norm(nome));
                chave = o.nome_chave("rdap", nome);
                r.entidade(chave, nome, etype=etype, description="Papel '" + p + "' no registro de " + alvo + ".", referencias=[ref]);
                r.vinculo(ENTRADA, chave, verbo, referencias=[ref]);

        if tipo == "domain":
            ini = None;
            for ev in d.get("events") or []:
                if ev.get("eventAction") == "registration":
                    ini = o.data_iso(ev.get("eventDate"));
            for ns in (d.get("nameservers") or [])[:MAX_NS]:
                n = str(ns.get("ldhName") or "").rstrip(".").lower();
                if o.RE_DOMINIO.match(n):
                    r.entidade(o.nome_chave("dom", n), n, etype="other", sub_etype="domínio",
                               description="Servidor de nomes de " + alvo + ".", referencias=[ref]);
                    r.vinculo(ENTRADA, o.nome_chave("dom", n), "usa servidor de nomes", referencias=[ref]);
            if ini:
                r.aviso("Domínio registrado em %s (data do evento 'registration')." % ini);
        elif tipo == "ip":
            rede = d.get("name") or d.get("handle");
            cidrs = [c for c in (d.get("cidr0_cidrs") or [])];
            if rede:
                bloco = "%s/%s" % (cidrs[0].get("v4prefix") or cidrs[0].get("v6prefix"), cidrs[0].get("length")) if cidrs else \
                        "%s – %s" % (d.get("startAddress"), d.get("endAddress"));
                r.entidade("bloco", bloco, etype="other", sub_etype="prefixo",
                           description=o.corta("Bloco '%s' (%s), país %s." % (rede, d.get("handle", ""), d.get("country", "?")), 300),
                           referencias=[ref]);
                r.vinculo(ENTRADA, "bloco", "pertence ao bloco", referencias=[ref]);
        elif tipo == "autnum":
            r.aviso("ASN %s: %s (%s)." % (alvo, d.get("name", "?"), d.get("country", "?")));
        if not r.entidades:
            r.aviso("O registro não expõe entidades públicas (privacidade/GDPR).");
        return r;
