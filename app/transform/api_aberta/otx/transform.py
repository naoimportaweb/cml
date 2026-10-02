"""AlienVault OTX: pulsos (campanhas/relatorios de ameaca) que citam o dominio ou IP, com
adversario e familias de malware. Anonimo funciona; CML_TX_OTX_KEY (opcional) libera tambem o
DNS passivo, que o OTX limita a quem esta autenticado."""

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA, env;
from transform import _osint as o;

MAX_PULSOS = 15;
MAX_PASSIVO = 30;


class TransformOtx(Transform):
    def executar(self, entrada, ctx):
        ip = o.ip_da_entrada(entrada);
        if ip:
            tipo, alvo = ("IPv6" if ":" in ip else "IPv4"), ip;
        else:
            tipo, alvo = "domain", o.exigir(o.dominio_da_entrada(entrada), "um domínio ou IP", entrada);
        chave = env("CML_TX_OTX_KEY");
        cab = {"X-OTX-API-KEY": chave} if chave else None;
        http = ctx.http();
        base = "https://otx.alienvault.com/api/v1/indicators/%s/%s/" % (tipo, alvo);
        d = http.json(base + "general", headers=cab);
        ref = ctx.ref("AlienVault OTX: " + alvo, "https://otx.alienvault.com/indicator/%s/%s" % ("ip" if tipo != "domain" else "domain", alvo));
        r = Resultado();

        info = d.get("pulse_info") or {};
        total = info.get("count", 0);
        for p in (info.get("pulses") or [])[:MAX_PULSOS]:
            c = "pulso_" + str(p.get("id"));
            link = "https://otx.alienvault.com/pulse/" + str(p.get("id"));
            pref = ctx.ref("Pulso OTX: " + o.corta(p.get("name"), 80), link);
            r.entidade(c, o.corta(p.get("name"), 200), etype="other", sub_etype="campanha de ameaça",
                       description=o.corta(p.get("description") or ("Pulso do OTX, tags: " + ", ".join((p.get("tags") or [])[:8])), 400),
                       referencias=[pref]);
            r.vinculo(c, ENTRADA, "cita", start_date=o.data_iso(p.get("created")), referencias=[pref]);
            if p.get("adversary"):
                a = o.nome_chave("adv", p["adversary"]);
                if not any(e["chave"] == a for e in r.entidades):
                    r.entidade(a, p["adversary"], etype="organization", sub_etype="ator de ameaça",
                               description="Adversário atribuído em pulso do OTX.", referencias=[pref]);
                r.vinculo(c, a, "atribuído a", referencias=[pref]);
            for fam in (p.get("malware_families") or [])[:3]:
                nome = fam.get("display_name") if isinstance(fam, dict) else str(fam);
                if not nome:
                    continue;
                m = o.nome_chave("mw", nome);
                if not any(e["chave"] == m for e in r.entidades):
                    r.entidade(m, nome, etype="other", sub_etype="malware", description="Família de malware citada em pulso do OTX.", referencias=[pref]);
                r.vinculo(c, m, "envolve malware", referencias=[pref]);
        if total > MAX_PULSOS:
            r.aviso("%d pulsos citam %s; mostrados os %d mais recentes." % (total, alvo, MAX_PULSOS));
        if total == 0:
            r.aviso("Nenhum pulso do OTX cita %s." % alvo);

        if chave:
            try:
                pdns = http.json(base + "passive_dns", headers=cab);
                for x in (pdns.get("passive_dns") or [])[:MAX_PASSIVO]:
                    h = str(x.get("hostname") if tipo != "domain" else x.get("address")).strip().lower();
                    if tipo == "domain" and o.ip_de_texto(h):
                        r.entidade("ip_" + h, h, etype="other", sub_etype="ip", description="Resolução histórica (DNS passivo do OTX).", referencias=[ref]);
                        r.vinculo(ENTRADA, "ip_" + h, "já resolveu para", start_date=o.data_iso(x.get("first")), end_date=o.data_iso(x.get("last")), referencias=[ref]);
                    elif tipo != "domain" and o.RE_DOMINIO.match(h):
                        r.entidade(o.nome_chave("dom", h), h, etype="other", sub_etype="domínio", description="Domínio que já resolveu para " + alvo + ".", referencias=[ref]);
                        r.vinculo(o.nome_chave("dom", h), ENTRADA, "já resolveu para", start_date=o.data_iso(x.get("first")), end_date=o.data_iso(x.get("last")), referencias=[ref]);
            except ErroTransform as e:
                r.aviso("DNS passivo do OTX indisponível: " + str(e));
        return r;
