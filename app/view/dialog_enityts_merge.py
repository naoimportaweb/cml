#dialog_entity_find.p
import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QHeaderView, QTableWidgetItem, QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from classlib.entity import Entity;
from view.ui.customvlayout import CustomVLayout;

class DialogEntitysMerge(QDialog):
    def __init__(self, form, entity):
        super().__init__(form)
        self.entitys = None;
        self.entity = entity;
        self.setWindowTitle("Merge entity")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.painel_entitys();
        self.entitys = entity.duplicate();
        self.list();

    #--------------------------------------------------------------
    def painel_entitys(self):
        layout = QVBoxLayout();
        self.table_search = CustomVLayout.widget_tabela(self, ["Name", "Small", "Type"], tamanhos=[QHeaderView.Stretch, QHeaderView.Stretch, QHeaderView.Stretch], double_click=self.table_double);
        layout.addWidget( self.table_search );
        self.layout_principal.addLayout( "entity", layout );
    
    def list(self):
        self.table_search.setRowCount( len( self.entitys ) );
        for i in range(len( self.entitys )):
            self.table_search.setItem( i, 0, QTableWidgetItem( self.entitys[i]["text_label"] ) );
            self.table_search.setItem( i, 1, QTableWidgetItem( self.entitys[i]["small_label"] ) );
            self.table_search.setItem( i, 1, QTableWidgetItem( self.entitys[i]["etype"] ) );
        return;

    def table_double(self):
        buffer = Entity.fromJson(self.entitys[ self.table_search.index() ]);
        self.entity.merge_to(buffer.id);
        self.entitys = self.entity.duplicate();
        self.list();

    #---------------------------------------------
    #def painel_show(self):
    #    layout = QVBoxLayout();
    #    lbl_name = QLabel("Entit:")
    #    lbl_name.setProperty("class", "normal")
    #    CustomVLayout.widget_linha(self, layout, [lbl_name, self.txt_name] );
    #    self.layout_principal.addLayout( "show", layout );