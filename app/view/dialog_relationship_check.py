import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QHBoxLayout, QHeaderView, QTableWidgetItem, QMdiArea, QMessageBox, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );

sys.path.append( ROOT );

from view.dialogentitylink import DialogEntityLink;
from view.dialog_entity_other import DialogEntityOther;
from view.dialog_entity_person import DialogEntityPerson;
from view.dialog_entity_organization import DialogEntityOrganization;
from view.ui.customvlayout import CustomVLayout;
from classlib.relationship.maprelationship import MapRelationship;
from classlib.relationship.relationship_info import RelatinshipInfo;
from classlib.relationship.maprelationship_box import MapRelationshipBox;


class DialogRelationshipCheck(QDialog):
    def __init__(self, form, mapa):
        super().__init__();
        nWidth = int(form.width() * 0.8); nHeight = int(form.height() * 0.6);
        if nWidth > 800:
            nWidth = 800;
        self.parent = form;
        self.mapa = mapa;
        self.setGeometry(form.x() + form.width()/2 - nWidth/2,
            form.y() + form.height()/2 - nHeight/2,
            nWidth, nHeight);

        self.map = None;
        self.setWindowTitle("Relationship Check")
        self.layout = QVBoxLayout();
        self.setLayout( self.layout );
        #----- errors -----
        self.layout.addWidget( QLabel("<h2>Errors:</h2>") );
        self.layout.addWidget( QLabel("What should be fixed") );
        self.table_error = CustomVLayout.widget_tabela(self, ["Type","Description", "Object"], tamanhos=[QHeaderView.ResizeToContents, QHeaderView.Stretch,  QHeaderView.ResizeToContents], double_click=self.table_error_double_click);
        self.layout.addWidget(self.table_error);
        #----- warning -----
        self.layout.addWidget( QLabel("<h2>Warnings:</h2>") );
        self.layout.addWidget( QLabel("We recommend improvement") );
        self.table_warning = CustomVLayout.widget_tabela(self, ["Type", "Description", "Object"], tamanhos=[QHeaderView.ResizeToContents, QHeaderView.Stretch,  QHeaderView.ResizeToContents], double_click=self.table_warning_double_click);
        self.layout.addWidget(self.table_warning);
        self.load_tables();
    def load_tables(self):
        erros = self.mapa.getErros();
        warnings = self.mapa.getWarnings();
        self.__load_table__( self.table_error   , erros);
        self.__load_table__( self.table_warning , warnings);
    
    def __load_table__(self, table, arr):
        table.setRowCount( len( arr ) );
        table.lista = arr;
        for i in range(len( arr )):
            table.setItem( i, 0, QTableWidgetItem( arr[i].entityType() ) );
            table.setItem( i, 2, QTableWidgetItem( arr[i].getText() ) );
            table.setItem( i, 1, QTableWidgetItem( str(arr[i].getObject()) ) );

    def table_error_double_click(self):
        obj = self.table_error.get();
        self.table_double_click(obj);

    def table_double_click(self, obj):
        if obj.entityType() == "Other" or obj.entityType() == "Person" or obj.entityType() == "Organization":
            if obj.entityType() == "Other":
                f = DialogEntityOther(self.parent, obj.obj );
            elif obj.entityType() == "Person":
                f = DialogEntityPerson(self.parent, obj.obj );
            elif obj.entityType() == "Organization":
                f = DialogEntityOrganization(self.parent, obj.obj );
            f.exec();
        if obj.entityType() == "Link":
            f = DialogEntityLink(   self.parent, obj.obj, self.mapa);
            f.exec();
        self.load_tables();
        return;
    
    def table_warning_double_click(self):
        obj = self.table_warning.get();
        self.table_double_click(obj);
        return;    