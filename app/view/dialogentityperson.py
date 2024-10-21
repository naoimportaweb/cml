import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QDate,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QTabWidget, QComboBox, QTableWidgetItem, QHeaderView,
                               QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from view.ui.customvlayout import CustomVLayout;
from view.dialogreference import DialogReference;
from view.dialog_classification import DialogClassification;
from classlib.configuration import Configuration;
from view.dialog_enityts_merge import DialogEntitysMerge;

class DialogEntityPerson(QDialog):
    def __init__(self, form, person):
        super().__init__()
        nWidth = int(form.width() * 0.8); nHeight = int(form.height() * 0.6);
        if nWidth > 800:
            nWidth = 800;
        self.setGeometry(form.x() + form.width()/2 - nWidth/2,
            form.y() + form.height()/2 - nHeight/2,
            nWidth, nHeight);

        self.setWindowTitle("Person")
        self.person = person;
        self.tab = QTabWidget();  
        self.page_rel = CustomVLayout.widget_tab( self.tab, "Person");
        self.page_pho = CustomVLayout.widget_tab( self.tab, "Photo");
        self.page_url = CustomVLayout.widget_tab( self.tab, "URLs");
        self.page_dox = CustomVLayout.widget_tab( self.tab, "Doxxing");
        self.page_ref = CustomVLayout.widget_tab( self.tab, "References");
        self.page_cls = CustomVLayout.widget_tab( self.tab, "Classification");
        self.page_act = CustomVLayout.widget_tab( self.tab, "Actions");
        # ------------------------------------------
        self.lbl_text = QLabel("Full Name");
        self.txt_text = QLineEdit();
        self.txt_text.setFont( Configuration.instancia().getFont() );
        self.txt_text.setText( self.person.entity.text ) ;
        self.txt_text.textChanged.connect(self.txt_text_changed)
        self.btn_merge = QPushButton("Merge entity");
        self.btn_merge.setFont( Configuration.instancia().getFont() );
        self.btn_merge.clicked.connect(self.btn_merge_click);
        CustomVLayout.widget_linha(self, self.page_rel, [self.lbl_text, self.txt_text, self.btn_merge] );
        self.btn_merge.setVisible( len( self.person.duplicate() ) );

        self.lbl_text_small = QLabel("Nickname");
        self.txt_text_small = QLineEdit();
        self.txt_text_small.setFont( Configuration.instancia().getFont() );
        self.txt_text_small.setText( self.person.entity.small_label ) ;
        self.txt_text_small.textChanged.connect(self.txt_text_small_changed)
        CustomVLayout.widget_linha(self, self.page_rel, [self.lbl_text_small, self.txt_text_small] );
        
        self.txt_descricao = QTextEdit();
        self.txt_descricao.setFont( Configuration.instancia().getFont() );
        self.txt_descricao.setPlainText( person.entity.full_description );
        self.txt_descricao.setLineWrapMode(QTextEdit.NoWrap);
        self.txt_descricao.textChanged.connect(self.txt_descricao_changed)
        self.txt_descricao.setLineWrapMode(QTextEdit.WidgetWidth);  
        self.page_rel.addWidget( self.txt_descricao );
        # --------------------------------------------------
        self.lbl_wikipedia = QLabel("Wikipedia");
        self.txt_wikipedia = QLineEdit();
        self.txt_wikipedia.setFont( Configuration.instancia().getFont() );
        self.txt_wikipedia.setText( self.person.entity.wikipedia ) ;
        self.txt_wikipedia.textChanged.connect(self.txt_wikipedia_changed)
        CustomVLayout.widget_linha(self, self.page_url, [self.lbl_wikipedia, self.txt_wikipedia] );
        #-----------------
        self.txt_doxxing = QTextEdit();
        self.txt_doxxing.setFont( Configuration.instancia().getFont() );
        self.txt_doxxing.setPlainText( person.doxxing );
        self.txt_doxxing.setLineWrapMode(QTextEdit.NoWrap);
        self.txt_doxxing.textChanged.connect(self.txt_doxxing_changed)
        self.txt_doxxing.setLineWrapMode(QTextEdit.WidgetWidth);  
        self.page_dox.addWidget( self.txt_doxxing );
        #-------------------------------------------
        self.cmb_type = QComboBox()
        self.cmb_type.setFont( Configuration.instancia().getFont() );
        self.cmb_type.addItem('Organization')
        self.cmb_type.addItem('Other')
        btn_alterar_type = QPushButton("Switch to type");
        btn_alterar_type.setFont( Configuration.instancia().getFont() );
        btn_alterar_type.clicked.connect(self.btn_alterar_type_click);
        CustomVLayout.widget_linha(self, self.page_act, [self.cmb_type, btn_alterar_type] );
        btn_remover = QPushButton("Remove");
        btn_remover.setFont( Configuration.instancia().getFont() );
        btn_remover.clicked.connect(self.btn_remover_click);
        CustomVLayout.widget_linha(self, self.page_act, [btn_remover] );
        #-------------------------------------------
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
        #layout = QVBoxLayout();
        #layout.addWidget( self.tab           );
        #self.setLayout(   layout             );
        #------------------------------------------
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
        
        layout = QVBoxLayout();
        layout.addWidget( self.tab           );
        self.setLayout(   layout             );

    def table_reference_load(self):
        self.table_reference.setRowCount( len( self.person.entity.references ) );
        for i in range(len( self.person.entity.references )):
            self.table_reference.setItem( i, 0, QTableWidgetItem( self.person.entity.references[i].title ) );
    
    def table_reference_click(self):
        element = self.person.entity.references[ self.table_reference.index() ];
        form = DialogReference(self, self.person, reference=element);
        form.exec();
        self.table_reference_load();

    def btn_reference_del_click(self):
        index = self.table_reference.index();
        self.person.entity.references.pop( index );
        self.table_reference_load();
    
    def btn_reference_add_click(self):
        form = DialogReference(self, self.person, reference=None);
        form.exec();
        self.table_reference_load()

    def txt_text_small_changed(self):
        self.person.entity.small_label = self.txt_text_small.text();
    
    def btn_merge_click(self):
        f = DialogEntitysMerge(self, self.person);
        f.exec();
        return;

    def txt_text_changed(self):
        self.person.entity.text = self.txt_text.text();
        self.btn_merge.setVisible( len( self.person.duplicate() )  );
    
    def txt_wikipedia_changed(self):
        self.person.entity.wikipedia = self.txt_wikipedia.text();

    def txt_descricao_changed(self):
        self.person.entity.full_description = self.txt_descricao.toPlainText();

    def txt_doxxing_changed(self):
        self.person.doxxing = self.txt_doxxing.toPlainText();
    
    def btn_remover_click(self):
        self.person.mapa.delEntity(self.person);
        self.close();

    def btn_alterar_type_click(self):
        etype = "";
        if self.cmb_type.currentIndex() == 0:
            etype = "organization";
        elif self.cmb_type.currentIndex() == 1:
            etype = "other";   
        retorno = self.person.setType( etype );
        if retorno:
            self.close();
    def table_class_click(self):
        return;
    
    def btn_class_del_click(self):
        self.person.entity.classification.pop(self.table_class.index());
        self.table_class_load();
        return;
    
    def btn_class_add_click(self):
        d = DialogClassification(self, self.person.entity);
        d.exec();
        return;
    
    def table_class_load(self):
        self.table_class.setRowCount( len( self.person.entity.classification ) );
        for i in range(len( self.person.entity.classification )):
            self.table_class.setItem( i, 0, QTableWidgetItem( self.person.entity.classification[i]["text_label"] ) );
            self.table_class.setItem( i, 1, QTableWidgetItem( self.person.entity.classification[i]["text_label_choice"] ) );
            self.table_class.setItem( i, 2, QTableWidgetItem( QDate.fromString(self.person.entity.classification[i]["start_date"], "yyyy-MM-dd").toString(self.person.entity.classification[i]["format_date"]) ) );
            self.table_class.setItem( i, 3, QTableWidgetItem( QDate.fromString(self.person.entity.classification[i]["end_date"], "yyyy-MM-dd").toString(self.person.entity.classification[i]["format_date"])  ) );
        return;
