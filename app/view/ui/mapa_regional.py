# Vista "Mapa regional" do mapa de vinculos: os paises que a investigacao toca, com a
# bandeira, ordenados por peso.
#
# E uma VISTA do mesmo documento, como a List View -- nao um quarto tipo de diagrama. Nao
# guarda nada, nao grava nada, e o duplo clique abre o dialogo do pais.
#
# ⚠️ NAO E PROJECAO GEOGRAFICA, e a razao esta em classlib/relationship/regional.py: nao ha
# coordenada no banco nem geometria no repositorio, e inventar qualquer uma das duas daria um
# desenho que parece certo e esta errado. Se um dia houver um GeoJSON em
# app/resources/paises.geojson, e aqui que o coropleto entra -- o id de pais semeado e uuid5 do
# ISO, entao a juncao com uma base externa ja e possivel pelo codigo.

from PySide6.QtCore import Qt, QByteArray;
from PySide6.QtGui import QColor, QFont, QPixmap;
from PySide6.QtWidgets import (QAbstractItemView, QHeaderView, QLabel, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget);

import base64, os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( CURRENTDIR ) ) );

from classlib.relationship import regional;
from view.ui import estilo;

COLUNAS = ["", "País", "Entidades", "Vínculos"];
LADO_BANDEIRA = 34;


class MapaRegional(QWidget):
    def __init__(self, form, mapa):
        super().__init__();
        self.form = form;
        self.mapa = mapa;
        self.linhas = [];

        layout = QVBoxLayout(self);
        layout.setContentsMargins(14, 12, 14, 12);
        layout.setSpacing(8);

        self.titulo = QLabel("Mapa regional");
        fonte = self.titulo.font(); fonte.setPointSize(13); fonte.setBold(True);
        self.titulo.setFont(fonte);
        layout.addWidget(self.titulo);

        self.explicacao = QLabel("");
        self.explicacao.setWordWrap(True);
        self.explicacao.setStyleSheet("color: %s;" % estilo.COR_APAGADO);
        layout.addWidget(self.explicacao);

        self.tabela = QTableWidget(0, len(COLUNAS));
        self.tabela.setHorizontalHeaderLabels(COLUNAS);
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers);
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows);
        self.tabela.verticalHeader().setVisible(False);
        self.tabela.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents);
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch);
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents);
        self.tabela.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents);
        self.tabela.setIconSize(self.tabela.iconSize());
        self.tabela.verticalHeader().setDefaultSectionSize(LADO_BANDEIRA + 8);
        self.tabela.cellDoubleClicked.connect(self.__abrir__);
        layout.addWidget(self.tabela);

    def __bandeira__(self, base64_png):
        if not base64_png:
            return None;
        try:
            dados = QByteArray.fromBase64(bytes(str(base64_png), "ascii"));
        except Exception:
            return None;
        pixmap = QPixmap();
        # loadFromData detecta pelo conteudo (JPEG novo ou PNG antigo), como no resto do app.
        if not pixmap.loadFromData(dados) or pixmap.isNull():
            return None;
        return pixmap.scaled(LADO_BANDEIRA, LADO_BANDEIRA, Qt.KeepAspectRatio, Qt.SmoothTransformation);

    def atualizar(self):
        resumo = regional.agregar(self.mapa);
        self.linhas = resumo;
        self.tabela.setRowCount(len(resumo));
        for i in range(len(resumo)):
            linha = resumo[i];
            celula_bandeira = QTableWidgetItem();
            celula_bandeira.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable);
            bandeira = self.__bandeira__(linha["bandeira"]);
            if bandeira != None:
                celula_bandeira.setData(Qt.DecorationRole, bandeira);
            self.tabela.setItem(i, 0, celula_bandeira);
            celula_bandeira.setData(Qt.UserRole, i);   # indice no modelo: a tabela pode ordenar

            nome = QTableWidgetItem(linha["nome"]);
            nome.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable);
            self.tabela.setItem(i, 1, nome);
            for coluna, chave in ((2, "entidades"), (3, "vinculos")):
                celula = QTableWidgetItem();
                celula.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable);
                celula.setData(Qt.DisplayRole, int(linha[chave]));   # número, para ordenar por valor
                self.tabela.setItem(i, coluna, celula);

        if len(resumo) == 0:
            self.explicacao.setText(
                "Nenhum país neste mapa. Um país é uma entidade com o sub-tipo “country” — "
                "é o que o script/country_seed.py grava, e o que o combo de sub-tipo oferece.");
            return;
        faltam = regional.sem_bandeira(resumo);
        texto = ("%d país(es) neste mapa, do mais tocado ao menos. "
                 "“Entidades” conta quantas caixas distintas se ligam a ele, não quantos vínculos."
                 % len(resumo));
        if faltam > 0:
            # Avisa em vez de desenhar buraco: bandeira que falta e dado que falta.
            texto = texto + "  %d sem bandeira (rode o script/country_seed.py)." % faltam;
        self.explicacao.setText(texto);

    def __abrir__(self, linha, _coluna):
        celula = self.tabela.item(linha, 0);
        if celula == None:
            return;
        indice = celula.data(Qt.UserRole);
        if indice == None or indice >= len(self.linhas):
            return;
        if self.form == None:
            return;
        self.form.entity_double_click(self.linhas[indice]["caixa"]);
        self.form.redesenhar();
