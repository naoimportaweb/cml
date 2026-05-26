import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from view.ui.customvlayout import CustomVLayout;
from classlib.importlib import ImportLib;

class DialogImport(QDialog):
    def __init__(self, form):
        super().__init__(form)
        self.resize(600, 320);
        self.option = 0;
        self.ptype = None;
        self.search_entity = None;
        self.setWindowTitle("Import data")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.painel_search();
        self.layout_principal.pad();

    def painel_search(self):
        layout = QGridLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        lbl_name = QLabel("Json file:")
        self.txt_file = QLineEdit()
        btn_search_file = QPushButton("Search")
        btn_search_file.clicked.connect(self.btn_search_file_click)
        CustomVLayout.widget_linha(self, layout, [lbl_name, self.txt_file, btn_search_file] );

        btn_import = QPushButton("Import")
        layout.addWidget(btn_import, 1, 0)
        btn_import.clicked.connect(self.btn_import_click)
        self.layout_principal.addLayout( "import", layout );

    def btn_import_click(self):
        i = ImportLib();
        paths = self.txt_file.text().split(",");
        #total = 0;
        #for path in paths:
        #    total = total + i.import_entitys(path);
        total = i.import_entitys(paths)
        msgBox = QMessageBox()
        msgBox.setText("Foi adicionado: " + str(total) + " elementos.")
        msgBox.exec()
    def btn_search_file_click(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile);
        dialog.setNameFilter("JSON (*.json)");
        if dialog.exec_():
            self.txt_file.setText( ",".join(dialog.selectedFiles()) );
            return self.txt_file.text();
        return None;
#[
#    {"text_label" : "0Trusted", "small_label": "", "description" : "Hacker", "etype" : "person", "sub_etype" : "hacker", "wikipedia" : "",
#          "default_url" : "", "icon" : "", "aka" : "a, b, c, d",
#          "references" : [
#                               {"description" : "", "entity_id" : "", "link1" : "", "link2" : "", "link3" : "", "title" : ""}
#                         ]
#     }
#]

#creation_time, , , id, , , , modification_time, 