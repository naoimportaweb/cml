"""Transparencia de certificados: subdominios de um dominio a partir dos certificados emitidos.
crt.sh e instavel (502 intermitente) — tenta 3 vezes e cai para o Cert Spotter."""

import os, sys, inspect, json;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA;
from transform import _osint as o;

MAX_SUBDOMINIOS = 150;


class TransformCrtsh(Transform):
    def executar(self, entrada, ctx):
        dom = o.exigir(o.dominio_da_entrada(entrada), "um domínio", entrada);
        http = ctx.http();
        r = Resultado();
        nomes = {};     # nome -> ultimo not_before
        fonte, url_fonte = "crt.sh", "https://crt.sh/?q=%25." + dom;
        try:
            def pedir():
                resp = http.get("https://crt.sh/", params={"q": "%." + dom, "output": "json"}, timeout=40);
                try:
                    return json.loads(resp.content.decode("utf-8", errors="replace"));
                except ValueError:
                    raise ErroTransform("crt.sh devolveu resposta inválida");
            for cert in o.com_tentativas(pedir, tentativas=3):
                for n in str(cert.get("name_value") or "").split("\n"):
                    nomes[n.strip().lower()] = cert.get("not_before");
        except ErroTransform as e:
            if "cancelado" in str(e):
                raise;
            r.aviso("crt.sh indisponível (%s); usado o Cert Spotter." % e);
            fonte, url_fonte = "Cert Spotter", "https://sslmate.com/ct_search_api/";
            dados = http.json("https://api.certspotter.com/v1/issuances",
                              params={"domain": dom, "include_subdomains": "true", "expand": "dns_names"});
            for cert in dados:
                for n in cert.get("dns_names") or []:
                    nomes[str(n).strip().lower()] = cert.get("not_before");

        ref = ctx.ref("Certificados públicos de " + dom + " (" + fonte + ")", url_fonte);
        usados = 0;
        for n in sorted(nomes):
            n = n[2:] if n.startswith("*.") else n;
            if n == dom or not n.endswith("." + dom) or not o.RE_DOMINIO.match(n):
                continue;
            chave = o.nome_chave("sub", n);
            if any(e["chave"] == chave for e in r.entidades):
                continue;
            if usados >= MAX_SUBDOMINIOS:
                r.aviso("Cortado em %d subdomínios; há mais nos certificados." % MAX_SUBDOMINIOS);
                break;
            r.entidade(chave, n, etype="other", sub_etype="subdomínio",
                       description="Subdomínio de " + dom + " visto em certificado TLS público.", referencias=[ref]);
            r.vinculo(ENTRADA, chave, "tem subdomínio", referencias=[ref]);
            usados += 1;
        if usados == 0:
            r.aviso("Nenhum subdomínio encontrado nos certificados.");
        return r;
