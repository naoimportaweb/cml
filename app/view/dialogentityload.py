import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QHeaderView, QTableWidgetItem, QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );

sys.path.append( ROOT );
sys.path.append("/opt/cml/app/");

from view.ui.customvlayout import CustomVLayout;
from classlib.server import Server;
from classlib.relationship.maprelationship import MapRelationship;
from classlib.relationship.person import Person
from classlib.relationship.organization import Organization
from classlib.relationship.other import Other
from classlib.relationship.link import Link
from classlib.entity import Entity;

class DialogEntityLoad(QDialog):
    def __init__(self, form):
        super().__init__(form);
        self.resize(600, 500);
        #nWidth = int(form.width() * 0.8); nHeight = int(form.height() * 0.6);
        #if nWidth > 800:
        #    nWidth = 800;
        #self.setGeometry(form.x() + form.width()/2 - nWidth/2,
        #    form.y() + form.height()/2 - nHeight/2,
        #    nWidth, nHeight);

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
        self.table_maps = CustomVLayout.widget_tabela(self, ["Entity", "Type", "Server"], tamanhos=[QHeaderView.Stretch, QHeaderView.Stretch, QHeaderView.Stretch], double_click=self.table_maps_double);
        layout.addWidget(self.table_maps);
        self.layout_principal.addLayout( "list", layout );

    def txt_name_finish(self):
        #r = MapRelationship();
        #self.entitys = r.search_entity( "%" + self.txt_name.text().strip() + "%");
        self.entitys = Entity.search("person,organization,other", "%" + self.txt_name.text().strip() + "%", proxy=True);
        self.entitys.sort(key=lambda x: x["text_label"])
        self.table_maps.setRowCount( len( self.entitys ) );
        for i in range(len( self.entitys )):
            self.table_maps.setItem( i, 0, QTableWidgetItem( self.entitys[i]["text_label"]) );
            self.table_maps.setItem( i, 1, QTableWidgetItem( self.entitys[i]["etype"]) );
            self.table_maps.setItem( i, 2, QTableWidgetItem( self.entitys[i]["server"]) );
    
    def table_maps_double(self):
        self.form.entity_selected(self.entitys[ self.table_maps.index() ]);
        self.close();


