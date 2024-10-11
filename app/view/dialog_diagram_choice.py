import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QHeaderView, 
                               QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );

sys.path.append( ROOT );

from view.ui.customvlayout import CustomVLayout;
from view.dialogentityload import DialogEntityLoad;

class DialogDiagramChoice(QDialog):
    def __init__(self, form):
        super().__init__(form)
        self.option = 0;
        self.ptype = None;
        self.search_entity = None;
        self.setWindowTitle("Digram type")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.painel_new();
        self.painel_organization_chart();
        self.layout_principal.pad();
        self.layout_principal.disable("organization");

    def painel_new(self):
        layout = QGridLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        btn_relationship = QPushButton("Relationship Diagram")
        btn_organzation_chart = QPushButton("Organization Chart Diagram")
        btn_cancel = QPushButton("Cancel")
        layout.addWidget(btn_relationship, 1, 0)
        layout.addWidget(btn_organzation_chart, 2, 0)
        layout.addWidget(btn_cancel, 6, 0)
        btn_relationship.clicked.connect(self.btn_relationship_click)
        btn_organzation_chart.clicked.connect(self.btn_organization_chart_click)
        btn_cancel.clicked.connect(self.btn_cancel_click)
        self.layout_principal.addLayout( "new", layout );

    def btn_cancel_click(self):
        self.ptype = None;
        self.close();
    
    def btn_relationship_click(self):
        return;

    def btn_organization_chart_click(self):
        self.layout_principal.enable("organization");
        self.layout_principal.disable("new");
        return;
    #--------------------------------------------------------------
    def painel_organization_chart(self):
        layout = QVBoxLayout();
        lbl_name = QLabel("Organization Name:")
        lbl_name.setProperty("class", "normal")
        self.txt_organization_name = QLineEdit()
        self.txt_organization_name.setMinimumWidth(500);
        self.txt_organization_name.editingFinished.connect(self.txt_organization_name_finish);
        CustomVLayout.widget_linha(self, layout, [lbl_name, self.txt_organization_name] );
        self.table_organization_search = CustomVLayout.widget_tabela(self, ["Name"], tamanhos=[QHeaderView.Stretch], double_click=self.table_organization_double);
        layout.addWidget( self.table_organization_search );
        self.layout_principal.addLayout( "organization", layout );
    
    def txt_organization_name_finish(self):
        return;

    def table_organization_double(self):
        return;


