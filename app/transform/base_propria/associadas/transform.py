"""Relacoes globais entidade<->entidade (entity_simple_association, hoje alimentada pelo
import do MISP Galaxy e sem UI). Exige o metodo Entity.associations no servidor."""

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform;

class TransformAssociadas(Transform):
    def executar(self, entrada, ctx):
        if not entrada.get("id"):
            raise ErroTransform("a entidade ainda não existe na base (salve o mapa primeiro)");
        r = Resultado();
        for i, e in enumerate(ctx.base().associadas(entrada["id"])):
            chave = "a" + str(i);
            r.entidade(chave, e.get("text_label"), e.get("etype") or "other",
                       small_label=e.get("small_label") or "", description=e.get("description") or "",
                       referencias=[ctx.ref("Base do CML (associação global)", "cml://entity/" + str(e.get("id")))],
                       id_existente=e.get("id"));
            # A tabela nao tem verbo nem direcao semantica: "associado a" e o que ela diz.
            r.vinculo("ENTRADA", chave, "associado a");
        if not r.entidades:
            r.aviso("Nenhuma associação global para esta entidade.");
        return r;
