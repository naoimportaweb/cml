import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QDate,  
                            QSaveFile, QTextStream, Qt, Slot, QRegularExpression)
from PySide6.QtGui import QAction, QIcon, QKeySequence, QTextCharFormat, QSyntaxHighlighter, QFont
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QTabWidget, QComboBox, QTableWidgetItem, QHeaderView,
                               QMdiArea, QMessageBox, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

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
        CustomVLayout.widget_linha(self, self.page_url, [self.lbl_wikipedia, self.txt_wikipedia] );
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