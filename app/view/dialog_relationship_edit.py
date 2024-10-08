import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QTabWidget,
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
        self.tab = QTabWidget();  
        self.page_info = CustomVLayout.widget_tab( self.tab, "Information");
        self.page_perm = CustomVLayout.widget_tab( self.tab, "Persmission");
        self.page_docs = CustomVLayout.widget_tab( self.tab, "Documents");
        layout = QVBoxLayout();
        layout.addWidget( self.tab );
        self.setLayout(   layout   );
        self.ui_relationship();
        self.ui_lock();
        self.ui_buttons();
        
    def ui_relationship(self):
        server = Server();
        
        lbl_name = QLabel("Map name:")
        lbl_name.setProperty("class", "normal")
        self.txt_name = QLineEdit()
        self.txt_name.setMinimumWidth(500);
        self.txt_name.editingFinished.connect(self.txt_name_finish);
        self.txt_name.setText( self.map.name );
        CustomVLayout.widget_linha(self, self.page_info, [lbl_name, self.txt_name] );
        
        lbl_key = QLabel("Map name:")
        lbl_key.setProperty("class", "normal");
        self.txt_key = QLineEdit()
        self.txt_key.setMinimumWidth(500);
        self.txt_key.setText( self.map.keyword );
        self.txt_key.textEdited.connect(      self.txt_key_press );
        CustomVLayout.widget_linha(self, self.page_info, [lbl_key, self.txt_key] );
        
        lbl_url = QLabel("URL:")
        lbl_url.setProperty("class", "normal");
        self.txt_url = QTextEdit()
        self.txt_url.setPlainText( server.ip + "/cml/webpage/view/relationship/relationship.php?id=" + self.map.id);
        CustomVLayout.widget_linha(self, self.page_info, [lbl_url] );
        CustomVLayout.widget_linha(self, self.page_info, [self.txt_url] );

        self.lbl_message = QLabel();
        CustomVLayout.widget_linha(self, self.page_info, [self.lbl_message] );

    def ui_lock(self):
        btn_lock = QPushButton("Lock map")
        btn_lock.clicked.connect(self.btn_lock_click)
        btn_unlock = QPushButton("UnLock map")
        btn_unlock.clicked.connect(self.btn_unlock_click)
        CustomVLayout.widget_linha(self, self.page_perm, [btn_unlock,btn_lock] );

    def ui_buttons(self):
        btn_entrar = QPushButton("Save Diagram")
        btn_entrar.clicked.connect(self.btn_save_click)
        CustomVLayout.widget_linha(self, self.page_info, [btn_entrar] );

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
