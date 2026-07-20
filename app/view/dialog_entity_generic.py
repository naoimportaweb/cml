import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QDate,  QSaveFile, QTextStream, Qt, Slot, QRegularExpression)
from PySide6.QtGui import QAction, QIcon, QKeySequence, QTextCharFormat, QSyntaxHighlighter, QFont
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QTabWidget, QComboBox, QTableWidgetItem, QHeaderView, QMdiArea, QMessageBox, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from view.ui.customvlayout import CustomVLayout;
from view.dialogreference import DialogReference;
from view.dialog_classification import DialogClassification;
from classlib.configuration import Configuration;
from classlib.culture import Culture;
from view.dialog_enityts_merge import DialogEntitysMerge;
from view.ui.qeditorplus import QEditorPlus;
from view.ui.qbot import QBot;
from view.ui.qimages import QImages;

class DialogEntityGeneric(QDialog):
    def __init__(self, form, obj):
        super().__init__(form);
        self.doxxing_show = False;
        self.obj = obj;
        self.tab = QTabWidget();  
        self.reclass = [];
        if self.obj.entity.etype == "person":
            self.reclass.append("Organization");
            self.reclass.append("Other");
        elif self.obj.entity.etype == "organization":
            self.reclass.append("Person");
            self.reclass.append("Other");
        elif self.obj.entity.etype == "other":
            self.reclass.append("Person");
            self.reclass.append("Organization");

    def panelDescricao(self):
        self.page_rel = CustomVLayout.widget_tab( self.tab, "Details");
        # todo tipo tem texto explicativo.
        self.lbl_text = QLabel("Full Name");
        self.txt_text = QLineEdit();
        self.txt_text.setFont( Configuration.instancia().getFont() );
        self.txt_text.setText( self.obj.entity.text ) ;
        self.txt_text.editingFinished.connect(self.txt_text_changed)
        self.btn_merge = QPushButton("Merge entity");
        self.btn_merge.setFont( Configuration.instancia().getFont() );
        self.btn_merge.clicked.connect(self.btn_merge_click);
        CustomVLayout.widget_linha(self, self.page_rel, [self.lbl_text, self.txt_text, self.btn_merge] );
        self.btn_merge.setVisible( len( self.obj.duplicate() ) );
        
        #alguns campos especiais para cada tipo de entidade
        if self.obj.entity.etype == "person":
            self.__panelNickname__("Nickname");
        elif self.obj.entity.etype == "other":
            self.__panelNickname__("Short name");
        elif self.obj.entity.etype == "organization":
            self.__panelNickname__("Acronym");
        
        # descricao também é para todso
        self.txt_descricao = QEditorPlus();
        #self.txt_descricao.setFont( Configuration.instancia().getFont() );
        self.txt_descricao.setPlainText( self.obj.entity.full_description );
        #self.txt_descricao.setLineWrapMode(QTextEdit.NoWrap);
        self.txt_descricao.textChanged.connect(self.txt_descricao_changed)
        #self.txt_descricao.focusOutEvent.connect(self.txt_descricao_finish );
        #self.txt_descricao.setLineWrapMode(QTextEdit.WidgetWidth);  
        self.page_rel.addWidget( self.txt_descricao );
        
    
    def btn_merge_lixo_click(self):
        self.txt_descricao_finish();
    
    def panelUrls(self):
        self.page_url = CustomVLayout.widget_tab( self.tab, "URLs");
        self.lbl_wikipedia = QLabel("Wikipedia");
        self.txt_wikipedia = QLineEdit();
        self.txt_wikipedia.setFont( Configuration.instancia().getFont() );
        self.txt_wikipedia.setText( self.obj.entity.wikipedia ) ;
        self.txt_wikipedia.textChanged.connect(self.txt_wikipedia_changed)
        qb = QBot(self, self.obj.entity, "bot/brazil/wikipedia/config.json");
        CustomVLayout.widget_linha(self, self.page_url, [self.lbl_wikipedia, self.txt_wikipedia, qb] );
        # Procura referencias para esta entidade: base (confiavel) + web (a revisar).
        self.lbl_buscaref = QLabel("Referências");
        qb_ref = QBot(self, self.obj.entity, "bot/brazil/referencias/config.json");
        CustomVLayout.widget_linha(self, self.page_url, [self.lbl_buscaref, qb_ref] );
        self.lbl_official = QLabel("Official Website:");
        self.txt_official = QLineEdit();
        self.txt_official.setFont( Configuration.instancia().getFont() );
        self.txt_official.setText( self.obj.entity.default_url ) ;
        self.txt_official.textChanged.connect(self.txt_official_changed)
        CustomVLayout.widget_linha(self, self.page_url, [self.lbl_official, self.txt_official] );
    
    def panelDoxxing(self):
        if self.obj.__class__.__name__ != "Person":
            return;
        self.page_dox = CustomVLayout.widget_tab( self.tab, "DX");
        self.txt_doxxing = QEditorPlus();
        self.txt_doxxing.setPlainText( self.obj.doxxing );
        self.txt_doxxing.textChanged.connect(self.txt_doxxing_changed)
        self.page_dox.addWidget( self.txt_doxxing );
        #btn_campo_doxxing = QPushButton("Exibir campo/ocultar campo");
        #btn_campo_doxxing.setFont( Configuration.instancia().getFont() );
        #btn_campo_doxxing.clicked.connect(self.btn_campo_doxxing_click);
        #self.txt_doxxing.setVisible( self.doxxing_show );
        #self.page_dox.addWidget( btn_campo_doxxing );
    
    def panelReferences(self):
        self.page_ref = CustomVLayout.widget_tab( self.tab, "References");
        btn_reference_add = QPushButton("Add");
        btn_reference_del = QPushButton("Remove");
        btn_reference_add.setFont( Configuration.instancia().getFont() );
        btn_reference_del.setFont( Configuration.instancia().getFont() );
        btn_reference_add.clicked.connect(self.btn_reference_add_click);
        btn_reference_del.clicked.connect(self.btn_reference_del_click);
        CustomVLayout.widget_linha(self, self.page_ref, [btn_reference_add, btn_reference_del] );
        self.table_reference = CustomVLayout.widget_tabela(self, ["Title"], tamanhos=[QHeaderView.Stretch], double_click=self.table_reference_click);
        self.page_ref.addWidget(self.table_reference);
        self.table_reference_load();

    def panelImages(self):
        # Aba de imagens (lista + rosto). O QImages carrega e grava sozinho, na hora.
        self.page_img = CustomVLayout.widget_tab( self.tab, "Images");
        self.page_img.addWidget( QImages(self, self.obj.entity, with_face=True) );

    def panelClassification(self):
        self.page_cls = CustomVLayout.widget_tab( self.tab, "Classification");
        btn_class_add = QPushButton("Add");
        btn_class_del = QPushButton("Remove");
        btn_class_add.setFont( Configuration.instancia().getFont() );
        btn_class_del.setFont( Configuration.instancia().getFont() );
        btn_class_add.clicked.connect(self.btn_class_add_click);
        btn_class_del.clicked.connect(self.btn_class_del_click);
        CustomVLayout.widget_linha(self, self.page_cls, [btn_class_add, btn_class_del] );
        self.table_class = CustomVLayout.widget_tabela(self, ["Classification", "Value", "Start", "End"], tamanhos=[QHeaderView.Stretch,QHeaderView.Stretch,QHeaderView.Stretch, QHeaderView.Stretch], double_click=self.table_class_click);
        self.page_cls.addWidget(self.table_class);
        self.table_class_load();
    
    def panelActioins(self):
        self.page_act = CustomVLayout.widget_tab( self.tab, "Actions");
        # So Other tem sub-tipo. Aqui e apenas SELECAO — cadastrar/editar sub-tipos e o rosto
        # default e na tela global (menu/toolbar "Sub-tipos"), nao dentro da entidade.
        if self.obj.entity.etype == "other":
            self.__subtype_selector__();
        self.cmb_type = QComboBox()
        self.cmb_type.setFont( Configuration.instancia().getFont() );
        for buffer in self.reclass:
            self.cmb_type.addItem( buffer )
        btn_alterar_type = QPushButton("Switch to type");
        btn_alterar_type.setFont( Configuration.instancia().getFont() );
        btn_alterar_type.clicked.connect(self.btn_alterar_type_click);
        CustomVLayout.widget_linha(self, self.page_act, [self.cmb_type, btn_alterar_type] );
        btn_remover = QPushButton("Remove");
        btn_remover.setFont( Configuration.instancia().getFont() );
        btn_remover.clicked.connect(self.btn_remover_click);
        CustomVLayout.widget_linha(self, self.page_act, [btn_remover] );

        # INCORPORAR: absorve outro elemento do mapa (referencias + vinculos repontados),
        # mantendo o nome e o tipo deste. Nao e o "Merge entity" (dedup global por nome).
        # So aparece para entidades (nao para vinculos), e so se houver outro elemento.
        if self.obj.entity.etype != "link":
            self.lbl_incorp = QLabel("Incorporate element:");
            self.lbl_incorp.setFont( Configuration.instancia().getFont() );
            self.cmb_incorp = QComboBox();
            self.cmb_incorp.setFont( Configuration.instancia().getFont() );
            self.btn_incorp = QPushButton("Incorporate");
            self.btn_incorp.setFont( Configuration.instancia().getFont() );
            self.btn_incorp.clicked.connect(self.btn_incorporar_click);
            CustomVLayout.widget_linha(self, self.page_act, [self.lbl_incorp, self.cmb_incorp, self.btn_incorp] );
            self.__incorp_load__();

    def __incorp_load__(self):
        # Lista os OUTROS elementos-entidade do mapa (nao este, nao vinculos) como candidatos.
        self.incorp_alvos = [];
        self.cmb_incorp.clear();
        candidatos = [ el for el in self.obj.mapa.elements
                       if el is not self.obj and el.entity.etype != "link" ];
        candidatos.sort( key=lambda el: str(el.entity.text or "").lower() );
        for el in candidatos:
            self.incorp_alvos.append( el );
            nome = str(el.entity.text or "(sem nome)");
            self.cmb_incorp.addItem( "%s  [%s]" % (nome, el.entity.etype) );
        vazio = ( len(self.incorp_alvos) == 0 );
        self.cmb_incorp.setEnabled( not vazio );
        self.btn_incorp.setEnabled( not vazio );
        if vazio:
            self.cmb_incorp.addItem( "(nenhum outro elemento no mapa)" );

    def btn_incorporar_click(self):
        if not self.incorp_alvos:
            return;
        alvo = self.incorp_alvos[ self.cmb_incorp.currentIndex() ];
        nome_alvo = str(alvo.entity.text or "(sem nome)");
        resp = QMessageBox.question(self, "Incorporate",
            ("Incorporar \"%s\" em \"%s\"?\n\nAs referências e os vínculos de \"%s\" passam "
             "para \"%s\"; \"%s\" sai do mapa. Seu nome e tipo não mudam.") %
            (nome_alvo, str(self.obj.entity.text or ""), nome_alvo, str(self.obj.entity.text or ""), nome_alvo),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No);
        if resp != QMessageBox.Yes:
            return;
        try:
            self.obj.mapa.incorporate( self.obj, alvo );
        except Exception as e:
            QMessageBox.warning(self, "Falha", str(e));
            return;
        # atualiza a UI: referencias novas na aba References e o combo sem o alvo incorporado.
        if hasattr(self, "table_reference"):
            self.table_reference_load();
        self.__incorp_load__();
        QMessageBox.information(self, "Incorporate",
            "\"%s\" incorporado. Salve o mapa para gravar." % nome_alvo);

    def __subtype_selector__(self):
        # Combo somente-leitura de sub-tipos existentes (buscados do servidor). Selecionar
        # grava na hora (Entity.set_subetype). "(nenhum)" limpa o sub-tipo.
        lbl = QLabel("Sub-tipo:");
        lbl.setFont( Configuration.instancia().getFont() );
        self.cmb_subtype = QComboBox();
        self.cmb_subtype.setFont( Configuration.instancia().getFont() );
        self.subtype_nomes = [""];
        self.cmb_subtype.addItem("(nenhum)");
        try:
            for s in self.obj.entity.load_subetypes():
                self.cmb_subtype.addItem( s.get("name") or "" );
                self.subtype_nomes.append( s.get("name") or "" );
        except Exception as e:
            print("subtype selector: falha ao carregar:", e);
        atual = self.obj.entity.sub_etype_name or "";
        if atual in self.subtype_nomes:
            self.cmb_subtype.setCurrentIndex( self.subtype_nomes.index( atual ) );
        self.cmb_subtype.currentIndexChanged.connect( self.__subtype_changed__ );
        CustomVLayout.widget_linha(self, self.page_act, [lbl, self.cmb_subtype] );

    def __subtype_changed__(self):
        nome = self.subtype_nomes[ self.cmb_subtype.currentIndex() ];
        js = self.obj.entity.set_subetype( nome );
        if not js or not js.get("status"):
            QMessageBox.warning(self, "Falha", "Não foi possível salvar o sub-tipo no servidor.");

    def __panelNickname__(self, label_small_label):
        self.lbl_text_small = QLabel( label_small_label );
        self.txt_text_small = QLineEdit();
        self.txt_text_small.setFont( Configuration.instancia().getFont() );
        self.txt_text_small.setText( self.obj.entity.small_label ) ;
        self.txt_text_small.textChanged.connect(self.txt_text_small_changed)
        CustomVLayout.widget_linha(self, self.page_rel, [self.lbl_text_small, self.txt_text_small] );

    # TABLE EVENTS REFERENCES
    def table_reference_load(self):
        self.table_reference.setRowCount( len( self.obj.entity.references ) );
        for i in range(len( self.obj.entity.references )):
            self.table_reference.setItem( i, 0, QTableWidgetItem( self.obj.entity.references[i].title ) );
    
    def table_reference_click(self):
        element = self.obj.entity.references[ self.table_reference.index() ];
        form = DialogReference(self, self.obj, reference=element);
        form.exec();
        self.table_reference_load();

    def btn_reference_del_click(self):
        index = self.table_reference.index();
        self.obj.entity.references.pop( index );
        self.table_reference_load();
    
    def btn_reference_add_click(self):
        form = DialogReference(self, self.obj, reference=None);
        form.exec();
        self.table_reference_load();

    def txt_text_small_changed(self):
        self.obj.entity.small_label = self.txt_text_small.text();
    
    def btn_merge_click(self):
        f = DialogEntitysMerge(self, self.obj);
        f.exec();
        return;

    def txt_text_changed(self):
        self.obj.entity.text = self.txt_text.text();
        self.btn_merge.setVisible( len( self.obj.duplicate() )  );
    
    def txt_wikipedia_changed(self):
        self.obj.entity.wikipedia = self.txt_wikipedia.text();

    def txt_official_changed(self):
        self.obj.entity.default_url = self.txt_official.text();

    def txt_descricao_changed(self):
        self.obj.entity.full_description = self.txt_descricao.toPlainText();

    def txt_doxxing_changed(self):
        self.obj.doxxing = self.txt_doxxing.toPlainText();
    
    def btn_remover_click(self):
        self.obj.mapa.delEntity(self.obj);
        self.close();

    def btn_alterar_type_click(self):
        etype = self.reclass[ self.cmb_type.currentIndex() ].lower(); 
        retorno = self.obj.setType( etype );
        if retorno:
            self.close();

    # TABELA DE CLASSIFCAÇÃO
    def table_class_click(self):
        return;
    
    def btn_class_del_click(self):
        self.obj.entity.classification.pop(self.table_class.index());
        self.table_class_load();
        return;
    
    def btn_class_add_click(self):
        d = DialogClassification(self, self.obj.entity);
        d.exec();
        return;
    
    def table_class_load(self):
        self.table_class.setRowCount( len( self.obj.entity.classification ) );
        for i in range(len( self.obj.entity.classification )):
            self.table_class.setItem( i, 0, QTableWidgetItem( self.obj.entity.classification[i]["text_label"] ) );
            self.table_class.setItem( i, 1, QTableWidgetItem( self.obj.entity.classification[i]["text_label_choice"] ) );
            self.table_class.setItem( i, 2, QTableWidgetItem( QDate.fromString(self.obj.entity.classification[i]["start_date"], "yyyy-MM-dd").toString(self.obj.entity.classification[i]["format_date"]) ) );
            self.table_class.setItem( i, 3, QTableWidgetItem( QDate.fromString(self.obj.entity.classification[i]["end_date"], "yyyy-MM-dd").toString(self.obj.entity.classification[i]["format_date"])  ) );
        return;

    #def btn_campo_doxxing_click(self):
    #    self.doxxing_show = not self.doxxing_show;
    #    self.txt_doxxing.setVisible( self.doxxing_show );

    def closeEvent(self, event):
        # Editar a entidade muda o que a caixa desenha (rotulo, descricao, tipo). O engine
        # so redesenha em evento de mouse, entao um merge ou uma troca de nome feita aqui
        # nao apareceria ate o proximo clique no canvas.
        try:
            janela = self.parent() and self.parent().active_mdi_child();
            if janela != None and hasattr(janela, "redesenhar"):
                janela.redesenhar();
        except Exception:
            pass;
        super().closeEvent(event);
