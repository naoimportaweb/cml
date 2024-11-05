import os, sys,  uuid, inspect;

from PySide6.QtCore import (QObject,  Signal, QByteArray, QFile, QFileInfo, QSettings, QDate,  
                            QSaveFile, QTextStream, Qt, Slot, QRegularExpression)
from PySide6.QtGui import QAction, QIcon, QKeySequence, QTextCharFormat, QSyntaxHighlighter, QFont
from PySide6.QtWidgets import (QWidget, QApplication, QFileDialog, QMainWindow, QTabWidget, QComboBox, QTableWidgetItem, QHeaderView,
                               QMdiArea, QMessageBox, QTextEdit, QDialog, QHBoxLayout, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(os.path.dirname( CURRENTDIR ));
sys.path.append( ROOT );

from classlib.configuration import Configuration;
from classlib.culture import Culture;

class QEditorPlus(QWidget):
    textChanged = Signal()
    editingFinished = Signal();
    def __init__(self, parent=None, type="editor"):
        super().__init__(parent);
        self.type = type;
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        self.highlighter = None; #MyHighlighter(self.txt.document(), self.txt );
        if self.type == "editor":
            self.txt1 = QTextEdit();
            self.txt1.setFont( Configuration.instancia().getFont() );
            self.txt1.setLineWrapMode(QTextEdit.NoWrap);
            self.txt1.setLineWrapMode(QTextEdit.WidgetWidth);  
            self.txt1.textChanged.connect(self.__txt1_changed__);
            self.btn_spell_check = QPushButton("Spell Check");
            self.btn_spell_check.setFont( Configuration.instancia().getFont() );
            self.btn_spell_check.clicked.connect(self.btn_spell_check_click);
            self.layout = QVBoxLayout();
            self.layout.addWidget( self.txt1 );
            self.layout.addWidget( self.btn_spell_check );
            self.setLayout( self.layout );
        else:
            self.txt1 = QLineEdit();
            self.txt1.editingFinished.connect(self.__editingFinished__)
            self.btn_spell_check = QPushButton("Spell Check");
            self.btn_spell_check.setFont( Configuration.instancia().getFont() );
            self.btn_spell_check.clicked.connect(self.btn_spell_check_click);
            self.layout = QHBoxLayout();
            self.layout.addWidget( self.txt1 );
            self.layout.addWidget( self.btn_spell_check );
            self.setLayout( self.layout );
    
    def setVisible(self, val):
        return;
        #if val == True:
        #    print("adicionando");
        #    self.layout.addWidget( self.txt );
        #    self.layout.addWidget( self.btn_spell_check );
        #else:
        #    print("removendo");
        #    self.layout.setParent(None)
        #    self.layout.setParent(None)
    
    def btn_spell_check_click(self):
        highlighter = None;
        highlighter = MyHighlighter(self.txt1.document(), self );
        highlighter.finished.connect(self.spell_check_finish)
        return;
    
    def spell_check_finish(self):
        print("Finsh spellcheck");

    def setText(self, text):
        if self.type == "editor":
            self.txt1.setPlainText( text );
        else:
            self.txt1.setText(text);

    def setPlainText(self, text):
        self.txt1.setPlainText( text );

    def toPlainText(self):
        if self.type == "editor":
            return self.txt1.toPlainText(); 
        else:
            return self.txt1.getText();
    
    def getText(self):
        if self.type == "editor":
            return self.txt1.toPlainText(); 
        else:
            return self.txt1.getText();

    def __txt1_changed__(self):
        self.textChanged.emit()
    def __editingFinished__(self):
        self.editingFinished.emit();

class MyHighlighter(QSyntaxHighlighter):
    finished = Signal()
    def __init__(self, document, control):
        super().__init__(document);
        self.culture = Culture("pt");
        self.control = control;
        self.patterns = [];
        self.__run__ = True;
    
    def highlightBlock(self, text):
        if not self.__run__:
            return;
        self.__run__ = False;
        self.patterns = self.culture.errors( self.control.getText() );
        myClassFormat = QTextCharFormat()
        myClassFormat.setFontWeight(QFont.Bold)
        myClassFormat.setBackground(Qt.yellow)
        for pattern in self.patterns:
            index = text.find(pattern);
            while index >= 0:
                length = len(pattern)
                self.setFormat(index, length, myClassFormat)
                index = text.find(pattern, index + length)
        self.finished.emit()
        
