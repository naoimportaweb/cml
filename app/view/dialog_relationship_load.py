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
from classlib.relationship.maprelationship import MapRelationship;
from classlib.relationship.person import Person
from classlib.relationship.organization import Organization
from classlib.relationship.other import Other
from classlib.relationship.link import Link
from classlib.organization_chart.organization_chart import OrganizationChart

class DialogRelationshipLoad(QDialog):
    def __init__(self, form):
        super().__init__();
        #self.resize(800, 660);
        nWidth = int(form.width() * 0.8); nHeight = int(form.height() * 0.6);
        if nWidth > 800:
            nWidth = 800;
        self.setGeometry(form.x() + form.width()/2 - nWidth/2,
            form.y() + form.height()/2 - nHeight/2,
            nWidth, nHeight);

        self.map = None;
        self.setWindowTitle("Connect")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.ui_search_relationship();
        self.ui_tabela();
        
    def ui_search_relationship(self):
        layout_server = QGridLayout()
        layout_server.setContentsMargins(20, 20, 20, 20)
        layout_server.setSpacing(10)
        self.setWindowTitle("Map Search")
        lbl_name = QLabel("Map name:")
        lbl_name.setProperty("class", "normal")
        layout_server.addWidget(lbl_name, 1, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setMinimumWidth(500);
        layout_server.addWidget(self.txt_name, 1, 1);
        self.txt_name.editingFinished.connect(self.txt_name_finish);   
        self.layout_principal.addLayout( "search", layout_server );

    def ui_tabela(self):
        layout = QVBoxLayout();
        self.table_maps = CustomVLayout.widget_tabela(self, ["User", "Name", "Map Type"], tamanhos=[QHeaderView.Stretch, QHeaderView.Stretch, QHeaderView.Stretch], double_click=self.table_maps_double);
        layout.addWidget(self.table_maps);
        self.layout_principal.addLayout( "list", layout );

    def txt_name_finish(self):
        r = MapRelationship();
        self.mapas = r.search( "%" + self.txt_name.text().strip() + "%");
        #self.mapas.sort(key=lambda x: x["name"]);
        self.table_maps.setRowCount( len( self.mapas["organization"] ) + len( self.mapas["relationship"] ) );
        linhas = 0;
        for i in range(len( self.mapas["relationship"] )):
            self.table_maps.setItem( linhas, 0, QTableWidgetItem( self.mapas["relationship"][i]["username"] ) );
            self.table_maps.setItem( linhas, 1, QTableWidgetItem( self.mapas["relationship"][i]["name"]) );
            self.table_maps.setItem( linhas, 2, QTableWidgetItem( "Relationship Map" ));
            linhas += 1;
        for i in range(len( self.mapas["organization"] )):
            self.table_maps.setItem( linhas, 0, QTableWidgetItem( self.mapas["organization"][i]["username"] ) );
            self.table_maps.setItem( linhas, 1, QTableWidgetItem( self.mapas["organization"][i]["organization_text_label"] + " - " + self.mapas["organization"][i]["name"]) );
            self.table_maps.setItem( linhas, 2, QTableWidgetItem( "Organization Chart") );
            linhas += 1;

    
    def table_maps_double(self):
        index = self.table_maps.index() ;
        if index < len( self.mapas["relationship"] ):
            r = MapRelationship();
            if r.load( self.mapas["relationship"][index]["id"] ):
                self.map = r;
                self.close();
        else:
            buffer = self.mapas["organization"][index - len( self.mapas["relationship"] ) ];
            o = OrganizationChart( buffer["organization_id"] );
            if o.load( buffer["id"]  ):
                self.map = o;
                self.close();
            return;


