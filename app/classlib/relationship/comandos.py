# Desfazer/refazer do mapa de vinculos (SPEC.md §3.3).
#
# Por que INSTANTANEO e nao um comando por operacao: o mapa e mexido em cinco lugares bem
# diferentes (arrastar no canvas, criar pelo duplo clique, apagar por dois dialogos,
# incorporar, e o aplicador de transform). Escrever o inverso de cada um daria cinco chances
# de errar, e o inverso do incorporate -- que reponta ponta de vinculo -- e o pior deles.
# Guardar o ANTES e o DEPOIS resolve os cinco com um mecanismo so.
#
# O instantaneo guarda ESTRUTURA e POSICAO, pela IDENTIDADE dos objetos (nada e clonado):
#   - quais elements estao no mapa, e em que ordem (ordem = quem desenha por cima);
#   - o x/y de cada um;
#   - as duas listas de ponta de cada vinculo (e o que o incorporate reponta).
# Os objetos continuam os mesmos, entao dialogo aberto e referencia guardada por ai nao viram
# ponteiro para lixo depois de um desfazer.
#
# O que ele NAO desfaz, de propósito: edicao DENTRO de um objeto (nome, descricao, referencia,
# data). Isso ja tem Cancelar no proprio dialogo, e guardar aqui exigiria clonar entidade
# inteira a cada clique.

from PySide6.QtGui import QUndoCommand;

LIMITE_PILHA = 100;


def tirar_instantaneo(mapa):
    pos = {};
    pontas = {};
    for elemento in mapa.elements:
        pos[elemento] = (elemento.x, elemento.y);
        if elemento.entity.etype == "link":
            pontas[elemento] = (list(elemento.to_entity), list(elemento.from_entity));
    return {"ordem": list(mapa.elements), "pos": pos, "pontas": pontas};


def aplicar_instantaneo(mapa, instantaneo):
    # Reposicao NO LUGAR (fatia), para quem guardou referencia a mapa.elements continuar vendo
    # a mesma lista em vez de uma lista velha e orfa.
    mapa.elements[:] = instantaneo["ordem"];
    for elemento, (x, y) in instantaneo["pos"].items():
        elemento.x = x;
        elemento.y = y;
    for vinculo, (para, de) in instantaneo["pontas"].items():
        vinculo.to_entity[:] = para;
        vinculo.from_entity[:] = de;


def mudou(antes, depois):
    if len(antes["ordem"]) != len(depois["ordem"]):
        return True;
    for i in range(len(antes["ordem"])):
        if antes["ordem"][i] is not depois["ordem"][i]:
            return True;
    if antes["pos"] != depois["pos"]:
        return True;
    for vinculo, (para, de) in antes["pontas"].items():
        atual = depois["pontas"].get(vinculo);
        if atual == None or atual[0] != para or atual[1] != de:
            return True;
    return False;


class ComandoMapa(QUndoCommand):
    """Um passo da pilha: leva o mapa de um instantaneo ao outro."""

    def __init__(self, mapa, antes, depois, texto):
        super().__init__(texto);
        self.mapa = mapa;
        self.antes = antes;
        self.depois = depois;

    def undo(self):
        aplicar_instantaneo(self.mapa, self.antes);

    def redo(self):
        # O QUndoStack chama redo() ao empilhar. Como o DEPOIS ja e o estado atual nessa hora,
        # reaplicar e inofensivo -- e e o que faz o refazer funcionar depois.
        aplicar_instantaneo(self.mapa, self.depois);


class Operacao:
    """Context manager: tira o antes, deixa o chamador mexer, tira o depois e empilha se algo
    mudou. Uso:

        with Operacao(mapa, "Apagar caixa"):
            mapa.delEntity(caixa);
    """

    def __init__(self, mapa, texto):
        self.mapa = mapa;
        self.texto = texto;
        self.antes = None;

    def __enter__(self):
        self.antes = tirar_instantaneo(self.mapa);
        return self;

    def __exit__(self, tipo, valor, traceback):
        if tipo != None:
            return False;   # deu erro no meio: nao empilha passo nenhum
        pilha = getattr(self.mapa, "desfazer", None);
        if pilha == None:
            return False;
        depois = tirar_instantaneo(self.mapa);
        if mudou(self.antes, depois):
            pilha.push(ComandoMapa(self.mapa, self.antes, depois, self.texto));
        return False;
