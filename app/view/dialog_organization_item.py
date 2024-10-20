import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QDate,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QTabWidget, QComboBox, QTableWidgetItem, QHeaderView,
                               QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from view.ui.customvlayout import CustomVLayout;
from classlib.configuration import Configuration;
from view.dialog_entity_find import DialogEntityFind;

class DialogOrganizationItem(QDialog):
    def __init__(self, form, element, graphic):
        super().__init__(form)
        nWidth = int(form.width() * 0.8); nHeight = int(form.height() * 0.6);
        if nWidth > 800:
            nWidth = 800;
        self.setGeometry(form.x() + form.width()/2 - nWidth/2,
            form.y() + form.height()/2 - nHeight/2, 600, 500);
        #if element == None:
        #    element = graphic.addEntityItem("New Item");
        self.element = element;
        self.graphic = graphic;
        self.setWindowTitle("Organization")
        self.tab = QTabWidget();  
        self.page_org = CustomVLayout.widget_tab( self.tab, "Organization");
        self.page_ele = CustomVLayout.widget_tab( self.tab, "Elements");
        self.page_act = CustomVLayout.widget_tab( self.tab, "Actions");
        # ------------------------------------------
        self.lbl_text = QLabel("Text");
        self.txt_text = QLineEdit();
        self.txt_text.setFont( Configuration.instancia().getFont() );
        self.txt_text.setText( self.element.text_label ) ;
        self.txt_text.textChanged.connect(self.txt_text_changed)
        CustomVLayout.widget_linha(self, self.page_org, [self.lbl_text, self.txt_text] );
        
        self.txt_descricao = QTextEdit();
        self.txt_descricao.setPlainText( "" );
        self.txt_descricao.setLineWrapMode(QTextEdit.NoWrap);
        self.txt_descricao.setFont( Configuration.instancia().getFont() );
        self.txt_descricao.textChanged.connect(self.txt_descricao_changed)
        self.txt_descricao.setLineWrapMode(QTextEdit.WidgetWidth);  
        self.page_org.addWidget( self.txt_descricao );
        # --------------------------------------------------
        
        #-------------------------------------------
        btn_ele_add = QPushButton("Add");
        btn_ele_del = QPushButton("Remove");
        btn_ele_add.setFont( Configuration.instancia().getFont() );
        btn_ele_del.setFont( Configuration.instancia().getFont() );
        btn_ele_add.clicked.connect(self.btn_ele_add_click);
        btn_ele_del.clicked.connect(self.btn_ele_del_click);
        CustomVLayout.widget_linha(self, self.page_ele, [btn_ele_add, btn_ele_del] );
        self.table_ele = CustomVLayout.widget_tabela(self, ["Name", "Type"], tamanhos=[QHeaderView.Stretch, QHeaderView.Stretch], double_click=self.table_ele_click);
        self.page_ele.addWidget(self.table_ele);
        self.table_ele_load();
        
        layout = QVBoxLayout();
        layout.addWidget( self.tab           );
        self.setLayout(   layout             );

    def txt_text_changed(self):
        self.element.text_label = self.txt_text.text();
    
    def btn_remover_click(self):
        self.close();
    
    def txt_descricao_changed(self):
        return;
    
    def table_ele_click(self):
        return;
    
    def btn_ele_del_click(self):
        return;
    
    def btn_ele_add_click(self):
        d = DialogEntityFind(self);
        d.exec();
        if d.entity != None:
            self.element.addEntity( d.entity );
            self.table_ele_load();
            return;
        return;
    
    def table_ele_load(self):
        self.table_ele.setRowCount( len( self.element.entitys ) );
        for i in range(len( self.element.entitys )):
            self.table_ele.setItem( i, 0, QTableWidgetItem( self.element.entitys[i]["entity"].text ) );
            self.table_ele.setItem( i, 1, QTableWidgetItem( self.element.entitys[i]["entity"].etype ) );
        return; 