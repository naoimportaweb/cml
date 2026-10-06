#!/usr/bin/env python3
# Teste do canvas do mapa de vinculos depois da migracao para QGraphicsView (SPEC.md §3.1).
# Monta um mapa EM MEMORIA -- sem servidor, sem login -- e confere o que a migracao nao pode
# ter quebrado, mais o que ela foi feita para ganhar:
#
#   - um item por element, vinculo embaixo e caixa em cima;
#   - a area PINTADA do vinculo cobre as pontas (senao o Qt corta a linha) e a area CLICAVEL
#     e so a caixa do verbo (senao o vinculo engole o clique de tudo entre as pontas);
#   - arrastar move o modelo, e mapa travado nao se move;
#   - zoom tem limite e a cena acompanha o conteudo.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/mapa_relationship_engine.py

import os, sys, inspect, tempfile;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
os.environ["HOME"] = tempfile.mkdtemp(prefix="cml_canvas_");

from PySide6.QtCore import QEvent, QPointF, Qt;
from PySide6.QtGui import QMouseEvent;
from PySide6.QtWidgets import QApplication;

from classlib.relationship.maprelationship import MapRelationship;
from view.ui.mapa_relationship_engine import MapaRelationshipEngine, ZOOM_MIN, ZOOM_MAX;

FALHAS = [];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def montar():
    mapa = MapRelationship();
    mapa.name = "Canvas";
    pessoa = mapa.addEntity("person", 100, 100, text="Fulano");
    org = mapa.addEntity("organization", 700, 500, text="Empresa X");
    vinculo = mapa.addEntity("link", 300, 300, text="dirige");
    vinculo.addFrom(pessoa);
    vinculo.addTo(org);
    return mapa, pessoa, org, vinculo;


def evento(engine, tipo, x_cena, y_cena):
    # Monta o evento em coordenada de VIEW a partir da coordenada de cena, para o teste nao
    # depender de onde a barra de rolagem esta.
    ponto = QPointF(engine.mapFromScene(QPointF(x_cena, y_cena)));
    return QMouseEvent(tipo, ponto, ponto, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier);


def main():
    QApplication(sys.argv);
    mapa, pessoa, org, vinculo = montar();
    engine = MapaRelationshipEngine(parent=None, mapa=mapa, form=None);
    engine.resize(900, 700);
    engine.redraw();

    print("itens e ordem");
    confere(len(engine.itens) == 3, "um item por element (%d)" % len(engine.itens));
    z = {i.elemento.entity.etype: i.zValue() for i in engine.itens};
    confere(z.get("link") == 0, "vinculo com z=0 (por baixo)");
    confere(z.get("person") == 1 and z.get("organization") == 1, "caixas com z=1 (por cima)");

    print("\nhiper-aresta: area pintada x area clicavel");
    item_link = [i for i in engine.itens if i.elemento.entity.etype == "link"][0];
    pintada = item_link.boundingRect();
    clicavel = item_link.shape().boundingRect();
    confere(pintada.contains(float(pessoa.x), float(pessoa.y)), "area pintada cobre a ponta de origem");
    confere(pintada.contains(float(org.x), float(org.y)), "area pintada cobre a ponta de destino");
    confere(not clicavel.contains(float(org.x), float(org.y)), "area clicavel NAO engole a outra caixa");
    confere(clicavel.width() < pintada.width(), "clicavel (%d) menor que pintada (%d)"
            % (clicavel.width(), pintada.width()));

    print("\nsorteio de clique");
    confere(engine.getElement(pessoa.x + 5, pessoa.y + 5) is pessoa, "clique na caixa acha a caixa");
    confere(engine.getElement(2000, 2000) == None, "clique no vazio nao acha nada");

    print("\narrastar move o modelo");
    x0, y0 = pessoa.x, pessoa.y;
    engine.mousePressEvent(evento(engine, QEvent.MouseButtonPress, x0 + 5, y0 + 5));
    confere(engine.selected_element is pessoa, "a caixa ficou selecionada no press");
    engine.mouseMoveEvent(evento(engine, QEvent.MouseMove, x0 + 45, y0 + 35));
    engine.mouseReleaseEvent(evento(engine, QEvent.MouseButtonRelease, x0 + 45, y0 + 35));
    confere(pessoa.x == x0 + 40 and pessoa.y == y0 + 30,
            "andou o mesmo que o mouse (%d,%d -> %d,%d)" % (x0, y0, pessoa.x, pessoa.y));
    confere(item_link.boundingRect().contains(float(pessoa.x), float(pessoa.y)),
            "o vinculo acompanhou a caixa que se moveu");

    print("\nmapa travado nao se move");
    mapa.locked = True;
    confere(mapa.getLocked(), "o mapa esta travado");
    x1, y1 = pessoa.x, pessoa.y;
    engine.mousePressEvent(evento(engine, QEvent.MouseButtonPress, x1 + 5, y1 + 5));
    engine.mouseMoveEvent(evento(engine, QEvent.MouseMove, x1 + 90, y1 + 90));
    engine.mouseReleaseEvent(evento(engine, QEvent.MouseButtonRelease, x1 + 90, y1 + 90));
    confere(pessoa.x == x1 and pessoa.y == y1, "travado: a caixa NAO andou (%d,%d)" % (pessoa.x, pessoa.y));
    mapa.locked = False;

    print("\nzoom");
    engine.zoom_normal();
    engine.zoom_mais();
    confere(engine.escala > 1.0, "zoom + aumenta (%.2f)" % engine.escala);
    engine.zoom_normal();
    confere(abs(engine.escala - 1.0) < 0.001, "zoom 100% volta a 1.0");
    for _ in range(40):
        engine.zoom_menos();
    confere(engine.escala >= ZOOM_MIN - 0.001, "nao passa do limite minimo (%.2f)" % engine.escala);
    for _ in range(80):
        engine.zoom_mais();
    confere(engine.escala <= ZOOM_MAX + 0.001, "nao passa do limite maximo (%.2f)" % engine.escala);
    engine.zoom_normal();
    engine.ajustar_a_janela();
    confere(engine.escala > 0, "ajustar a janela devolve escala valida (%.2f)" % engine.escala);

    print("\ncena acompanha o conteudo");
    cena = engine.cena.sceneRect();
    confere(cena.contains(float(org.x), float(org.y)), "a cena contem a caixa mais distante");
    anterior = engine.cena.sceneRect().width();
    org.setX(3000);
    engine.redraw();
    confere(engine.cena.sceneRect().width() > anterior,
            "cena cresceu quando a caixa foi longe (%d -> %d)" % (anterior, engine.cena.sceneRect().width()));

    print("\nmapa vazio nao quebra");
    vazio = MapaRelationshipEngine(parent=None, mapa=MapRelationship(), form=None);
    vazio.redraw();
    confere(len(vazio.itens) == 0 and not vazio.cena.sceneRect().isEmpty(),
            "mapa sem caixa redesenha e tem cena com tamanho");

    print("\nselecao em massa");
    mapa, pessoa, org, vinculo = montar();
    engine = MapaRelationshipEngine(parent=None, mapa=mapa, form=None);
    engine.resize(900, 700); engine.redraw();
    confere(engine.selecionados() == [], "comeca sem nada selecionado");
    confere(engine.selecionar_todos() == 3, "selecionar tudo pega os 3");
    confere(len(engine.selecionados()) == 3, "e selecionados() concorda");
    engine.selecionar([pessoa]);
    confere(engine.selecionados() == [pessoa], "selecionar() troca a selecao");

    print("\narrastar move o GRUPO");
    engine.selecionar([pessoa, org]);
    px, py, ox, oy = pessoa.x, pessoa.y, org.x, org.y;
    engine.mousePressEvent(evento(engine, QEvent.MouseButtonPress, px + 5, py + 5));
    engine.mouseMoveEvent(evento(engine, QEvent.MouseMove, px + 55, py + 25));
    engine.mouseReleaseEvent(evento(engine, QEvent.MouseButtonRelease, px + 55, py + 25));
    confere(pessoa.x == px + 50 and pessoa.y == py + 20, "a caixa clicada andou");
    confere(org.x == ox + 50 and org.y == oy + 20, "a OUTRA selecionada andou igual");
    confere(mapa.desfazer.count() == 1, "o grupo inteiro = um passo de desfazer");
    mapa.desfazer.undo();
    confere(pessoa.x == px and org.x == ox, "desfazer devolveu as duas");

    print("\nclicar em caixa fora da selecao recomeca a selecao");
    engine.selecionar([org]);
    engine.mousePressEvent(evento(engine, QEvent.MouseButtonPress, pessoa.x + 5, pessoa.y + 5));
    confere(engine.selecionados() == [pessoa], "so a clicada ficou selecionada");
    engine.mouseReleaseEvent(evento(engine, QEvent.MouseButtonRelease, pessoa.x + 5, pessoa.y + 5));

    print("\nbuscar no mapa");
    mapa, pessoa, org, vinculo = montar();
    engine = MapaRelationshipEngine(parent=None, mapa=mapa, form=None);
    engine.resize(900, 700); engine.redraw();
    confere(engine.buscar("empresa") == 1, "acha por nome, sem diferenciar maiuscula");
    confere(engine.selecionados() == [org], "e deixa o achado selecionado");
    confere(engine.buscar("inexistente") == 0, "nao acha o que nao existe");
    confere(engine.buscar("") == 0, "busca vazia nao seleciona o mapa inteiro");

    print("\napagar selecionados em ordem de dependencia");
    mapa, pessoa, org, vinculo = montar();
    engine = MapaRelationshipEngine(parent=None, mapa=mapa, form=None);
    engine.resize(900, 700); engine.redraw();
    engine.selecionar([pessoa]);   # caixa presa a um vinculo que ficou de fora
    apagados, barrados = engine.apagar_selecionados();
    confere((apagados, barrados) == (0, 1), "caixa presa a vinculo de fora e BARRADA, nao apagada por tabela");
    confere(pessoa in mapa.elements, "e continua no mapa");
    engine.selecionar([pessoa, vinculo, org]);
    apagados, barrados = engine.apagar_selecionados();
    confere(apagados == 3 and barrados == 0, "com o vinculo junto, sai tudo (%d/%d)" % (apagados, barrados));
    confere(len(mapa.elements) == 0, "mapa ficou vazio");
    mapa.desfazer.undo();
    confere(len(mapa.elements) == 3, "um desfazer trouxe os tres de volta");

    print("\nmapa travado nao apaga");
    mapa.locked = True;
    engine.redraw(); engine.selecionar_todos();
    try:
        engine.apagar_selecionados();
        confere(False, "deveria recusar");
    except Exception as erro:
        confere("travado" in str(erro), "recusou: %s" % erro);
    mapa.locked = False;

    print("\nclique acompanha a ampliação do viewlet");
    # Graus DIFERENTES de propósito: com todos iguais o viewlet não amplia ninguém (e aí o
    # teste passaria sem testar nada, que foi o erro da primeira versão desta asserção).
    mapa, pessoa, org, vinculo = montar();
    outra_folha = mapa.addEntity("person", 50, 500, text="Segunda");
    elo = mapa.addEntity("link", 300, 400, text="liga"); elo.addFrom(outra_folha); elo.addTo(org);
    engine = MapaRelationshipEngine(parent=None, mapa=mapa, form=None);
    engine.resize(900, 700); engine.redraw();
    engine.aplicar_viewlet("grau");
    item = [i for i in engine.itens if i.elemento is org][0];
    confere(item.escala > 1.0, "a caixa está ampliada (%.2f)" % item.escala);
    borda_x = org.x + org.w + 4;   # fora do retângulo cru, dentro do desenhado
    confere(item.shape().boundingRect().right() > borda_x, "o ponto está dentro da área desenhada");
    confere(engine.getElement(borda_x, org.y + org.h / 2) is org,
            "e o clique nele acha a caixa (antes caía no vazio)");
    engine.aplicar_viewlet("nenhum");

    print("\nbuscar revela também o que está dentro de grupo colapsado");
    mapa, pessoa, org, vinculo = montar();
    engine = MapaRelationshipEngine(parent=None, mapa=mapa, form=None);
    engine.resize(900, 700); engine.redraw();
    outra = mapa.addEntity("person", 700, 700, text="Beltrano");
    engine.redraw();
    engine.selecionar([pessoa, outra]);
    engine.colapsar_selecionados("Grupo");
    confere(len(engine.grupos) == 1, "grupo criado");
    achou = engine.buscar("Beltrano");
    confere(achou == 1, "achou dentro do grupo");
    confere(len(engine.grupos) == 0, "o grupo foi expandido para mostrar");
    confere(engine.selecionados() == [outra], "e o achado ficou selecionado de verdade");

    print("\nbotão direito não desfaz a seleção");
    mapa, pessoa, org, vinculo = montar();
    engine = MapaRelationshipEngine(parent=None, mapa=mapa, form=None);
    engine.resize(900, 700); engine.redraw();
    engine.selecionar([pessoa, org]);
    ponto = QPointF(engine.mapFromScene(QPointF(pessoa.x + 5, pessoa.y + 5)));
    direito = QMouseEvent(QEvent.MouseButtonPress, ponto, ponto, Qt.RightButton, Qt.RightButton, Qt.NoModifier);
    engine.mousePressEvent(direito);
    confere(len(engine.selecionados()) == 2, "as duas continuam selecionadas (%d)" % len(engine.selecionados()));
    confere(engine.selected_element == None, "e nada entrou em modo de arrasto");

    print("\npeso do vínculo é DERIVADO das referências");
    mapa, pessoa, org, vinculo = montar();
    confere(vinculo.peso() == 0, "sem referência, peso 0");
    fino = vinculo._Link__espessura__() if hasattr(vinculo, "_Link__espessura__") else vinculo.__espessura__();
    for i in range(3):
        vinculo.addReference("Fonte %d" % i, "https://exemplo.test/%d" % i);
    confere(vinculo.peso() == 3, "três referências, peso 3 (%d)" % vinculo.peso());
    grosso = vinculo.__espessura__();
    confere(grosso > fino, "e a linha engrossou (%d -> %d)" % (fino, grosso));
    for i in range(20):
        vinculo.addReference("Mais %d" % i, "https://exemplo.test/m%d" % i);
    confere(vinculo.__espessura__() <= 4, "com teto: acima de 4 a linha vira mancha (%d)" % vinculo.__espessura__());
    confere(len(mapa.elements) == 3, "e nada disso criou element novo (é derivado, não guardado)");

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
