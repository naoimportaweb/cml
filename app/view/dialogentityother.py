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
from classlib.configuration import Configuration;
from view.dialog_classification import DialogClassification;

class DialogEntityOther(QDialog):
    def __init__(self, form, other):
        super().__init__()
        nWidth = int(form.width() * 0.8); nHeight = int(form.height() * 0.6);
        if nWidth > 800:
            nWidth = 800;
        self.setGeometry(form.x() + form.width()/2 - nWidth/2,
            form.y() + form.height()/2 - nHeight/2,
            nWidth, nHeight);

        self.setWindowTitle("Other")
        self.other = other;
        self.tab = QTabWidget();  
        self.page_rel = CustomVLayout.widget_tab( self.tab, "other");
        self.page_pho = CustomVLayout.widget_tab( self.tab, "Photo");
        self.page_ref = CustomVLayout.widget_tab( self.tab, "References");
        self.page_cls = CustomVLayout.widget_tab( self.tab, "Classification");
        self.page_act = CustomVLayout.widget_tab( self.tab, "Actions");
        # ------------------------------------------
        self.lbl_text = QLabel("Text");
        self.txt_text = QLineEdit();
        self.txt_text.setFont( Configuration.instancia().getFont() );
        self.txt_text.setText( self.other.entity.text ) ;
        self.txt_text.textChanged.connect(self.txt_text_changed)
        CustomVLayout.widget_linha(self, self.page_rel, [self.lbl_text, self.txt_text] );
        
        self.txt_descricao = QTextEdit();
        self.txt_descricao.setPlainText( other.entity.full_description );
        self.txt_descricao.setLineWrapMode(QTextEdit.NoWrap);
        self.txt_descricao.setFont( Configuration.instancia().getFont() );
        self.txt_descricao.textChanged.connect(self.txt_descricao_changed)
        self.txt_descricao.setLineWrapMode(QTextEdit.WidgetWidth);  
        self.page_rel.addWidget( self.txt_descricao );
        # --------------------------------------------------
        #-------------------------------------------
        self.cmb_type = QComboBox()
        self.cmb_type.setFont( Configuration.instancia().getFont() );
        self.cmb_type.addItem('Person')
        self.cmb_type.addItem('Organization')
        btn_alterar_type = QPushButton("Switch to type");
        btn_alterar_type.setFont( Configuration.instancia().getFont() );
        btn_alterar_type.clicked.connect(self.btn_alterar_type_click);
        CustomVLayout.widget_linha(self, self.page_act, [self.cmb_type, btn_alterar_type] );
        btn_remover = QPushButton("Remove");
        btn_remover.setFont( Configuration.instancia().getFont() );
        btn_remover.clicked.connect(self.btn_remover_click);
        CustomVLayout.widget_linha(self, self.page_act, [btn_remover] );
        #-------------------------------------------
        btn_class_add = QPushButton("Add");
        btn_class_del = QPushButton("Remove");
        btn_class_add.setFont( Configuration.instancia().getFont() );
        btn_class_del.setFont( Configuration.instancia().getFont() );
        btn_class_add.clicked.connect(self.btn_class_add_click);
        btn_class_del.clicked.connect(self.btn_class_del_click);
        CustomVLayout.widget_linha(self, self.page_cls, [btn_class_add, btn_class_del] );
        self.table_class = CustomVLayout.widget_tabela(self, ["Classification", "Value"], tamanhos=[QHeaderView.Stretch, QHeaderView.Stretch], double_click=self.table_class_click);
        self.page_cls.addWidget(self.table_class);
        self.table_class_load();
        #
        btn_reference_add = QPushButton("Add");
        btn_reference_add.setFont( Configuration.instancia().getFont() );
        btn_reference_del = QPushButton("Remove");
        btn_reference_del.setFont( Configuration.instancia().getFont() );
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
    def btn_remover_click(self):
        self.other.mapa.delEntity(self.other);
        self.close();
    def txt_descricao_changed(self):
        self.other.entity.full_description = self.txt_descricao.toPlainText();
    def btn_alterar_type_click(self):
        etype = "";
        if self.cmb_type.currentIndex() == 0:
            etype = "person";
        elif self.cmb_type.currentIndex() == 1:
            etype = "organization"; 
        retorno = self.other.setType( etype );
        if retorno:
            self.close();
    def table_class_click(self):
        return;
    
    def btn_class_del_click(self):
        self.other.entity.classification.pop(self.table_class.index());
        self.table_class_load();
        return;
    
    def btn_class_add_click(self):
        d = DialogClassification(self, self.other.entity);
        d.exec();
        return;
    
    def table_class_load(self):
        
        self.table_class.setRowCount( len( self.other.entity.classification ) );
        for i in range(len( self.other.entity.classification )):
            self.table_class.setItem( i, 0, QTableWidgetItem( self.other.entity.classification[i]["text_label"] ) );
            self.table_class.setItem( i, 1, QTableWidgetItem( self.other.entity.classification[i]["text_label_choice"] ) );
        return;