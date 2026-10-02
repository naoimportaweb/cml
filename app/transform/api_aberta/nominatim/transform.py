"""Nominatim (OpenStreetMap): geocodifica o nome/endereco da entidade e propoe o lugar, a cidade
e o pais. Politica de uso: 1 req/s e UA identificavel — o cache de 30 dias e o ttl cuidam disso."""

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA;
from transform import _osint as o;

MAX_LUGARES = 3;


class TransformNominatim(Transform):
    def executar(self, entrada, ctx):
        q = str(entrada.get("text_label") or "").strip();
        if len(q) < 3:
            raise ErroTransform("nome curto demais para geocodificar.");
        lista = ctx.http().json("https://nominatim.openstreetmap.org/search",
                                params={"q": q, "format": "jsonv2", "limit": MAX_LUGARES, "addressdetails": 1});
        r = Resultado();
        for i, x in enumerate(lista[:MAX_LUGARES]):
            ref = ctx.ref("OpenStreetMap: " + o.corta(x.get("display_name"), 80),
                          "https://www.openstreetmap.org/%s/%s" % (x.get("osm_type"), x.get("osm_id")));
            c = "lugar_%d" % i;
            r.entidade(c, o.corta(x.get("display_name"), 240), etype="other", sub_etype="local",
                       description="%s (%s). Coordenadas: %s, %s." % (x.get("category", "?"), x.get("type", "?"), x.get("lat"), x.get("lon")),
                       referencias=[ref]);
            r.vinculo(ENTRADA, c, "localiza-se em" if i == 0 else "pode se localizar em", referencias=[ref]);
            if i == 0:
                ad = x.get("address") or {};
                cidade = ad.get("city") or ad.get("town") or ad.get("municipality") or ad.get("village");
                if cidade:
                    r.entidade("cidade", "%s, %s" % (cidade, ad.get("state", ad.get("country", ""))), etype="other", sub_etype="local",
                               description="Município do lugar geocodificado.", referencias=[ref]);
                    r.vinculo(c, "cidade", "fica em", referencias=[ref]);
                if ad.get("country"):
                    r.entidade("pais", ad["country"], etype="other", sub_etype="país", description="País do lugar geocodificado.", referencias=[ref]);
                    r.vinculo("cidade" if cidade else c, "pais", "fica em", referencias=[ref]);
        if not r.entidades:
            r.aviso("O OpenStreetMap não achou \"%s\"." % q);
        elif len(r.entidades) > 1:
            r.aviso("Mais de um lugar possível: confira qual é o certo antes de aceitar.");
        return r;
