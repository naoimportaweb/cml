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
from classlib.maprelationship import MapRelationship;

class DialogRelationship(QDialog):
    def __init__(self):
        super().__init__();
        self.map = None;
        self.setWindowTitle("Connect")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.ui_search_relationship();
        self.ui_buttons();
        self.layout_principal.disable("buttons");
        
    def ui_search_relationship(self):
        layout_server = QGridLayout()
        layout_server.setContentsMargins(20, 20, 20, 20)
        layout_server.setSpacing(10)
        self.setWindowTitle("Relationship Map")
        lbl_name = QLabel("Map name:")
        lbl_name.setProperty("class", "normal")
        layout_server.addWidget(lbl_name, 1, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setMinimumWidth(500);
        self.txt_name.editingFinished.connect(self.txt_name_finish);
        layout_server.addWidget(self.txt_name, 1, 1);
        lbl_key = QLabel("Map name:")
        lbl_key.setProperty("class", "normal");
        layout_server.addWidget(lbl_key, 2, 0)
        self.txt_key = QLineEdit()
        self.txt_key.setMinimumWidth(500);
        self.txt_key.textEdited.connect(      self.txt_key_press );
        #self.txt_key.editingFinished.connect( self.txt_key_finish);
        layout_server.addWidget(self.txt_key, 2, 1);

        self.lbl_message = QLabel();
        
        layout_server.addWidget( self.lbl_message , 3, 1);
        self.layout_principal.addLayout( "search", layout_server );

    def ui_buttons(self):
        layout = QGridLayout()
        btn_entrar = QPushButton("Create new Diagram")
        btn_entrar.clicked.connect(self.btn_entrar_click)
        layout.addWidget(btn_entrar, 4, 2)
        self.layout_principal.addLayout( "buttons", layout );

    def btn_entrar_click(self):
        r = MapRelationship();
        r.name = self.txt_name.text();
        r.keyword = self.txt_key.text();
        if r.create():
            self.map = r;
            self.close();
    def txt_name_finish(self):
        print("procurar por....", self.txt_name.text());
        self.validar();
    def txt_key_finish(self):
        print("procurar por....", self.txt_key.text());
        self.validar();
    
    def validar(self):
        if self.__validar__():
            self.layout_principal.enable("buttons");
            self.lbl_message.setStyleSheet("QLabel { color : green; }");
            self.lbl_message.setText("");
            return True;
        else:
            self.layout_principal.disable("buttons");
            self.lbl_message.setStyleSheet("QLabel { color : red; }");
            return False;
    
    def txt_key_press(self):
        if len(self.txt_name.text()) > 0 and len(self.txt_key.text()) > 0:
            self.lbl_message.setText("");
            self.layout_principal.enable("buttons");
        else:
            self.layout_principal.disable("buttons");
    
    def __validar__(self):
        if len(self.txt_name.text()) == 0 or len(self.txt_key.text()) == 0:
            self.lbl_message.setText("Enter a name and keywords.");
            return False;
        r = MapRelationship();
        if r.exists(self.txt_name.text()):
            self.lbl_message.setText( "This diraggram already exists.." );
            return False;
        return True;
