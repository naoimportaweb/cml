#!/usr/bin/env python3
# Teste do organograma depois da reescrita. Em memoria, sem servidor.
#
# O que a versao antiga fazia e nao pode voltar a fazer:
#   - altura fixa em 25 e y = nivel*75: caixa com tres nomes transbordava na linha de baixo;
#   - posicao sem controle de vizinho: caixas irmas encostavam ou se sobrepunham;
#   - Remove que nao removia nada (metodo com corpo vazio);
#   - duplo clique desligado.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/organograma.py

import os, sys, inspect, tempfile;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
TEMP = tempfile.mkdtemp(prefix="cml_org_");
os.environ["HOME"] = TEMP;

from PySide6.QtGui import QPainter, QPixmap;
from PySide6.QtWidgets import QApplication;

from classlib.organization_chart.organization_chart import OrganizationChart;
from classlib.organization_chart import organization_chart_item as modelo;
from classlib.entity import Entity;
from classlib.exportar_diagrama import fonte_do_diagrama;
from classlib import exportar_diagrama as ex;

FALHAS = [];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def entidade(nome, etype="person"):
    e = Entity();
    e.text = nome;
    e.etype = etype;
    return e;


def desenhar(chart):
    """Roda o layout, que e o que o canvas e o exportador fazem antes de pintar."""
    rascunho = QPixmap(1, 1);
    painter = QPainter();
    painter.begin(rascunho);
    painter.setFont(fonte_do_diagrama());
    if chart.root != None:
        chart.root.recalc(painter);
    painter.end();


def montar():
    chart = OrganizationChart("org");
    chart.text_label = "Construtora X";
    raiz = chart.addEntityItem("Presidência");
    raiz.addEntity(entidade("Zeca Silva"));
    diretorias = [];
    for nome, pessoas in [("Diretoria Financeira", ["Ana Souza", "Bruno Lima"]),
                          ("Diretoria de Obras", ["Carla Dias"]),
                          ("Diretoria Jurídica", ["Dora Reis", "Elton Paz", "Fábio Cruz"])]:
        item = chart.addEntityItem(nome, organization_chart_item_parent_id=raiz.id);
        for pessoa in pessoas:
            item.addEntity(entidade(pessoa));
        diretorias.append(item);
    for nome in ["Contabilidade", "Tesouraria"]:
        chart.addEntityItem(nome, organization_chart_item_parent_id=diretorias[0].id);
    chart.addEntityItem("Contencioso", organization_chart_item_parent_id=diretorias[2].id);
    return chart, raiz, diretorias;


def colisoes(chart):
    itens = chart.root.todos();
    pares = 0;
    for i in range(len(itens)):
        for j in range(i + 1, len(itens)):
            a, b = itens[i], itens[j];
            if not (a.x + a.w <= b.x or b.x + b.w <= a.x or a.y + a.h <= b.y or b.y + b.h <= a.y):
                pares = pares + 1;
    return pares;


def main():
    QApplication(sys.argv);
    chart, raiz, diretorias = montar();
    desenhar(chart);

    print("layout: nada se sobrepõe");
    confere(colisoes(chart) == 0, "zero colisões entre caixas (%d)" % colisoes(chart));

    print("\nfolga entre irmãos é a combinada");
    por_nivel = {};
    for item in chart.root.todos():
        por_nivel.setdefault(item.level, []).append(item);
    folgas = [];
    for nivel in por_nivel:
        linha = sorted(por_nivel[nivel], key=lambda i: i.x);
        for k in range(1, len(linha)):
            folgas.append(linha[k].x - (linha[k - 1].x + linha[k - 1].w));
    confere(len(folgas) > 0 and min(folgas) >= modelo.ESPACO_IRMAO,
            "menor folga %d >= %d" % (min(folgas), modelo.ESPACO_IRMAO));

    print("\npai centrado sobre os filhos");
    fora = 0;
    for pai in chart.root.todos():
        if len(pai.elements) == 0:
            continue;
        primeiro, ultimo = pai.elements[0], pai.elements[-1];
        centro_filhos = (primeiro.x + primeiro.w / 2.0 + ultimo.x + ultimo.w / 2.0) / 2.0;
        if abs((pai.x + pai.w / 2.0) - centro_filhos) > 2:
            fora = fora + 1;
    confere(fora == 0, "todo pai no centro dos filhos (%d fora)" % fora);

    print("\naltura é medida, não fixa");
    uma = [d for d in diretorias if d.text_label == "Diretoria de Obras"][0];     # 1 pessoa
    tres = [d for d in diretorias if d.text_label == "Diretoria Jurídica"][0];    # 3 pessoas
    confere(tres.h > uma.h, "caixa com 3 nomes é mais alta que a de 1 (%d > %d)" % (tres.h, uma.h));
    vazia = chart.addEntityItem("Sem ninguém", organization_chart_item_parent_id=raiz.id);
    desenhar(chart);
    confere(vazia.h < uma.h, "e a sem ninguém é a mais baixa (%d < %d)" % (vazia.h, uma.h));
    confere(colisoes(chart) == 0, "mesmo com alturas diferentes, nada se sobrepõe");

    print("\nníveis descem na ordem");
    niveis = sorted(set(i.level for i in chart.root.todos()));
    ys = [min(i.y for i in chart.root.todos() if i.level == n) for n in niveis];
    confere(ys == sorted(ys) and len(set(ys)) == len(ys), "cada nível abaixo do anterior: %s" % ys);

    print("\nclique acerta a caixa certa");
    alvo = diretorias[1];
    confere(chart.findByXY(alvo.x + 5, alvo.y + 5) is alvo, "clique dentro acha o item");
    confere(chart.findByXY(alvo.x - 50, alvo.y - 50) == None, "clique fora não acha nada");

    print("\nremover: os filhos SOBEM, não somem junto");
    chart, raiz, diretorias = montar();
    desenhar(chart);
    financeira = diretorias[0];
    netos = [i.text_label for i in financeira.elements];
    antes = len(chart.root.todos());
    confere(chart.removerItem(financeira), "removeu a diretoria");
    restantes = [i.text_label for i in chart.root.todos()];
    confere("Diretoria Financeira" not in restantes, "ela saiu");
    for neto in netos:
        confere(neto in restantes, "%s continua no organograma" % neto);
    confere(len(chart.root.todos()) == antes - 1, "saiu exatamente um item");
    subiram = [i for i in chart.root.todos() if i.text_label in netos];
    confere(all(i.level == 1 for i in subiram), "e subiram um nível");
    confere(all(i.organization_chart_item_parent_id == raiz.id for i in subiram), "agora penduradas na raiz");
    desenhar(chart);
    confere(colisoes(chart) == 0, "o desenho continua sem colisão depois da remoção");

    print("\nraiz com filhos não é removida por engano");
    try:
        chart.removerItem(chart.root);
        confere(False, "deveria recusar");
    except Exception as erro:
        confere("raiz" in str(erro).lower(), "recusou com motivo: %s" % erro);

    print("\nentidade sai do item, não do banco");
    chart, raiz, diretorias = montar();
    juridica = diretorias[2];
    confere(len(juridica.entitys) == 3, "três no item");
    confere(juridica.delEntity(1), "removeu a do meio");
    nomes = [e.getText() for e in juridica.entitys];
    confere(nomes == ["Dora Reis", "Fábio Cruz"], "sobraram as certas: %s" % nomes);
    confere(not juridica.delEntity(9), "índice inválido não quebra");

    print("\ntamanho do desenho e exportação");
    desenhar(chart);
    x, y, largura, altura = chart.tamanho();
    confere(largura > 100 and altura > 100, "tamanho faz sentido (%dx%d)" % (largura, altura));
    caminho = ex.exportar(chart, os.path.join(TEMP, "organograma"), formato="png", legenda=False);
    confere(os.path.exists(caminho) and os.path.getsize(caminho) > 2000, "exportou PNG do organograma");

    print("\norganograma só com a raiz, e vazio");
    so_raiz = OrganizationChart("x");
    sozinho = so_raiz.addEntityItem("Único");
    desenhar(so_raiz);
    confere(sozinho.w > 0 and sozinho.y == 0, "a raiz sozinha é posicionada");
    confere(so_raiz.removerItem(sozinho), "e pode ser removida quando não tem filhos");
    confere(so_raiz.root == None, "o organograma fica vazio");
    confere(so_raiz.tamanho() == (0, 0, 1, 1), "tamanho de organograma vazio não quebra");

    print("\no exportador mede a MESMA altura que o item tem");
    # O exportador somava as linhas das entidades de novo, por cima do h que ja as inclui: 93
    # reais viravam 138, o "caber na pagina" encolhia demais e o 1:1 criava pagina em branco.
    alto = OrganizationChart("alt");
    item = alto.addEntityItem("Diretoria");
    for nome in ["Ana", "Bruno", "Carla"]:
        item.addEntity(entidade(nome));
    desenhar(alto);
    conteudo, _total = ex.__area__(alto, False);
    confere(conteudo.height() == item.h,
            "altura medida = altura do item (%d == %d)" % (conteudo.height(), item.h));
    confere(conteudo.width() == item.w, "e a largura também");

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
