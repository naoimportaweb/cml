#dialog_entity_find.p
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

from classlib.entity import Entity;
from view.ui.customvlayout import CustomVLayout;

class DialogEntityFind(QDialog):
    def __init__(self, form):
        super().__init__(form)
        self.entitys = None;
        self.entity = None;
        self.setWindowTitle("Find entity")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.painel_entitys();

    #--------------------------------------------------------------
    def painel_entitys(self):
        layout = QVBoxLayout();
        lbl_name = QLabel("Entity name:")
        lbl_name.setProperty("class", "normal")
        self.txt_name = QLineEdit()
        self.txt_name.setMinimumWidth(500);
        self.txt_name.editingFinished.connect(self.txt_name_finish);
        CustomVLayout.widget_linha(self, layout, [lbl_name, self.txt_name] );
        self.table_search = CustomVLayout.widget_tabela(self, ["Name", "Type"], tamanhos=[QHeaderView.Stretch, QHeaderView.Stretch], double_click=self.table_double);
        layout.addWidget( self.table_search );
        self.layout_principal.addLayout( "entity", layout );
    
    def txt_name_finish(self):
        self.entitys = Entity.search("", "%" + self.txt_name.text() + "%");
        self.table_search.setRowCount( len( self.entitys ) );
        self.entity = None;
        for i in range(len( self.entitys )):
            self.table_search.setItem( i, 0, QTableWidgetItem( self.entitys[i]["text_label"] ) );
            self.table_search.setItem( i, 1, QTableWidgetItem( self.entitys[i]["etype"] ) );
        return;

    def table_double(self):
        self.entity = self.entitys[ self.table_search.index ];
        self.close();
        return;

    #---------------------------------------------
    def painel_show(self):
        layout = QVBoxLayout();
        lbl_name = QLabel("Entit:")
        lbl_name.setProperty("class", "normal")
        CustomVLayout.widget_linha(self, layout, [lbl_name, self.txt_name] );
        self.layout_principal.addLayout( "show", layout );