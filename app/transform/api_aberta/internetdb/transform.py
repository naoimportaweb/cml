"""Shodan InternetDB (gratuito, sem chave): portas abertas, hostnames, CPEs e CVEs de um IP.
Se a entidade for um dominio, resolve (DoH) e consulta ate 3 IPs publicos."""

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA;
from transform import _osint as o;

MAX_IPS = 3;
MAX_PORTAS = 30;
MAX_CVES = 30;


class TransformInternetDB(Transform):
    def executar(self, entrada, ctx):
        http = ctx.http();
        r = Resultado();
        ip = o.ip_da_entrada(entrada);
        if ip:
            ips = [ip];
        else:
            dom = o.exigir(o.dominio_da_entrada(entrada), "um IP ou domínio", entrada);
            d = http.json("https://cloudflare-dns.com/dns-query", params={"name": dom, "type": "A"},
                          headers={"Accept": "application/dns-json"});
            ips = [a["data"] for a in (d.get("Answer") or []) if a.get("type") == 1 and o.ip_publico(a.get("data"))][:MAX_IPS];
            if not ips:
                raise ErroTransform("o domínio %s não resolve para um IP público." % dom);
        if not all(o.ip_publico(i) for i in ips):
            raise ErroTransform("IP privado/reservado: não há o que consultar na internet.");

        for ip in ips:
            url = "https://internetdb.shodan.io/" + ip;
            try:
                d = http.json(url);
            except ErroTransform as e:
                if "HTTP 404" in str(e):
                    r.aviso("%s: sem dados no InternetDB (nada indexado)." % ip);
                    continue;
                raise;
            ref = ctx.ref("Shodan InternetDB " + ip, url);
            cabeca = ENTRADA;
            if len(ips) > 1 or not o.ip_da_entrada(entrada):
                cabeca = "ip_" + ip;
                r.entidade(cabeca, ip, etype="other", sub_etype="ip", description="IP resolvido a partir do domínio.", referencias=[ref]);
                r.vinculo(ENTRADA, cabeca, "resolve para", referencias=[ref]);
            for h in (d.get("hostnames") or [])[:MAX_PORTAS]:
                h = str(h).lower();
                if o.RE_DOMINIO.match(h):
                    r.entidade(o.nome_chave("dom", h), h, etype="other", sub_etype="domínio",
                               description="Hostname associado ao IP " + ip + ".", referencias=[ref]);
                    r.vinculo(cabeca, o.nome_chave("dom", h), "tem hostname", referencias=[ref]);
            for p in (d.get("ports") or [])[:MAX_PORTAS]:
                chave = "porta_%s_%s" % (ip, p);
                r.entidade(chave, "%s:%s" % (ip, p), etype="other", sub_etype="porta",
                           description="Porta %s aberta em %s (visto pelo Shodan)." % (p, ip), referencias=[ref]);
                r.vinculo(cabeca, chave, "expõe porta", referencias=[ref]);
            for cve in (d.get("vulns") or [])[:MAX_CVES]:
                chave = "cve_" + str(cve).lower();
                r.entidade(chave, str(cve), etype="other", sub_etype="vulnerabilidade",
                           description="CVE associada ao IP " + ip + " pelo Shodan (inferida de versão; confirme).",
                           referencias=[ctx.ref(str(cve) + " (NVD)", "https://nvd.nist.gov/vuln/detail/" + str(cve))]);
                r.vinculo(cabeca, chave, "pode ser vulnerável a", referencias=[ref]);
            if d.get("tags"):
                r.aviso("%s: tags do Shodan: %s" % (ip, ", ".join(d["tags"])));
        return r;
