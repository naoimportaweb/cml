"""RIPEstat: para um IP, o prefixo anunciado, o ASN e o contato de abuso; para um ASN, os prefixos
anunciados e os vizinhos BGP. (O BGPView, outra opcao comum, esta fora do ar.)"""

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA;
from transform import _osint as o;

API = "https://stat.ripe.net/data/%s/data.json";
MAX_PREFIXOS = 30;
MAX_VIZINHOS = 30;


class TransformRipestat(Transform):
    def executar(self, entrada, ctx):
        http = ctx.http();
        r = Resultado();
        ip = o.ip_da_entrada(entrada);
        asn = None if ip else o.asn_da_entrada(entrada);
        if not ip and not asn:
            raise ErroTransform("a entidade '%s' não parece ser um IP nem um ASN (ex.: AS15169)." % o.corta(entrada.get("text_label"), 60));

        if ip:
            if not o.ip_publico(ip):
                raise ErroTransform("IP privado/reservado: não há o que consultar.");
            d = http.json(API % "prefix-overview", params={"resource": ip}).get("data") or {};
            ref = ctx.ref("RIPEstat: " + ip, "https://stat.ripe.net/" + ip);
            pref = d.get("resource");
            if pref:
                r.entidade("prefixo", pref, etype="other", sub_etype="prefixo", description="Prefixo que contém o IP " + ip + ".", referencias=[ref]);
                r.vinculo(ENTRADA, "prefixo", "pertence ao prefixo", referencias=[ref]);
            for a in (d.get("asns") or [])[:3]:
                c = "asn_%s" % a.get("asn");
                r.entidade(c, "AS%s – %s" % (a.get("asn"), a.get("holder", "")), etype="other", sub_etype="asn",
                           description="Sistema autônomo que anuncia o prefixo.", referencias=[ref]);
                r.vinculo(ENTRADA, c, "é anunciado pelo", referencias=[ref]);
            try:
                ab = http.json(API % "abuse-contact-finder", params={"resource": ip}).get("data") or {};
                for m in (ab.get("abuse_contacts") or [])[:2]:
                    r.entidade("em_" + m.lower(), m.lower(), etype="other", sub_etype="e-mail", description="Contato de abuso do bloco (RIPEstat).", referencias=[ref]);
                    r.vinculo(ENTRADA, "em_" + m.lower(), "tem contato de abuso", referencias=[ref]);
            except ErroTransform:
                pass;       # contato de abuso e acessorio
            return r;

        ref = ctx.ref("RIPEstat: AS%d" % asn, "https://stat.ripe.net/AS%d" % asn);
        for p in (http.json(API % "announced-prefixes", params={"resource": "AS%d" % asn}).get("data", {}).get("prefixes") or [])[:MAX_PREFIXOS]:
            c = "pref_" + p["prefix"];
            r.entidade(c, p["prefix"], etype="other", sub_etype="prefixo", description="Prefixo anunciado pelo AS%d." % asn, referencias=[ref]);
            r.vinculo(ENTRADA, c, "anuncia", referencias=[ref]);
        viz = http.json(API % "asn-neighbours", params={"resource": "AS%d" % asn}).get("data", {}).get("neighbours") or [];
        for n in sorted(viz, key=lambda x: -x.get("power", 0))[:MAX_VIZINHOS]:
            c = "asn_%s" % n.get("asn");
            r.entidade(c, "AS%s" % n.get("asn"), etype="other", sub_etype="asn",
                       description="Vizinho BGP do AS%d (%s)." % (asn, n.get("type", "?")), referencias=[ref]);
            r.vinculo(ENTRADA, c, "é vizinho BGP de", referencias=[ref]);
        return r;
