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

from classlib.configuration import Configuration;
from view.ui.customvlayout import CustomVLayout;
from view.dialogreference import DialogReference;
from view.dialog_classification import DialogClassification;

class DialogEntityOrganization(QDialog):
    def __init__(self, form, organization):
        super().__init__()
        #self.resize(800, 660);
        nWidth = int(form.width() * 0.8); nHeight = int(form.height() * 0.6);
        if nWidth > 800:
            nWidth = 800;
        self.setGeometry(form.x() + form.width()/2 - nWidth/2,
            form.y() + form.height()/2 - nHeight/2,
            nWidth, nHeight);
        config = Configuration();
        self.setWindowTitle("Organization")
        self.organization = organization;
        self.tab = QTabWidget();  
        self.page_rel = CustomVLayout.widget_tab( self.tab, "Organization");
        self.page_pho = CustomVLayout.widget_tab( self.tab, "Photo");
        self.page_dat = CustomVLayout.widget_tab( self.tab, "Data");
        self.page_ref = CustomVLayout.widget_tab( self.tab, "References");
        self.page_cls = CustomVLayout.widget_tab( self.tab, "Classification");
        self.page_act = CustomVLayout.widget_tab( self.tab, "Actions");
        # ------------------------------------------
        self.lbl_text = QLabel("Name");
        self.txt_text = QLineEdit();
        self.txt_text.setFont(config.getFont());
        self.txt_text.setText( self.organization.entity.text ) ;
        self.txt_text.textChanged.connect(self.txt_text_changed)
        CustomVLayout.widget_linha(self, self.page_rel, [self.lbl_text, self.txt_text] );

        self.lbl_text_small = QLabel("Acronym");
        self.txt_text_small = QLineEdit();
        self.txt_text_small.setFont( Configuration.instancia().getFont() );
        self.txt_text_small.setText( self.organization.entity.small_label ) ;
        self.txt_text_small.textChanged.connect(self.txt_text_small_changed)
        CustomVLayout.widget_linha(self, self.page_rel, [self.lbl_text_small, self.txt_text_small] );
        
        self.txt_descricao = QTextEdit();
        self.txt_descricao.setPlainText( organization.entity.full_description );
        self.txt_descricao.setLineWrapMode(QTextEdit.NoWrap);
        self.txt_descricao.textChanged.connect(self.txt_descricao_changed)
        self.txt_descricao.setFont(config.getFont());
        self.txt_descricao.setLineWrapMode(QTextEdit.WidgetWidth);  
        self.page_rel.addWidget( self.txt_descricao );
        # --------------------------------------------------
        btn_class_add = QPushButton("Add");
        btn_class_del = QPushButton("Remove");
        btn_class_add.setFont( Configuration.instancia().getFont() );
        btn_class_del.setFont( Configuration.instancia().getFont() );
        btn_class_add.clicked.connect(self.btn_class_add_click);
        btn_class_del.clicked.connect(self.btn_class_del_click);
        CustomVLayout.widget_linha(self, self.page_cls, [btn_class_add, btn_class_del] );
        #self.table_class = CustomVLayout.widget_tabela(self, ["Classification", "Value"], tamanhos=[QHeaderView.Stretch, QHeaderView.Stretch], double_click=self.table_class_click);
        self.table_class = CustomVLayout.widget_tabela(self, ["Classification", "Value", "Start", "End"], tamanhos=[QHeaderView.Stretch,QHeaderView.Stretch,QHeaderView.Stretch, QHeaderView.Stretch], double_click=self.table_class_click);
        self.page_cls.addWidget(self.table_class);
        self.table_class_load();
        #-------------------------------------------
        self.cmb_type = QComboBox()
        self.cmb_type.setFont( Configuration.instancia().getFont() );
        self.cmb_type.addItem('Person')
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
        layout = QVBoxLayout();
        layout.addWidget( self.tab           );
        self.setLayout(   layout             );

    def table_reference_load(self):
        self.table_reference.setRowCount( len( self.organization.entity.references ) );
        for i in range(len( self.organization.entity.references )):
            self.table_reference.setItem( i, 0, QTableWidgetItem( self.organization.entity.references[i].title ) );
    
    def table_reference_click(self):
        element = self.organization.entity.references[ self.table_reference.index() ];
        form = DialogReference(self, self.organization, reference=element);
        form.exec();
        self.table_reference_load();

    def btn_reference_del_click(self):
        index = self.table_reference.index();
        self.organization.entity.references.pop( index );
        self.table_reference_load();
    
    def btn_reference_add_click(self):
        form = DialogReference(self, self.organization, reference=None);
        form.exec();
        self.table_reference_load()

    def txt_text_changed(self):
        self.organization.entity.text = self.txt_text.text();

    def txt_text_small_changed(self):
        self.organization.entity.small_label = self.txt_text_small.text();

    def btn_remover_click(self):
        self.organization.mapa.delEntity(self.organization);
        self.close();
    
    def txt_descricao_changed(self):
        self.organization.entity.full_description = self.txt_descricao.toPlainText();
    
    def btn_alterar_type_click(self):
        etype = "";
        if self.cmb_type.currentIndex() == 0:
            etype = "person";
        elif self.cmb_type.currentIndex() == 1:
            etype = "other";   
        retorno = self.organization.setType( etype );
        if retorno:
            self.close();
    def table_class_click(self):
        return;
    
    def btn_class_del_click(self):
        self.organization.entity.classification.pop(self.table_class.index());
        self.table_class_load();
        return;
    
    def btn_class_add_click(self):
        d = DialogClassification(self, self.organization.entity);
        d.exec();
        return;
    
    def table_class_load(self):
        self.table_class.setRowCount( len( self.organization.entity.classification ) );
        for i in range(len( self.organization.entity.classification )):
            self.table_class.setItem( i, 0, QTableWidgetItem( self.organization.entity.classification[i]["text_label"] ) );
            self.table_class.setItem( i, 1, QTableWidgetItem( self.organization.entity.classification[i]["text_label_choice"] ) );
            self.table_class.setItem( i, 2, QTableWidgetItem( QDate.fromString(self.organization.entity.classification[i]["start_date"], "yyyy-MM-dd").toString(self.organization.entity.classification[i]["format_date"]) ) );
            self.table_class.setItem( i, 3, QTableWidgetItem( QDate.fromString(self.organization.entity.classification[i]["end_date"], "yyyy-MM-dd").toString(self.organization.entity.classification[i]["format_date"])  ) );
        return;