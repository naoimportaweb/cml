#!/usr/bin/env python3
# Teste da List View do mapa de vinculos (SPEC.md §3.3). Mapa EM MEMORIA, sem servidor.
#
# O que importa conferir:
#   - entidades e vinculos vao para abas diferentes, com as colunas de cada um;
#   - o grau conta as duas pontas do vinculo;
#   - colunas de numero ordenam por VALOR (10 depois de 9, nao antes);
#   - data suja (0000-00-00, None) vira celula vazia, nao celula mentirosa;
#   - com a tabela ORDENADA, o duplo clique ainda abre o objeto certo -- a linha visivel
#     deixa de ser o indice do modelo, que e onde esse tipo de tela costuma errar.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/lista_diagrama.py

import os, sys, inspect, tempfile;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
os.environ["HOME"] = tempfile.mkdtemp(prefix="cml_lista_");

from PySide6.QtCore import Qt;
from PySide6.QtWidgets import QApplication;

from classlib.relationship.maprelationship import MapRelationship;
from view.ui.lista_diagrama import ListaDiagrama, periodo, data_limpa, rotulo_tipo;

FALHAS = [];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


class FormFalso:
    """Faz o papel do MdiMap: so anota qual element recebeu o duplo clique."""
    def __init__(self):
        self.aberto = None;
        self.redesenhou = False;
    def entity_double_click(self, elemento):
        self.aberto = elemento;
    def redesenhar(self):
        self.redesenhou = True;


def montar():
    mapa = MapRelationship();
    mapa.name = "Lista";
    # Zebra: a ordem no modelo NAO e a ordem alfabetica nem a de grau, de proposito.
    zeca = mapa.addEntity("person", 100, 100, text="Zeca");
    ana = mapa.addEntity("person", 300, 100, text="Ana");
    org = mapa.addEntity("organization", 500, 300, text="Empresa X");
    org.entity.small_label = "EX";
    processo = mapa.addEntity("other", 100, 400, text="Processo 123");
    processo.entity.sub_etype_name = "processo";
    processo.start_date = "0000-00-00";      # data suja: tem que sair como celula vazia
    zeca.start_date = "2019-01-01"; zeca.end_date = "2022-12-31";

    v1 = mapa.addEntity("link", 250, 200, text="dirige");
    v1.addFrom(zeca); v1.addTo(org);
    v2 = mapa.addEntity("link", 350, 250, text="assina");
    v2.addFrom(ana, start_date="2020-05-01", end_date=None); v2.addTo(org);
    v3 = mapa.addEntity("link", 200, 350, text="cita");
    v3.addFrom(processo); v3.addTo(org);
    return mapa, {"zeca": zeca, "ana": ana, "org": org, "processo": processo};


def coluna(tabela, linha, indice):
    item = tabela.item(linha, indice);
    return "" if item == None else item.text();


def main():
    QApplication(sys.argv);
    mapa, cx = montar();
    form = FormFalso();
    lista = ListaDiagrama(form, mapa);
    lista.atualizar();

    ent, vin = lista.tabela_entidades, lista.tabela_vinculos;

    print("separacao das abas");
    confere(ent.rowCount() == 4, "4 entidades na aba Entidades (%d)" % ent.rowCount());
    confere(vin.rowCount() == 3, "3 vinculos na aba Vinculos (%d)" % vin.rowCount());

    print("\ncolunas");
    confere(rotulo_tipo(cx["processo"]) == "Outro · processo", "tipo mostra o subtipo: %s" % rotulo_tipo(cx["processo"]));
    linha_org = [i for i in range(ent.rowCount()) if coluna(ent, i, 1) == "Empresa X"][0];
    confere(coluna(ent, linha_org, 2) == "EX", "apelido na coluna propria");
    confere(ent.item(linha_org, 3).data(Qt.DisplayRole) == 3, "grau da Empresa X conta as 3 pontas");

    print("\ndata");
    confere(data_limpa("0000-00-00") == "", "0000-00-00 e data suja");
    confere(periodo("2019-01-01", "2022-12-31") == "2019-01-01 → 2022-12-31", "periodo fechado");
    confere(periodo(None, None) == "", "sem data nao inventa periodo");
    linha_proc = [i for i in range(ent.rowCount()) if coluna(ent, i, 1) == "Processo 123"][0];
    confere(coluna(ent, linha_proc, 4) == "", "data suja virou celula vazia, nao '0000-00-00'");

    print("\nvinculo");
    linha_assina = [i for i in range(vin.rowCount()) if coluna(vin, i, 0) == "assina"][0];
    confere(coluna(vin, linha_assina, 1) == "Ana", "ponta DE");
    confere(coluna(vin, linha_assina, 2) == "Empresa X", "ponta PARA");
    confere("2020-05-01" in coluna(vin, linha_assina, 3), "periodo da ponta DE: %s" % coluna(vin, linha_assina, 3));
    confere(coluna(vin, linha_assina, 4) == "", "ponta PARA sem data fica vazia");

    print("\nordenacao por valor, nao por texto");
    ent.sortItems(3, Qt.DescendingOrder);
    primeiro = ent.item(0, 3).data(Qt.DisplayRole);
    ultimo = ent.item(ent.rowCount() - 1, 3).data(Qt.DisplayRole);
    confere(isinstance(primeiro, int), "coluna de numero guarda numero, nao texto");
    confere(primeiro >= ultimo, "ordenou decrescente (%s ... %s)" % (primeiro, ultimo));
    confere(coluna(ent, 0, 1) == "Empresa X", "o mais ligado ficou em cima");

    print("\nduplo clique COM a tabela ordenada");
    # Depois do sortItems, a linha 0 nao e mais o indice 0 do modelo. Se o codigo usasse o
    # numero da linha, abriria o objeto errado -- e esta e a linha de defesa do teste.
    lista.__abrir_entidade__(0, 1);
    confere(form.aberto is cx["org"], "abriu a Empresa X, que e quem esta na linha 0");
    confere(form.redesenhou, "pediu redesenho depois de fechar o dialogo");
    form.aberto = None;
    vin.sortItems(0, Qt.AscendingOrder);
    lista.__abrir_vinculo__(0, 0);
    confere(form.aberto != None and form.aberto.entity.text == coluna(vin, 0, 0),
            "vinculo aberto bate com a linha clicada (%s)" % coluna(vin, 0, 0));

    print("\nnao edita e nao grava");
    from PySide6.QtWidgets import QAbstractItemView;
    confere(ent.editTriggers() == QAbstractItemView.NoEditTriggers, "tabela e somente leitura");
    item = ent.item(0, 1);
    confere(not (item.flags() & Qt.ItemIsEditable), "celula nao editavel");

    print("\nmapa vazio");
    vazia = ListaDiagrama(form, MapRelationship());
    vazia.atualizar();
    confere(vazia.tabela_entidades.rowCount() == 0 and vazia.tabela_vinculos.rowCount() == 0,
            "mapa sem nada mostra tabela vazia, sem quebrar");

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
