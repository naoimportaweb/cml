import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append(ROOT);

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QMdiArea, QMessageBox, QTextEdit, QWidget, QHBoxLayout)

from view.ui.mapareawidget import MapAreaWidget;
from view.dialogentitylink import DialogEntityLink;
from view.dialogentityorganization import DialogEntityOrganization;
from view.dialogentityperson import DialogEntityPerson;
from view.dialogentityother import DialogEntityOther;
from view.dialogchoice import DialogChoiceEntity;

class MdiMap(QWidget):
    def __init__(self, form, mapa):
        super().__init__();
        self.form_principal = form;
        self.painter_widget = MapAreaWidget(parent=None, mapa=mapa, form=self);
        self.mapa = mapa;
        layout = QHBoxLayout()
        layout.addWidget( self.painter_widget );
        self.setLayout(layout)
        self.painter_widget.redraw();
        

    def entity_double_click(self, entity):
        if entity.entity.etype == "person":
            form = DialogEntityPerson( self.form_principal,entity);
        elif entity.entity.etype == "other":
            form = DialogEntityOther(  self.form_principal,entity);
        elif entity.entity.etype == "organization":
            form = DialogEntityOrganization(self.form_principal,entity);
        elif entity.entity.etype == "link":
            form = DialogEntityLink(   self.form_principal, entity, self.mapa);
        form.exec();
    
    def map_double_click(self, map, x, y):
        form = DialogChoiceEntity(self.form_principal);
        form.exec();
        if form.ptype != None:  # NOVO ITEM É AQUI
            map.addEntity( form.ptype, x, y );
        else:                   # ITEM EXISTENTE É AQUI
            if form.search_entity != None:
                map.addExistEntity(form.search_entity, x, y);


    def new_map(self):
        return;

    def load_file(self, fileName):
        return;

    def save(self):
        self.mapa.save();

    def save_as(self):
        return;

    def save_file(self, fileName):
        return;

    def user_friendly_current_file(self):
        return;

    def current_file(self):
        return;

    def closeEvent(self, event):
        return;

    def document_was_modified(self):
        return;

    def maybe_save(self):
        return;

    def set_current_file(self, fileName):
        return;

    def stripped_name(self, fullFileName):
        return;
