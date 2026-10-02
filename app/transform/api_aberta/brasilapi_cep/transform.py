"""CEP -> logradouro, bairro, cidade e coordenadas (BrasilAPI v2). O CEP vem do nome, do
apelido ou da descricao da entidade."""

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA;
from transform import _osint as o;


class TransformCep(Transform):
    def executar(self, entrada, ctx):
        cep = o.exigir(o.cep_da_entrada(entrada), "um CEP", entrada);
        url = "https://brasilapi.com.br/api/cep/v2/" + cep;
        d = ctx.http().json(url);
        ref = ctx.ref("CEP %s-%s (BrasilAPI)" % (cep[:5], cep[5:]), url);
        r = Resultado();
        rua = ", ".join(x for x in (d.get("street"), d.get("neighborhood")) if x);
        nome = "%s – %s/%s" % (rua or "CEP " + cep, d.get("city", ""), d.get("state", ""));
        c = (d.get("location") or {}).get("coordinates") or {};
        desc = "CEP %s-%s." % (cep[:5], cep[5:]);
        if c.get("latitude"):
            desc += " Coordenadas: %s, %s." % (c.get("latitude"), c.get("longitude"));
        r.entidade("local", nome, etype="other", sub_etype="local", description=desc, referencias=[ref]);
        r.vinculo(ENTRADA, "local", "está em", referencias=[ref]);
        if d.get("city"):
            cidade = "%s/%s" % (d["city"], d.get("state", ""));
            r.entidade("cidade", cidade, etype="other", sub_etype="local", description="Município do CEP " + cep + ".", referencias=[ref]);
            r.vinculo("local", "cidade", "fica em", referencias=[ref]);
        return r;
