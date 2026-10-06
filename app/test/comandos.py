#!/usr/bin/env python3
# Teste do desfazer/refazer do mapa de vinculos (SPEC.md §3.3). Mapa EM MEMORIA, sem servidor.
#
# O que o instantaneo promete, e que o teste cobra:
#   - mover, criar, apagar, incorporar e aplicar-em-lote desfazem e refazem;
#   - um lote inteiro sai com UM desfazer, nao com trinta;
#   - os objetos sao os MESMOS depois de desfazer (quem guardou referencia nao fica com lixo);
#   - a propria lista mapa.elements continua sendo o mesmo objeto;
#   - operacao que nao mudou nada nao empilha passo;
#   - o incorporate, que reponta ponta de vinculo, volta ao que era.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/comandos.py

import os, sys, inspect, tempfile;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
os.environ["HOME"] = tempfile.mkdtemp(prefix="cml_undo_");

from PySide6.QtWidgets import QApplication;

from classlib.relationship.maprelationship import MapRelationship;
from classlib.relationship.comandos import Operacao, tirar_instantaneo, mudou;

FALHAS = [];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def montar():
    mapa = MapRelationship();
    mapa.name = "Desfazer";
    zeca = mapa.addEntity("person", 100, 100, text="Zeca");
    ana = mapa.addEntity("person", 300, 100, text="Ana");
    org = mapa.addEntity("organization", 500, 300, text="Empresa X");
    vinculo = mapa.addEntity("link", 250, 200, text="dirige");
    vinculo.addFrom(zeca);
    vinculo.addTo(org);
    mapa.desfazer.clear();   # a montagem nao conta como historico
    return mapa, zeca, ana, org, vinculo;


def main():
    QApplication(sys.argv);

    print("mover");
    mapa, zeca, ana, org, vinculo = montar();
    with Operacao(mapa, "Mover caixa"):
        zeca.setX(900); zeca.setY(800);
    confere(mapa.desfazer.count() == 1, "empilhou 1 passo");
    confere(mapa.desfazer.undoText() == "Mover caixa", "o passo sabe dizer o que e: %s" % mapa.desfazer.undoText());
    mapa.desfazer.undo();
    confere(zeca.x == 100 and zeca.y == 100, "desfez a posicao (%s,%s)" % (zeca.x, zeca.y));
    mapa.desfazer.redo();
    confere(zeca.x == 900 and zeca.y == 800, "refez a posicao (%s,%s)" % (zeca.x, zeca.y));

    print("\ncriar");
    mapa, zeca, ana, org, vinculo = montar();
    antes = len(mapa.elements);
    with Operacao(mapa, "Criar caixa"):
        nova = mapa.addEntity("other", 50, 50, text="Contrato");
    confere(len(mapa.elements) == antes + 1, "entrou no mapa");
    mapa.desfazer.undo();
    confere(len(mapa.elements) == antes and nova not in mapa.elements, "desfazer tirou a caixa nova");
    mapa.desfazer.redo();
    confere(mapa.elements[-1] is nova, "refazer trouxe O MESMO objeto de volta");

    print("\napagar");
    mapa, zeca, ana, org, vinculo = montar();
    posicao = mapa.elements.index(ana);
    with Operacao(mapa, "Apagar caixa"):
        mapa.delEntity(ana);
    confere(ana not in mapa.elements, "saiu do mapa");
    mapa.desfazer.undo();
    confere(ana in mapa.elements, "desfazer trouxe de volta");
    confere(mapa.elements.index(ana) == posicao, "voltou na MESMA posicao da lista (ordem de desenho)");

    print("\nlote: um transform inteiro = um desfazer");
    mapa, zeca, ana, org, vinculo = montar();
    antes = len(mapa.elements);
    with Operacao(mapa, "Aplicar transform"):
        for i in range(12):
            caixa = mapa.addEntity("other", 10 * i, 600, text="Achado %d" % i);
            elo = mapa.addEntity("link", 10 * i, 650, text="aponta");
            elo.addFrom(zeca); elo.addTo(caixa);
    confere(len(mapa.elements) == antes + 24, "entraram 24 elements");
    confere(mapa.desfazer.count() == 1, "mas empilhou UM passo so (%d)" % mapa.desfazer.count());
    mapa.desfazer.undo();
    confere(len(mapa.elements) == antes, "um desfazer limpou o lote inteiro");

    print("\nincorporar (reponta ponta de vinculo)");
    mapa, zeca, ana, org, vinculo = montar();
    # A assercao tem de guardar PARA ONDE a ponta apontava, nao a lista de pontas: o
    # incorporate muta o LinkEntity no lugar, entao guardar a lista (os mesmos objetos) e
    # comparar depois da sempre igual -- foi assim que este teste passou verde escondendo o
    # defeito, ate uma revisao perceber.
    alvos_antes = [p.entity for p in vinculo.from_entity];
    confere(alvos_antes == [zeca], "antes, a ponta aponta para a origem");
    with Operacao(mapa, "Incorporar"):
        mapa.incorporate(ana, zeca);    # destino=ana, origem=zeca
    confere(zeca not in mapa.elements, "a origem saiu do mapa");
    confere([p.entity for p in vinculo.from_entity] == [ana], "o vinculo passou a apontar para o destino");
    mapa.desfazer.undo();
    confere(zeca in mapa.elements, "desfazer trouxe a origem de volta");
    confere([p.entity for p in vinculo.from_entity] == [zeca],
            "e a PONTA voltou a apontar para a origem (não ficou órfã)");
    mapa.desfazer.redo();
    confere([p.entity for p in vinculo.from_entity] == [ana], "refazer reaponta para o destino");

    print("\nnao empilha o que nao mudou");
    mapa, zeca, ana, org, vinculo = montar();
    with Operacao(mapa, "Nada"):
        pass;
    confere(mapa.desfazer.count() == 0, "operacao sem mudanca nao vira passo");
    with Operacao(mapa, "Abrir dialogo e cancelar"):
        zeca.entity.text = "Zeca Silva";   # edicao DENTRO do objeto: fora do escopo do instantaneo
    confere(mapa.desfazer.count() == 0, "edicao de conteudo nao empilha (tem Cancelar no dialogo)");

    print("\nidentidade preservada");
    mapa, zeca, ana, org, vinculo = montar();
    lista_original = mapa.elements;
    with Operacao(mapa, "Apagar caixa"):
        mapa.delEntity(ana);
    mapa.desfazer.undo();
    confere(mapa.elements is lista_original, "mapa.elements continua sendo o MESMO objeto lista");
    confere([e for e in mapa.elements if e is ana], "a caixa de volta e o mesmo objeto");

    print("\nerro no meio nao empilha passo pela metade");
    mapa, zeca, ana, org, vinculo = montar();
    try:
        with Operacao(mapa, "Vai falhar"):
            mapa.addEntity("other", 1, 1, text="meio");
            raise RuntimeError("estourou");
    except RuntimeError:
        pass;
    confere(mapa.desfazer.count() == 0, "excecao no meio da operacao nao deixa passo na pilha");

    print("\nlimite da pilha");
    mapa, zeca, ana, org, vinculo = montar();
    from classlib.relationship.comandos import LIMITE_PILHA;
    for i in range(LIMITE_PILHA + 20):
        with Operacao(mapa, "Mover caixa"):
            zeca.setX(100 + i);
    confere(mapa.desfazer.count() <= LIMITE_PILHA, "pilha nao cresce sem fim (%d <= %d)"
            % (mapa.desfazer.count(), LIMITE_PILHA));

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
