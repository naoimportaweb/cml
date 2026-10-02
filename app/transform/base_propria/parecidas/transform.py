"""Procura na base do CML entidades cujo nome contem (ou esta contido) no da entrada: possiveis
homonimos e duplicatas. Nao sai da base — nenhuma consulta vaza para fora."""

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, norm;

MAX = 25;

class TransformParecidas(Transform):
    def executar(self, entrada, ctx):
        nome = str(entrada.get("text_label") or "").strip();
        if len(norm(nome)) < 3:
            raise ErroTransform("nome curto demais para procurar semelhantes");
        r = Resultado();
        achadas = ctx.base().buscar("%" + nome.replace("%", "") + "%");
        n = 0;
        for e in achadas:
            if e.get("id") == entrada.get("id"):
                continue;
            if n >= MAX:
                r.aviso("Mostrando só as primeiras %d." % MAX);
                break;
            chave = "b" + str(n);
            exato = norm(e.get("text_label")) == norm(nome);
            r.entidade(chave, e.get("text_label"), e.get("etype") or "other",
                       small_label=e.get("small_label") or "", description=e.get("description") or "",
                       referencias=[ctx.ref("Base do CML", "cml://entity/" + str(e.get("id")), "Já cadastrada na base.")],
                       id_existente=e.get("id"));
            r.vinculo("ENTRADA", chave, "mesmo nome que" if exato else "nome parecido com");
            n += 1;
        if n == 0:
            r.aviso("Nada parecido na base.");
        return r;
