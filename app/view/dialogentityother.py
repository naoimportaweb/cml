import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QTabWidget, QComboBox, QTableWidgetItem, QHeaderView,
                               QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from view.ui.customvlayout import CustomVLayout;
from view.dialogreference import DialogReference;

class DialogEntityOther(QDialog):
    def __init__(self, other):
        super().__init__()
        self.setWindowTitle("Other")
        self.other = other;
        self.tab = QTabWidget();  
        self.page_rel = CustomVLayout.widget_tab( self.tab, "other");
        self.page_pho = CustomVLayout.widget_tab( self.tab, "Photo");
        self.page_ref = CustomVLayout.widget_tab( self.tab, "References");
        # ------------------------------------------
        self.lbl_text = QLabel("Text");
        self.txt_text = QLineEdit();
        self.txt_text.setText( self.other.entity.text ) ;
        self.txt_text.textChanged.connect(self.txt_text_changed)
        CustomVLayout.widget_linha(self, self.page_rel, [self.lbl_text, self.txt_text] );
        
        self.txt_descricao = QTextEdit();
        self.txt_descricao.setPlainText( other.entity.full_description );
        self.txt_descricao.setLineWrapMode(QTextEdit.NoWrap);
        self.txt_descricao.textChanged.connect(self.txt_descricao_changed)
        font = self.txt_descricao.font();
        font.setFamily("Courier");
        self.txt_descricao.setLineWrapMode(QTextEdit.WidgetWidth);  
        self.page_rel.addWidget( self.txt_descricao );
        # --------------------------------------------------
        #-------------------------------------------
        btn_reference_add = QPushButton("Add");
        btn_reference_del = QPushButton("Remove");
        btn_reference_add.clicked.connect(self.btn_reference_add_click);
        btn_reference_del.clicked.connect(self.btn_reference_del_click);
        CustomVLayout.widget_linha(self, self.page_ref, [btn_reference_add, btn_reference_del] );
        self.table_reference = CustomVLayout.widget_tabela(self, ["Title"], tamanhos=[QHeaderView.Stretch], double_click=self.table_reference_click);
        self.page_ref.addWidget(self.table_reference);
        self.table_reference_load();
        layout = QVBoxLayout();
        layout.addWidget( self.tab           );
        self.setLayout(   layout             );

    def table_reference_load(self):
        self.table_reference.setRowCount( len( self.other.entity.references ) );
        for i in range(len( self.other.entity.references )):
            self.table_reference.setItem( i, 0, QTableWidgetItem( self.other.entity.references[i].title ) );
    
    def table_reference_click(self):
        element = self.other.entity.references[ self.table_reference.index() ];
        form = DialogReference(self, self.other, reference=element);
        form.exec();
        self.table_reference_load();

    def btn_reference_del_click(self):
        index = self.table_reference.index();
        self.other.entity.references.pop( index );
        self.table_reference_load();
    
    def btn_reference_add_click(self):
        form = DialogReference(self, self.other, reference=None);
        form.exec();
        self.table_reference_load()

    def txt_text_changed(self):
        self.other.entity.text = self.txt_text.text();
    
    def txt_descricao_changed(self):
        self.other.entity.full_description = self.txt_descricao.toPlainText();