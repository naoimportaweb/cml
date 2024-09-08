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
from view.dialogchoice import DialogChoiceEntity;

class MdiMap(QWidget):
    def __init__(self):
        super().__init__();
        self.painter_widget = MapAreaWidget(parent=None, form=self);
        layout = QHBoxLayout()
        layout.addWidget( self.painter_widget );
        self.setLayout(layout)

    def entity_double_click(self, entity):
        if entity.etype == "person":
            form = DialogEntityPerson(entity);
        elif entity.etype == "organization":
            form = DialogEntityOrganization(entity);
        elif entity.etype == "link":
            form = DialogEntityLink(entity);
        form.exec();
    
    def map_double_click(self, map, x, y):
        form = DialogChoiceEntity();
        form.exec();
        if form.ptype != None:
            map.addEntity( form.ptype, x, y );

    def new_map(self):
        return;

    def load_file(self, fileName):
        return;

    def save(self):
        return;

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
