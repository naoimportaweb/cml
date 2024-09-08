import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QTabWidget, QComboBox,
                               QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from view.ui.customvlayout import CustomVLayout;

class DialogEntityPerson(QDialog):
    def __init__(self, person):
        super().__init__()
        self.setWindowTitle("Person")
        self.person = person;
        self.tab = QTabWidget();  
        self.page_rel = CustomVLayout.widget_tab( self.tab, "Person");
        self.page_pho = CustomVLayout.widget_tab( self.tab, "Photo");
        self.page_dox = CustomVLayout.widget_tab( self.tab, "Doxxing");
        # ------------------------------------------
        self.lbl_text = QLabel("Text");
        self.txt_text = QLineEdit();
        self.txt_text.setText( self.person.text ) ;
        self.txt_text.textChanged.connect(self.txt_text_changed)
        CustomVLayout.widget_linha(self, self.page_rel, [self.lbl_text, self.txt_text] );
        
        self.txt_descricao = QTextEdit();
        self.txt_descricao.setPlainText( person.full_description );
        self.txt_descricao.setLineWrapMode(QTextEdit.NoWrap);
        self.txt_descricao.textChanged.connect(self.txt_descricao_changed)
        font = self.txt_descricao.font();
        font.setFamily("Courier");
        self.txt_descricao.setLineWrapMode(QTextEdit.WidgetWidth);  
        self.page_rel.addWidget( self.txt_descricao );
        # --------------------------------------------------
        self.txt_doxxing = QTextEdit();
        self.txt_doxxing.setPlainText( person.doxxing );
        self.txt_doxxing.setLineWrapMode(QTextEdit.NoWrap);
        self.txt_doxxing.textChanged.connect(self.txt_doxxing_changed)
        font = self.txt_doxxing.font();
        font.setFamily("Courier");
        self.txt_doxxing.setLineWrapMode(QTextEdit.WidgetWidth);  
        self.page_dox.addWidget( self.txt_doxxing );

        layout = QVBoxLayout();
        layout.addWidget( self.tab           );
        self.setLayout(   layout             );


    def txt_text_changed(self):
        self.person.text = self.txt_text.text();
    
    def txt_descricao_changed(self):
        self.person.full_description = self.txt_descricao.toPlainText();

    def txt_doxxing_changed(self):
        self.person.doxxing = self.txt_doxxing.toPlainText();