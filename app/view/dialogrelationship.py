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

class DialogRelationship(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Connect")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.ui_search_relationship();
        
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
        layout_server.addWidget(self.txt_name, 1, 1, 1, 2)
        self.layout_principal.addLayout( "search", layout_server );

#    def btn_click_register_navegar(self):
#        self.layout_principal.disable("login");
#        self.layout_principal.enable("register");
#    def btn_click_login_navegar(self):
#        self.layout_principal.enable("login");
#        self.layout_principal.disable("register");       
#    def btn_click_register_entrar(self):
#        server = Server();
#        envelop = {"username" : self.txt_register_username.text(),
#        "password" : self.txt_register_password.text(),
#        "mail" : self.txt_register_mail.text()};
#        server.status = True;
#        self.close();
#    def btn_click_login_entrar(self):
#        server = Server();
#        envelop = {"username" : self.txt_login_username.text(),
#        "password" : self.txt_login_password.text()};
#        server.status = True;
#        self.close();
