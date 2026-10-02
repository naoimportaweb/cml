"""GDELT DOC 2.0: matérias de imprensa dos ultimos 3 meses que citam o nome da entidade. A data da
matéria vira start_date. O GDELT casa por TEXTO: homonimos entram — por isso o painel Proposta."""

import os, sys, inspect, json;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA;
from transform import _osint as o;

MAX_MATERIAS = 25;


class TransformGdelt(Transform):
    def executar(self, entrada, ctx):
        nome = str(entrada.get("text_label") or "").strip();
        if len(nome) < 4:
            raise ErroTransform("o GDELT exige um nome com pelo menos 4 caracteres.");
        params = {"query": '"%s"' % nome.replace('"', ""), "mode": "artlist", "maxrecords": MAX_MATERIAS,
                  "format": "json", "sort": "datedesc", "timespan": "3months"};
        # O GDELT limita a 1 consulta a cada 5 s por IP: o 429 e comum, entao espera e repete.
        resp = o.com_tentativas(lambda: ctx.http().get("https://api.gdeltproject.org/api/v2/doc/doc", params=params, timeout=40),
                                tentativas=4, pausa=7.0);
        txt = resp.content.decode("utf-8", errors="replace");
        try:
            d = json.loads(txt, strict=False);
        except ValueError:
            raise ErroTransform("GDELT: " + o.corta(txt, 140));       # costuma ser aviso de limite de uso
        r = Resultado();
        vistos = set();
        for a in d.get("articles") or []:
            url, titulo = a.get("url"), o.corta(a.get("title"), 200);
            if not url or titulo == "" or url in vistos:
                continue;
            vistos.add(url);
            c = "mat_%d" % len(vistos);
            ref = ctx.ref(titulo, url);
            r.entidade(c, titulo, etype="other", sub_etype="matéria",
                       description="Matéria de %s (%s)." % (a.get("domain", "?"), a.get("language", "?")), referencias=[ref]);
            r.vinculo(c, ENTRADA, "cita", start_date=o.data_iso(a.get("seendate")), referencias=[ref]);
        if not r.entidades:
            r.aviso("Nenhuma matéria dos últimos 3 meses cita \"%s\" no GDELT." % nome);
        else:
            r.aviso("O GDELT casa por texto: confira se cada matéria é mesmo da entidade (homônimos).");
        return r;
