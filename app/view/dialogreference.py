import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow,
                               QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );

sys.path.append( ROOT );
sys.path.append("/opt/cml/app/");

from view.ui.customvlayout import CustomVLayout;
from classlib.server import Server;

class DialogReference(QDialog):
    def __init__(self, form, element, reference):
        super().__init__()
        self.element = element;
        self.reference = reference;
        self.form = form;
        self.setWindowTitle("Reference")
        layout = QGridLayout()
        lbl_title = QLabel("Title")
        lbl_title.setProperty("class", "normal")
        layout.addWidget(lbl_title, 1, 0)
        self.txt_title = QLineEdit()
        layout.addWidget(self.txt_title, 1, 1)

        lbl_link1 = QLabel("Link:")
        lbl_link1.setProperty("class", "normal")
        layout.addWidget(lbl_link1, 2, 0)
        self.txt_link1 = QLineEdit()
        layout.addWidget(self.txt_link1, 2, 1)

        lbl_link2 = QLabel("Link:")
        lbl_link2.setProperty("class", "normal")
        layout.addWidget(lbl_link2, 3, 0)
        self.txt_link2 = QLineEdit()
        layout.addWidget(self.txt_link2, 3, 1)

        lbl_link3 = QLabel("Link:")
        lbl_link3.setProperty("class", "normal")
        layout.addWidget(lbl_link3, 4, 0)
        self.txt_link3 = QLineEdit()
        layout.addWidget(self.txt_link3, 4, 1)

        btn_salvar = QPushButton("Save")
        btn_salvar.clicked.connect(self.btn_salvar_click)
        layout.addWidget(btn_salvar, 5, 2)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.btn_close_click)
        layout.addWidget(btn_close, 5, 1)

        if reference != None:
            self.txt_title.setText( self.reference.title);
            self.txt_link1.setText( self.reference.link1 );
            self.txt_link2.setText( self.reference.link2 );
            self.txt_link3.setText( self.reference.link3 );

        self.setLayout(   layout             );


    def btn_salvar_click(self):
        if self.reference == None:
            self.reference = self.element.addReference(self.txt_title.text(), self.txt_link1.text(), self.txt_link2.text(),  self.txt_link3.text());
        else:
            self.reference.title = self.txt_title.text();
            self.reference.link1 = self.txt_link1.text();
            self.reference.link2 = self.txt_link2.text();
            self.reference.link3 = self.txt_link3.text();

    def btn_close_click(self):
        self.close();

