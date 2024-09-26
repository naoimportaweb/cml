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

from view.ui.customvlayout import CustomVLayout;
from view.dialogentityload import DialogEntityLoad;

class DialogChoiceEntity(QDialog):
    def __init__(self, form):
        super().__init__(form)
        self.option = 0;
        self.ptype = None;
        self.search_entity = None;
        self.setWindowTitle("Choice")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.painel_new();
        self.painel_search();
        self.layout_principal.pad();
        self.layout_principal.disable("search");

    def painel_new(self):
        layout = QGridLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        btn_search = QPushButton("Search existent")
        btn_person = QPushButton("New Person")
        btn_organization = QPushButton("New Organization")
        btn_relationship = QPushButton("New Relationship");
        btn_other = QPushButton("Other")
        btn_cancel = QPushButton("Cancel")
        layout.addWidget(btn_search, 1, 0)
        layout.addWidget(btn_person, 2, 0)
        layout.addWidget(btn_organization, 3, 0)
        layout.addWidget(btn_relationship, 4, 0)
        layout.addWidget(btn_other, 5, 0)
        layout.addWidget(btn_cancel, 6, 0)
        btn_search.clicked.connect(self.btn_search_click)
        btn_person.clicked.connect(self.btn_person_click)
        btn_other.clicked.connect(self.btn_other_click)
        btn_organization.clicked.connect(self.btn_organization_click)
        btn_relationship.clicked.connect(self.btn_relationship_click)
        btn_cancel.clicked.connect(self.btn_cancel_click)
        self.layout_principal.addLayout( "new", layout );

    def painel_search(self):
        layout = QGridLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        btn_new = QPushButton("New entity")
        btn_cancel = QPushButton("Cancel")
        layout.addWidget(btn_new, 1, 0)
        layout.addWidget(btn_cancel, 5, 0)
        btn_new.clicked.connect(self.btn_new_click)
        btn_cancel.clicked.connect(self.btn_cancel_click)
        self.layout_principal.addLayout( "search", layout );

    def btn_person_click(self):
        self.ptype = "person";
        self.close();
    def btn_other_click(self):
        self.ptype = "other";
        self.close();
    def btn_organization_click(self):
        self.ptype = "organization";
        self.close();
    def btn_relationship_click(self):
        self.ptype = "link";
        self.close();
    def btn_cancel_click(self):
        self.ptype = None;
        self.close();
    def btn_search_click(self):
        f = DialogEntityLoad( self );
        f.exec();

    def btn_new_click(self):
       self.layout_principal.enable("new");
       self.layout_principal.disable("search");

    def entity_selected(self, element):
        self.search_entity = element;
        self.close();