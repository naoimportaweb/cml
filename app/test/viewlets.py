#!/usr/bin/env python3
# Teste dos viewlets (cor/tamanho por propriedade) e do ocultar-sem-apagar (SPEC.md §3.3).
# Mapa EM MEMORIA, sem servidor.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/viewlets.py

import os, sys, inspect, tempfile;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
os.environ["HOME"] = tempfile.mkdtemp(prefix="cml_viewlet_");

from PySide6.QtWidgets import QApplication;

from classlib.relationship.maprelationship import MapRelationship;
from classlib.relationship import viewlets;
from view.ui.mapa_relationship_engine import MapaRelationshipEngine;

FALHAS = [];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def montar():
    mapa = MapRelationship();
    mapa.name = "Viewlets";
    hub = mapa.addEntity("organization", 500, 300, text="Construtora X");
    folhas = [];
    for i in range(4):
        caixa = mapa.addEntity("person", 100 + i * 120, 100, text="P%d" % i);
        folhas.append(caixa);
        elo = mapa.addEntity("link", 200, 200, text="liga");
        elo.addFrom(caixa); elo.addTo(hub);
    solta = mapa.addEntity("other", 700, 600, text="Avulsa");
    # fonte so em uma: o viewlet "sem_fonte" tem de separar as duas situacoes
    hub.entity.references = [object()];
    mapa.desfazer.clear();
    return mapa, hub, folhas, solta;


def main():
    QApplication(sys.argv);
    mapa, hub, folhas, solta = montar();

    print("tamanho por vínculos");
    tabela = viewlets.calcular(mapa, "grau");
    confere(len(tabela) == 6, "uma entrada por caixa, vinculo de fora (%d)" % len(tabela));
    confere(tabela[hub][0] > tabela[folhas[0]][0], "o hub ficou maior que a folha");
    confere(tabela[solta][0] == viewlets.ESCALA_MIN, "a caixa sem vinculo ficou no tamanho normal");
    confere(tabela[hub][0] <= viewlets.ESCALA_MAX, "ninguem passa do teto de escala");

    print("\nrank acha o hub por vizinhança");
    rank = viewlets.calcular(mapa, "rank");
    confere(rank[folhas[0]][0] > rank[solta][0],
            "folha ligada ao hub vale mais que caixa solta, mesmo com grau baixo");

    print("\ncor por tipo");
    tipo = viewlets.calcular(mapa, "tipo");
    confere(tipo[hub][1] == viewlets.COR_TIPO["organization"], "organização com a cor dela");
    confere(tipo[folhas[0]][1] == viewlets.COR_TIPO["person"], "pessoa com a cor dela");
    confere(tipo[hub][0] == viewlets.ESCALA_MIN, "viewlet de cor não mexe no tamanho");

    print("\ncor: sem fonte");
    fonte = viewlets.calcular(mapa, "sem_fonte");
    confere(fonte[hub][1] == viewlets.COR_OK, "quem tem referência fica neutro");
    confere(fonte[solta][1] == viewlets.COR_ALERTA, "quem não tem referência fica em alerta");

    print("\nnenhum e desconhecido");
    confere(viewlets.calcular(mapa, "nenhum") == {}, "'nenhum' não devolve nada");
    confere(viewlets.calcular(mapa, "inventado") == {}, "viewlet desconhecido não quebra");
    confere(viewlets.calcular(MapRelationship(), "grau") == {}, "mapa vazio não quebra");

    print("\ntodos iguais não ampliam ninguém");
    plano = MapRelationship();
    for i in range(3):
        plano.addEntity("person", i * 50, 0, text="X%d" % i);
    tabela = viewlets.calcular(plano, "grau");
    confere(all(v[0] == viewlets.ESCALA_MIN for v in tabela.values()),
            "sem vínculo nenhum, ninguém cresce (ampliar tudo por igual não diz nada)");

    print("\nno canvas: a área CLICÁVEL cresce junto com o desenho");
    engine = MapaRelationshipEngine(parent=None, mapa=mapa, form=None);
    engine.resize(900, 700); engine.redraw();
    item_hub = [i for i in engine.itens if i.elemento is hub][0];
    antes = item_hub.shape().boundingRect().width();
    engine.aplicar_viewlet("grau");
    depois = item_hub.shape().boundingRect().width();
    confere(depois > antes, "a área clicável acompanhou a ampliação (%d -> %d)" % (antes, depois));
    confere(item_hub.boundingRect().width() >= depois, "e a área pintada cobre a clicável");
    engine.aplicar_viewlet("nenhum");
    confere(abs(item_hub.shape().boundingRect().width() - antes) < 1, "voltar a 'nenhum' volta ao tamanho");

    print("\nocultar sem apagar");
    mapa, hub, folhas, solta = montar();
    engine = MapaRelationshipEngine(parent=None, mapa=mapa, form=None);
    engine.resize(900, 700); engine.redraw();
    total = len(engine.itens);
    engine.ocultar([solta]);
    confere(len(mapa.elements) == 10, "o documento continua inteiro (nada foi apagado)");
    confere(len(engine.itens) == total - 1, "mas sumiu da tela");
    confere(mapa.desfazer.count() == 0, "ocultar é vista: não entra no desfazer");
    confere(engine.getElement(solta.x + 5, solta.y + 5) == None, "e não recebe clique no escuro");

    print("\nocultar caixa esconde o vínculo que a toca");
    antes_itens = len(engine.itens);
    engine.ocultar([folhas[0]]);
    confere(len(engine.itens) == antes_itens - 2, "sumiram a caixa E o vínculo dela (%d)" % len(engine.itens));

    print("\nbuscar revela o que está oculto");
    achou = engine.buscar("P0");
    confere(achou == 1, "achou mesmo oculta");
    confere(folhas[0] not in engine.ocultos, "e revelou, em vez de deixar o analista no escuro");

    print("\nmostrar tudo");
    engine.ocultar([solta, folhas[1]]);
    quantos = engine.mostrar_tudo();
    confere(quantos >= 2 and engine.quantidade_oculta() == 0, "voltou tudo (%d)" % quantos);
    confere(len(engine.itens) == 10, "todos os elements de volta na tela");

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
