import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QDate, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QTabWidget, QComboBox, QTableWidgetItem, QHeaderView, QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from view.ui.customvlayout import CustomVLayout;
from view.dialogreference import DialogReference;
from classlib.configuration import Configuration;
from view.dialog_classification import DialogClassification;
from view.dialog_entity_generic import DialogEntityGeneric;

class DialogEntityOrganization(DialogEntityGeneric):
    def __init__(self, form, organization):
        super().__init__(form, organization)
        nWidth = int(form.width() * 0.8); nHeight = int(form.height() * 0.6);
        if nWidth > 800:
            nWidth = 800;
        self.setGeometry(form.x() + form.width()/2 - nWidth/2, form.y() + form.height()/2 - nHeight/2, nWidth, nHeight);
        self.setWindowTitle("Organization")
        self.panelDescricao();
        self.panelUrls();
        self.panelReferences();
        self.panelClassification();
        self.panelActioins();
        
        layout = QVBoxLayout();
        layout.addWidget( self.tab           );
        self.setLayout(   layout             );









