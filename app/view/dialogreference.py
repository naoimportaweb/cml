import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow,
                               QMdiArea, QMessageBox, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );

sys.path.append( ROOT );
sys.path.append("/opt/cml/app/");

from classlib.configuration import Configuration;
from view.ui.customvlayout import CustomVLayout;
from classlib.server import Server;
from view.ui.qeditorplus import QEditorPlus;
from view.ui.qbot import QBot;

class DialogReference(QDialog):
    def __init__(self, form, element, reference):
        super().__init__()
        nWidth = int(form.width() * 0.8); nHeight = int(form.height() * 0.6);
        if nWidth > 800:
            nWidth = 800;
        self.setGeometry(form.x() + form.width()/2 - nWidth/2,
            form.y() + form.height()/2 - nHeight/2,
            nWidth, nHeight);

        self.element = element;
        self.reference = reference;
        self.form = form;
        self.setWindowTitle("Reference")
        layout = QGridLayout()
        lbl_title = QLabel("Title")
        lbl_title.setFont( Configuration.instancia().getFont() );
        lbl_title.setProperty("class", "normal")
        layout.addWidget(lbl_title, 1, 0)
        self.txt_title = QLineEdit();
        self.txt_title.setFont( Configuration.instancia().getFont() );
        layout.addWidget(self.txt_title, 1, 1)

        self.txt_descricao = QEditorPlus();
        self.txt_descricao.textChanged.connect(self.txt_descricao_changed)
        layout.addWidget( self.txt_descricao, 2,1 );

        lbl_link1 = QLabel("Link:")
        lbl_link1.setFont( Configuration.instancia().getFont() );
        lbl_link1.setProperty("class", "normal")
        layout.addWidget(lbl_link1, 3, 0)
        self.txt_link1 = QLineEdit();
        self.txt_link1.setFont( Configuration.instancia().getFont() );
        layout.addWidget(self.txt_link1, 3, 1)

        lbl_link2 = QLabel("Link:")
        lbl_link2.setFont( Configuration.instancia().getFont() );
        lbl_link2.setProperty("class", "normal")
        layout.addWidget(lbl_link2, 4, 0)
        self.txt_link2 = QLineEdit()
        self.txt_link2.setFont( Configuration.instancia().getFont() );
        layout.addWidget(self.txt_link2, 4, 1)

        lbl_link3 = QLabel("Link:")
        lbl_link3.setFont( Configuration.instancia().getFont() );
        lbl_link3.setProperty("class", "normal")
        layout.addWidget(lbl_link3, 5, 0)
        self.txt_link3 = QLineEdit();
        self.txt_link3.setFont( Configuration.instancia().getFont() );
        layout.addWidget(self.txt_link3, 5, 1)

        if self.reference != None:
            qb = QBot(self, self.reference, "bot/brazil/wayback/config.json");
            layout.addWidget(qb, 6, 1)

        btn_salvar = QPushButton("Save")
        btn_salvar.clicked.connect(self.btn_salvar_click)
        layout.addWidget(btn_salvar, 7, 1)

        if reference != None:
            self.txt_descricao.setPlainText( self.reference.description );
            self.txt_title.setText( self.reference.title);
            self.txt_link1.setText( self.reference.link1 );
            self.txt_link2.setText( self.reference.link2 );
            self.txt_link3.setText( self.reference.link3 );
        self.setLayout(   layout             );

    def txt_descricao_changed(self):
        if self.reference != None:
            self.reference.description = self.txt_descricao.toPlainText();

    def btn_salvar_click(self):
        if self.reference == None:
            self.reference = self.element.addReference(self.txt_title.text(), self.txt_link1.text(), self.txt_link2.text(),  self.txt_link3.text(), descricao=self.txt_descricao.toPlainText() );
        else:
            self.reference.title = self.txt_title.text();
            self.reference.link1 = self.txt_link1.text();
            self.reference.link2 = self.txt_link2.text();
            self.reference.link3 = self.txt_link3.text();
            self.reference.description = self.txt_descricao.toPlainText();

    def btn_close_click(self):
        self.close();

