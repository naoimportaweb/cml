"""VirusTotal v3 (chave gratuita: 4 req/min, 500/dia): reputacao, resolucoes DNS historicas e
subdominios de um dominio, ou dominios que resolveram para um IP. Chave: CML_TX_VIRUSTOTAL_KEY."""

import os, sys, inspect, time;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA, env;
from transform import _osint as o;

API = "https://www.virustotal.com/api/v3/";
LIMITE = 30;


class TransformVirusTotal(Transform):
    def executar(self, entrada, ctx):
        chave = env("CML_TX_VIRUSTOTAL_KEY");
        if not chave:
            raise ErroTransform("falta CML_TX_VIRUSTOTAL_KEY no ~/.env.");
        http = ctx.http();
        cab = {"x-apikey": chave};
        ip = o.ip_da_entrada(entrada);
        r = Resultado();
        if ip:
            base, alvo, gui = API + "ip_addresses/" + ip, ip, "https://www.virustotal.com/gui/ip-address/" + ip;
        else:
            alvo = o.exigir(o.dominio_da_entrada(entrada), "um domínio ou IP", entrada);
            base, gui = API + "domains/" + alvo, "https://www.virustotal.com/gui/domain/" + alvo;
        ref = ctx.ref("VirusTotal: " + alvo, gui);

        st = (http.json(base, headers=cab).get("data", {}).get("attributes", {}).get("last_analysis_stats")) or {};
        if st:
            r.aviso("VirusTotal: %s malicioso(s), %s suspeito(s) de %s motores." % (st.get("malicious", 0), st.get("suspicious", 0), sum(st.values())));

        if ip:
            for x in http.json(base + "/resolutions", params={"limit": LIMITE}, headers=cab).get("data") or []:
                h = str((x.get("attributes") or {}).get("host_name") or "").lower();
                if o.RE_DOMINIO.match(h):
                    r.entidade(o.nome_chave("dom", h), h, etype="other", sub_etype="domínio", description="Domínio que já resolveu para " + ip + ".", referencias=[ref]);
                    quando = (x.get("attributes") or {}).get("date");
                    r.vinculo(o.nome_chave("dom", h), ENTRADA, "já resolveu para",
                              start_date=time.strftime("%Y-%m-%d", time.gmtime(quando)) if isinstance(quando, int) else None, referencias=[ref]);
        else:
            for x in http.json(base + "/resolutions", params={"limit": LIMITE}, headers=cab).get("data") or []:
                a = str((x.get("attributes") or {}).get("ip_address") or "");
                if o.ip_de_texto(a):
                    r.entidade("ip_" + a, a, etype="other", sub_etype="ip", description="IP que " + alvo + " já resolveu (VirusTotal).", referencias=[ref]);
                    r.vinculo(ENTRADA, "ip_" + a, "já resolveu para", referencias=[ref]);
            for x in http.json(base + "/subdomains", params={"limit": LIMITE}, headers=cab).get("data") or []:
                h = str(x.get("id") or "").lower();
                if o.RE_DOMINIO.match(h):
                    r.entidade(o.nome_chave("sub", h), h, etype="other", sub_etype="subdomínio", description="Subdomínio de " + alvo + " (VirusTotal).", referencias=[ref]);
                    r.vinculo(ENTRADA, o.nome_chave("sub", h), "tem subdomínio", referencias=[ref]);
        return r;
