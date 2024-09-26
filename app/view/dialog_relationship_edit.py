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
from classlib.relationship.maprelationship import MapRelationship;

class DialogRelationshipEdit(QDialog):
    def __init__(self, form, mapa):
        super().__init__();
        nWidth = int(form.width() * 0.8); nHeight = int(form.height() * 0.6);
        if nWidth > 800:
            nWidth = 800;
        self.setGeometry(form.x() + form.width()/2 - nWidth/2,
            form.y() + form.height()/2 - nHeight/2,
            nWidth, nHeight);

        self.map = mapa;
        self.setWindowTitle("Edit")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.ui_relationship();
        self.ui_lock();
        self.ui_buttons();
        
    def ui_relationship(self):
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
        self.txt_name.setText( self.map.name );
        layout_server.addWidget(self.txt_name, 1, 1);
        lbl_key = QLabel("Map name:")
        lbl_key.setProperty("class", "normal");
        layout_server.addWidget(lbl_key, 2, 0)
        self.txt_key = QLineEdit()
        self.txt_key.setMinimumWidth(500);
        self.txt_key.setText( self.map.keyword );
        self.txt_key.textEdited.connect(      self.txt_key_press );
        #self.txt_key.editingFinished.connect( self.txt_key_finish);
        layout_server.addWidget(self.txt_key, 2, 1);
        self.lbl_message = QLabel();
        layout_server.addWidget( self.lbl_message , 3, 1);
        self.layout_principal.addLayout( "relationship", layout_server );

    def ui_lock(self):
        layout = QGridLayout()
        btn_lock = QPushButton("Lock map")
        btn_lock.clicked.connect(self.btn_lock_click)
        layout.addWidget(btn_lock, 4, 2)

        btn_unlock = QPushButton("UnLock map")
        btn_unlock.clicked.connect(self.btn_unlock_click)
        layout.addWidget(btn_unlock, 4, 1)

        self.layout_principal.addLayout( "lock", layout );

    def ui_buttons(self):
        layout = QGridLayout()
        btn_entrar = QPushButton("Save Diagram")
        btn_entrar.clicked.connect(self.btn_save_click)
        layout.addWidget(btn_entrar, 4, 2)
        self.layout_principal.addLayout( "buttons", layout );

    def btn_unlock_click(self):
        self.map.locked_map();
        self.map.unlock_map();

    def btn_lock_click(self):
        self.map.locked_map();
        self.map.lock_map();

    def btn_save_click(self):
        self.map.name = self.txt_name.text();
        self.map.keyword = self.txt_key.text();
        if self.validar():
            if self.map.save():
                self.close();
    
    def txt_name_finish(self):
        self.validar();
    def txt_key_finish(self):
        self.validar();
    
    def validar(self):
        if len(self.txt_name.text()) == 0 or len(self.txt_key.text()) == 0:
            self.lbl_message.setText("Enter a name and keyword.");
            return False;
        if self.map.exists(self.txt_name.text()):
            self.lbl_message.setText( "This diraggram already exists.." );
            return False;
        return True;
    
    def txt_key_press(self):
        return False;
    
    def __validar__(self):
        return False;
