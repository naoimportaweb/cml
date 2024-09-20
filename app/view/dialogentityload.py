import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QHeaderView, QTableWidgetItem,
                               QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );

sys.path.append( ROOT );
sys.path.append("/opt/cml/app/");

from view.ui.customvlayout import CustomVLayout;
from classlib.server import Server;
from classlib.maprelationship import MapRelationship;
from classlib.entitys import Person, Organization, Link, Rectangle

class DialogEntityLoad(QDialog):
    def __init__(self, form):
        super().__init__();
        #self.map = None;
        self.form = form;
        self.entitys = None;
        self.entity = None;
        self.setWindowTitle("Entity Search")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.ui_search_relationship();
        self.ui_tabela();
        
    def ui_search_relationship(self):
        layout_server = QGridLayout();
        layout_server.setContentsMargins(20, 20, 20, 20);
        layout_server.setSpacing(10);
        lbl_name = QLabel("Entity name:");
        lbl_name.setProperty("class", "normal");
        layout_server.addWidget(lbl_name, 1, 0);
        self.txt_name = QLineEdit();
        self.txt_name.setMinimumWidth(500);
        layout_server.addWidget(self.txt_name, 1, 1);
        self.txt_name.editingFinished.connect(self.txt_name_finish);   
        self.layout_principal.addLayout( "search", layout_server );

    def ui_tabela(self):
        layout = QVBoxLayout();
        self.table_maps = CustomVLayout.widget_tabela(self, ["Entity"], tamanhos=[QHeaderView.Stretch], double_click=self.table_maps_double);
        layout.addWidget(self.table_maps);
        self.layout_principal.addLayout( "list", layout );

    def txt_name_finish(self):
        r = MapRelationship();
        self.entitys = r.search_entity( "%" + self.txt_name.text().strip() + "%");
        self.table_maps.setRowCount( len( self.entitys ) );
        for i in range(len( self.entitys )):
            self.table_maps.setItem( i, 0, QTableWidgetItem( self.entitys[i]["text_label"]) );
    
    def table_maps_double(self):
        self.form.entity_selected(self.entitys[ self.table_maps.index() ]);
        self.close();


