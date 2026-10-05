# O mapa de vinculos em TABELA, nao em desenho -- a "List View" do Maltego (SPEC.md §3.3).
#
# E uma VISTA do mesmo mapa, nao outro documento: le os mesmos elements, nao guarda nada e nao
# grava nada. Duplo clique abre o dialogo do objeto, igual ao duplo clique no canvas e ao do
# DialogRelationshipCheck.
#
# Duas abas porque no CML o vinculo TAMBEM e element, e as colunas dele sao outras: entidade tem
# apelido e classificacao, vinculo tem ponta de origem, ponta de destino e um periodo POR PONTA.

from PySide6.QtWidgets import (QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem,
                               QTabWidget, QVBoxLayout, QWidget);
from PySide6.QtCore import Qt;

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( CURRENTDIR ) ) );

ROTULO_TIPO = {"person": "Pessoa", "organization": "Organização", "other": "Outro", "link": "Vínculo"};
COLUNAS_ENTIDADE = ["Tipo", "Nome", "Apelido", "Vínculos", "Período", "Refs", "Classif.", "Descrição"];
COLUNAS_VINCULO = ["Verbo", "De", "Para", "Período (de)", "Período (para)", "Refs"];
SUJO = ("", "0000-00-00", "none", "null");


def data_limpa(valor):
    # Data suja existe no banco (0000-00-00, NULL, texto) e nao pode virar celula mentirosa.
    texto = str(valor or "").strip();
    return "" if texto.lower() in SUJO else texto;


def periodo(inicio, fim):
    inicio, fim = data_limpa(inicio), data_limpa(fim);
    if inicio == "" and fim == "":
        return "";
    if inicio != "" and fim != "":
        return inicio + " → " + fim;
    return (inicio or fim) + (" →" if inicio != "" else "← ");


def rotulo_tipo(elemento):
    base = ROTULO_TIPO.get(elemento.entity.etype, elemento.entity.etype or "?");
    sub = (elemento.entity.sub_etype_name or "").strip();
    return base + (" · " + sub if sub != "" else "");


def __texto__(valor):
    return " ".join(str(valor or "").split());


def __celula__(texto, numero=None):
    item = QTableWidgetItem();
    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable);
    if numero != None:
        # Guardado como numero para a coluna ordenar por valor, nao em ordem alfabetica
        # ("10" antes de "9" e o defeito classico de tabela ordenada por texto).
        item.setData(Qt.DisplayRole, int(numero));
    else:
        item.setText(texto);
    return item;


class ListaDiagrama(QWidget):
    def __init__(self, form, mapa):
        super().__init__();
        self.form = form;
        self.mapa = mapa;
        self.linhas_entidade = [];   # indice da linha -> element, para o duplo clique
        self.linhas_vinculo = [];

        self.abas = QTabWidget();
        self.tabela_entidades = self.__montar_tabela__(COLUNAS_ENTIDADE, self.__abrir_entidade__);
        self.tabela_vinculos = self.__montar_tabela__(COLUNAS_VINCULO, self.__abrir_vinculo__);
        # Ordem inicial escolhida, nao herdada: mais ligados primeiro, que e a pergunta que a
        # tabela responde e o desenho nao ("quem e o centro disto?"). Como o setSortingEnabled
        # reaplica o indicador atual, a ordem que o analista escolher sobrevive aos refresh.
        self.tabela_entidades.horizontalHeader().setSortIndicator(COLUNAS_ENTIDADE.index("Vínculos"), Qt.DescendingOrder);
        self.tabela_vinculos.horizontalHeader().setSortIndicator(COLUNAS_VINCULO.index("Verbo"), Qt.AscendingOrder);
        self.abas.addTab(self.tabela_entidades, "Entidades");
        self.abas.addTab(self.tabela_vinculos, "Vínculos");

        layout = QVBoxLayout();
        layout.setContentsMargins(0, 0, 0, 0);
        layout.addWidget(self.abas);
        self.setLayout(layout);

    def __montar_tabela__(self, colunas, ao_abrir):
        tabela = QTableWidget(0, len(colunas));
        tabela.setHorizontalHeaderLabels(colunas);
        # Vista, nao editor: quem edita e o dialogo do objeto.
        tabela.setEditTriggers(QAbstractItemView.NoEditTriggers);
        tabela.setSelectionBehavior(QAbstractItemView.SelectRows);
        tabela.setAlternatingRowColors(True);
        tabela.setSortingEnabled(True);
        tabela.verticalHeader().setVisible(False);
        tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive);
        tabela.horizontalHeader().setStretchLastSection(True);
        tabela.cellDoubleClicked.connect(ao_abrir);
        return tabela;

    # ------------------------------------------------------------------ dados

    def __caixas__(self):
        return [e for e in self.mapa.elements if e.entity.etype != "link"];

    def __vinculos__(self):
        return [e for e in self.mapa.elements if e.entity.etype == "link"];

    def __grau__(self, caixa):
        # Quantos vinculos tocam esta caixa, contando as duas pontas.
        total = 0;
        for vinculo in self.__vinculos__():
            for ponta in list(vinculo.to_entity) + list(vinculo.from_entity):
                if ponta.entity is caixa:
                    total = total + 1;
        return total;

    def __pontas__(self, lista):
        nomes = [__texto__(p.entity.entity.text) for p in lista if p.entity != None];
        return ", ".join([n for n in nomes if n != ""]);

    def __periodo_pontas__(self, lista):
        partes = [periodo(p.start_date, p.end_date) for p in lista];
        return ", ".join([p for p in partes if p != ""]);

    def atualizar(self):
        """Refaz as duas tabelas a partir do modelo. Chamado ao mostrar a lista e no
        redesenhar do MdiMap -- a lista nunca guarda copia do mapa."""
        self.__preencher_entidades__();
        self.__preencher_vinculos__();

    def __preencher_entidades__(self):
        caixas = self.__caixas__();
        tabela = self.tabela_entidades;
        tabela.setSortingEnabled(False);   # ordenar durante o preenchimento embaralha as linhas
        tabela.setRowCount(len(caixas));
        self.linhas_entidade = caixas;
        for linha in range(len(caixas)):
            caixa = caixas[linha];
            entidade = caixa.entity;
            celula_tipo = __celula__(rotulo_tipo(caixa));
            celula_tipo.setData(Qt.UserRole, linha);   # indice no modelo, que a ordenacao nao muda
            tabela.setItem(linha, 0, celula_tipo);
            tabela.setItem(linha, 1, __celula__(__texto__(entidade.text)));
            tabela.setItem(linha, 2, __celula__(__texto__(entidade.small_label)));
            tabela.setItem(linha, 3, __celula__(None, numero=self.__grau__(caixa)));
            # O periodo da CAIXA (o que vale neste mapa), nao o da entidade global.
            tabela.setItem(linha, 4, __celula__(periodo(caixa.start_date, caixa.end_date)));
            tabela.setItem(linha, 5, __celula__(None, numero=len(entidade.references or [])));
            tabela.setItem(linha, 6, __celula__(None, numero=len(entidade.classification or [])));
            tabela.setItem(linha, 7, __celula__(__texto__(entidade.full_description)[:300]));
        tabela.setSortingEnabled(True);
        tabela.resizeColumnsToContents();

    def __preencher_vinculos__(self):
        vinculos = self.__vinculos__();
        tabela = self.tabela_vinculos;
        tabela.setSortingEnabled(False);
        tabela.setRowCount(len(vinculos));
        self.linhas_vinculo = vinculos;
        for linha in range(len(vinculos)):
            vinculo = vinculos[linha];
            celula_verbo = __celula__(__texto__(vinculo.entity.text));
            celula_verbo.setData(Qt.UserRole, linha);
            tabela.setItem(linha, 0, celula_verbo);
            tabela.setItem(linha, 1, __celula__(self.__pontas__(vinculo.from_entity)));
            tabela.setItem(linha, 2, __celula__(self.__pontas__(vinculo.to_entity)));
            tabela.setItem(linha, 3, __celula__(self.__periodo_pontas__(vinculo.from_entity)));
            tabela.setItem(linha, 4, __celula__(self.__periodo_pontas__(vinculo.to_entity)));
            tabela.setItem(linha, 5, __celula__(None, numero=len(vinculo.entity.references or [])));
        tabela.setSortingEnabled(True);
        tabela.resizeColumnsToContents();

    # ------------------------------------------------------------------ acoes

    def __abrir__(self, tabela, origem, linha):
        # A tabela pode estar ordenada por qualquer coluna, entao o numero da linha visivel nao
        # e o indice no modelo: o element vai guardado na propria celula.
        item = tabela.item(linha, 0);
        if item == None:
            return;
        indice = item.data(Qt.UserRole);
        elemento = origem[indice] if (indice != None and indice < len(origem)) else None;
        if elemento == None or self.form == None:
            return;
        self.form.entity_double_click(elemento);
        self.form.redesenhar();

    def __abrir_entidade__(self, linha, coluna):
        self.__abrir__(self.tabela_entidades, self.linhas_entidade, linha);

    def __abrir_vinculo__(self, linha, coluna):
        self.__abrir__(self.tabela_vinculos, self.linhas_vinculo, linha);
