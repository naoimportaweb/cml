import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QHeaderView, QTableWidgetItem, QComboBox,
                               QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );

sys.path.append( ROOT );
sys.path.append("/opt/cml/app/");

from view.ui.customvlayout import CustomVLayout;
from classlib.server import Server;
from classlib.configuration import Configuration;
from classlib.classification import Classification;

class DialogClassification(QDialog):
    def __init__(self, form):
        super().__init__();
        nWidth = int(form.width() * 0.8); nHeight = int(form.height() * 0.6);
        if nWidth > 800:
            nWidth = 800;
        self.setGeometry(form.x() + form.width()/2 - nWidth/2,
            form.y() + form.height()/2 - nHeight/2,
            nWidth, nHeight);

        self.table_classification = None;
        self.setWindowTitle("Search Classification")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        #self.ui_search_relationship();
        self.cmb_type = QComboBox()
        self.cmb_type.setFont( Configuration.instancia().getFont() );
        #self.cmb_type.addItem('Organization')
        #self.cmb_type.addItem('Other')
        self.ui_search_classification();
        self.ui_tabela();
        btn_alterar_type = QPushButton("Select classification");
        btn_alterar_type.setFont( Configuration.instancia().getFont() );
        btn_alterar_type.clicked.connect(self.btn_alterar_type_click);
        CustomVLayout.widget_linha(self, self.layout_principal, [self.cmb_type, btn_alterar_type] );
        #self.ui_tabela();
        
    def ui_search_classification(self):
        layout_server = QGridLayout()
        layout_server.setContentsMargins(20, 20, 20, 20)
        layout_server.setSpacing(10)
        lbl_name = QLabel("Name:")
        lbl_name.setProperty("class", "normal")
        layout_server.addWidget(lbl_name, 1, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setMinimumWidth(500);
        layout_server.addWidget(self.txt_name, 1, 1);
        self.txt_name.editingFinished.connect(self.txt_name_finish);   
        self.layout_principal.addLayout( "search", layout_server );

    def ui_tabela(self):
        layout = QVBoxLayout();
        self.table_classification = CustomVLayout.widget_tabela(self, ["Name"], tamanhos=[QHeaderView.Stretch], double_click=self.table_classification_double);
        layout.addWidget(self.table_classification);
        self.layout_principal.addLayout( "list", layout );

    def txt_name_finish(self):
        c = Classification();
        self.classifications = c.search("%" + self.txt_name.text().strip() + "%");
        self.table_classification.setRowCount( len( self.classifications ) );
        for i in range(len( self.classifications )):
            self.table_classification.setItem( i, 0, QTableWidgetItem( self.classifications[i]["text_label"] ) );
        return;
        #r = MapRelationship();
        #self.mapas = r.search( "%" + self.txt_name.text().strip() + "%");
        #self.mapas.sort(key=lambda x: x["name"]);
        #self.table_maps.setRowCount( len( self.mapas ) );
        #for i in range(len( self.mapas )):
        #    self.table_maps.setItem( i, 0, QTableWidgetItem( self.mapas[i]["username"] ) );
        #    self.table_maps.setItem( i, 1, QTableWidgetItem( self.mapas[i]["name"]) );
    
    def table_classification_double(self):
        for buffer in self.classifications:
            self.cmb_type.addItem( buffer["text_label"] )
        return;
        #r = MapRelationship();
        #if r.load( self.mapas[ self.table_maps.index() ]["id"] ):
        #    self.map = r;
        #    self.close();
    def btn_alterar_type_click(self):
        return;

