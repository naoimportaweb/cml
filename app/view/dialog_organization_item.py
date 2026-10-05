import os, sys, inspect;

from PySide6.QtCore import (Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QAbstractItemView, QHeaderView, QMessageBox, QTableWidget,
                               QTableWidgetItem, QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from classlib.configuration import Configuration;
from view.dialog_entity_find import DialogEntityFind;

COLUNAS = ["Nome", "Tipo"];


class DialogOrganizationItem(QDialog):
    """Item do organograma: o rotulo (o cargo, a area, a diretoria) e QUEM o ocupa.

    O que mudou em relacao a versao antiga, e por que:
      - o botao Remove era um metodo vazio: dava para pendurar entidade e nunca tirar;
      - havia uma caixa de descricao grande cujo textChanged era "return" -- quem escrevesse
        nela perdia tudo ao fechar, sem aviso. Caixa que nao grava e pior que caixa que nao
        existe, entao ela saiu;
      - as abas separavam "Organization"/"Elements"/"Actions" com uma delas vazia.

    As entidades entram SEMPRE pela busca (DialogEntityFind), nunca digitadas: entidade e
    global no CML, e criar uma nova com o mesmo nome e o que o merge_to tem de limpar depois.
    """

    def __init__(self, form, element, graphic):
        super().__init__(form)
        self.element = element;
        self.graphic = graphic;
        self.setWindowTitle("Item do organograma");
        self.setMinimumSize(620, 460);

        layout = QVBoxLayout(self);
        layout.setContentsMargins(18, 16, 18, 16);
        layout.setSpacing(8);

        layout.addWidget(QLabel("Cargo, área ou unidade"));
        self.txt_text = QLineEdit();
        self.txt_text.setFont( Configuration.instancia().getFont() );
        self.txt_text.setText( self.element.text_label );
        self.txt_text.setPlaceholderText("ex.: Diretoria Financeira");
        self.txt_text.textChanged.connect(self.txt_text_changed);
        layout.addWidget(self.txt_text);

        layout.addSpacing(10);
        cabecalho = QHBoxLayout();
        cabecalho.addWidget(QLabel("Quem ocupa"));
        cabecalho.addStretch(1);
        self.btn_ele_add = QPushButton("Buscar entidade...");
        self.btn_ele_add.setProperty("destaque", "sim");
        self.btn_ele_add.setAutoDefault(False);
        self.btn_ele_add.clicked.connect(self.btn_ele_add_click);
        self.btn_ele_del = QPushButton("Remover");
        self.btn_ele_del.setAutoDefault(False);
        self.btn_ele_del.clicked.connect(self.btn_ele_del_click);
        cabecalho.addWidget(self.btn_ele_add);
        cabecalho.addWidget(self.btn_ele_del);
        layout.addLayout(cabecalho);

        self.table_ele = QTableWidget(0, len(COLUNAS));
        self.table_ele.setHorizontalHeaderLabels(COLUNAS);
        self.table_ele.setEditTriggers(QAbstractItemView.NoEditTriggers);
        self.table_ele.setSelectionBehavior(QAbstractItemView.SelectRows);
        self.table_ele.setSelectionMode(QAbstractItemView.SingleSelection);
        self.table_ele.setAlternatingRowColors(True);
        self.table_ele.verticalHeader().setVisible(False);
        self.table_ele.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch);
        self.table_ele.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents);
        layout.addWidget(self.table_ele);

        self.aviso = QLabel("");
        self.aviso.setWordWrap(True);
        layout.addWidget(self.aviso);

        botoes = QDialogButtonBox(QDialogButtonBox.Close);
        botoes.rejected.connect(self.close);
        layout.addWidget(botoes);

        self.table_ele_load();
        self.txt_text.setFocus();
        self.txt_text.selectAll();

    # ------------------------------------------------------------------ acoes

    def txt_text_changed(self):
        self.element.text_label = self.txt_text.text();

    def btn_ele_add_click(self):
        janela = DialogEntityFind(self);
        janela.exec();
        if janela.entity == None:
            return;
        # Mesma entidade duas vezes no mesmo item nao diz nada e polui a caixa no desenho.
        for ja in self.element.entitys:
            if ja.entity.id == janela.entity.id:
                self.__avisar__("%s já está neste item." % janela.entity.getText());
                return;
        self.element.addEntity( janela.entity );
        self.table_ele_load();
        self.__avisar__("");

    def btn_ele_del_click(self):
        linha = self.table_ele.currentRow();
        if linha < 0:
            self.__avisar__("Escolha na lista quem deve sair.");
            return;
        nome = self.element.entitys[linha].getText();
        if QMessageBox.question(self, "Remover", "Tirar \"%s\" deste item?" % nome,
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return;
        # Sai do ITEM, nao do banco: a entidade continua existindo e nos outros mapas.
        self.element.delEntity(linha);
        self.table_ele_load();
        self.__avisar__("\"%s\" saiu deste item — a entidade continua no banco." % nome);

    def __avisar__(self, texto):
        self.aviso.setText(texto);

    def table_ele_load(self):
        self.table_ele.setRowCount( len( self.element.entitys ) );
        for i in range(len( self.element.entitys )):
            celula = QTableWidgetItem( self.element.entitys[i].getText() );
            celula.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable);
            self.table_ele.setItem( i, 0, celula );
            tipo = QTableWidgetItem( self.element.entitys[i].entity.etype or "" );
            tipo.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable);
            self.table_ele.setItem( i, 1, tipo );
        self.btn_ele_del.setEnabled( len(self.element.entitys) > 0 );
