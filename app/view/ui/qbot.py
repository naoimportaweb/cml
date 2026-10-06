import os, sys,  uuid, inspect, json, importlib;

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

class QBot(QWidget):
    def __init__(self, parent, obj, bot_json):
        super().__init__(parent);
        self.obj = obj;
        self.js = json.loads( open( ROOT + "/" + bot_json ).read() );
        self.btn = QPushButton( self.js["button"] );
        self.btn.setFont( Configuration.instancia().getFont() );
        self.btn.clicked.connect(self.btn_check);
        # Bot que depende de LLM (hoje o 'entidades') fica desligado com o motivo no lugar de
        # aceitar o clique e estourar excecao. O config.json do bot declara isso com "llm".
        if self.js.get("llm"):
            from transform.nucleo import motivo_llm;
            motivo = motivo_llm();
            if motivo != None:
                self.btn.setEnabled(False);
                self.btn.setText( self.js["button"] + " (indisponível)" );
                self.btn.setToolTip( motivo[0].upper() + motivo[1:] + "." );
        self.layout = QVBoxLayout();
        self.layout.addWidget( self.btn );
        self.setLayout( self.layout );
    
    def btn_check(self):
        f = self.instance( self.js["module"] , ROOT + "/" + self.js["path"] , self.js["class"], self.obj );
        f.show();

    def instance(self, module_name, path_module, class_name, obj_parameter):
        spec = importlib.util.spec_from_file_location(module_name, path_module);
        module = importlib.util.module_from_spec(spec);
        sys.modules[module_name] = module;
        spec.loader.exec_module(module);
        cls = getattr(module, class_name);
        inst = cls(self, obj_parameter);
        return inst;