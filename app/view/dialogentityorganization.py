import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings,
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

class DialogEntityOrganization(QDialog):
    def __init__(self, form, organizagion):
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
        self.organizagion = organizagion;
        self.tab = QTabWidget();  
        self.page_rel = CustomVLayout.widget_tab( self.tab, "Organization");
        self.page_pho = CustomVLayout.widget_tab( self.tab, "Photo");
        self.page_dat = CustomVLayout.widget_tab( self.tab, "Data");
        self.page_ref = CustomVLayout.widget_tab( self.tab, "References");
        self.page_act = CustomVLayout.widget_tab( self.tab, "Actions");
        # ------------------------------------------
        self.lbl_text = QLabel("Text");
        self.txt_text = QLineEdit();
        self.txt_text.setFont(config.getFont());
        self.txt_text.setText( self.organizagion.entity.text ) ;
        self.txt_text.textChanged.connect(self.txt_text_changed)
        CustomVLayout.widget_linha(self, self.page_rel, [self.lbl_text, self.txt_text] );
        
        self.txt_descricao = QTextEdit();
        self.txt_descricao.setPlainText( organizagion.entity.full_description );
        self.txt_descricao.setLineWrapMode(QTextEdit.NoWrap);
        self.txt_descricao.textChanged.connect(self.txt_descricao_changed)
        self.txt_descricao.setFont(config.getFont());
        self.txt_descricao.setLineWrapMode(QTextEdit.WidgetWidth);  
        self.page_rel.addWidget( self.txt_descricao );
        # --------------------------------------------------
        #-------------------------------------------
        self.cmb_type = QComboBox()
        self.cmb_type.setFont( Configuration.instancia().getFont() );
        self.cmb_type.addItem('Person')
        self.cmb_type.addItem('Other')
        btn_alterar_type = QPushButton("Switch to type");
        btn_alterar_type.setFont( Configuration.instancia().getFont() );
        btn_alterar_type.clicked.connect(self.btn_alterar_type_click);
        CustomVLayout.widget_linha(self, self.page_act, [self.cmb_type, btn_alterar_type] );
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
        self.table_reference.setRowCount( len( self.organizagion.entity.references ) );
        for i in range(len( self.organizagion.entity.references )):
            self.table_reference.setItem( i, 0, QTableWidgetItem( self.organizagion.entity.references[i].title ) );
    
    def table_reference_click(self):
        element = self.organizagion.entity.references[ self.table_reference.index() ];
        form = DialogReference(self, self.organizagion, reference=element);
        form.exec();
        self.table_reference_load();

    def btn_reference_del_click(self):
        index = self.table_reference.index();
        self.organizagion.entity.references.pop( index );
        self.table_reference_load();
    
    def btn_reference_add_click(self):
        form = DialogReference(self, self.organizagion, reference=None);
        form.exec();
        self.table_reference_load()

    def txt_text_changed(self):
        self.organizagion.entity.text = self.txt_text.text();
    
    def txt_descricao_changed(self):
        self.organizagion.entity.full_description = self.txt_descricao.toPlainText();
    def btn_alterar_type_click(self):
        etype = "";
        if self.cmb_type.currentIndex() == 0:
            etype = "person";
        elif self.cmb_type.currentIndex() == 1:
            etype = "other";   
        retorno = self.organizagion.setType( etype );
        if retorno:
            self.close();
