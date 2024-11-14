import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QDate, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QComboBox, QApplication, QFileDialog, QMainWindow, QHeaderView, QTableWidgetItem, QComboBox, QDateEdit, QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );

sys.path.append( ROOT );
sys.path.append("/opt/cml/app/");

from view.ui.customvlayout import CustomVLayout;
from classlib.server import Server;
from classlib.configuration import Configuration;
from classlib.classification import Classification;

class DialogClassification(QDialog):
    def __init__(self, form, entity):
        super().__init__(form);
        self.form = form;
        self.entity = entity;
        nWidth = int(form.width() * 1); nHeight = int(form.height() * 1);
        if nWidth > 800:
            nWidth = 800;
        self.setGeometry(form.x() + form.width()/2 - nWidth/2,
            form.y() + form.height()/2 - nHeight/2,
            nWidth, nHeight);

        self.table_classification = None;
        self.setWindowTitle("Search Classification")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.cmb_type = QComboBox()
        self.cmb_type.setFont( Configuration.instancia().getFont() );
        self.ui_search_classification();
        self.ui_tabela();

        btn_alterar_type = QPushButton("Select classification");
        btn_alterar_type.setFont( Configuration.instancia().getFont() );
        btn_alterar_type.setFocusPolicy(Qt.NoFocus);
        btn_alterar_type.clicked.connect(self.btn_alterar_type_click);
        
        self.btn_start_date_enable = QPushButton("Enable");
        self.btn_end_date_enable = QPushButton("Enable");
        self.start_date_flag = False;
        self.end_date_flag = False;
        self.btn_start_date_enable.setFocusPolicy(Qt.NoFocus);
        self.btn_end_date_enable.setFocusPolicy(Qt.NoFocus);
        self.btn_start_date_enable.clicked.connect(self.btn_start_date_enable_click);
        self.btn_end_date_enable.clicked.connect(self.btn_end_date_enable_click);
        self.start_date = QDateEdit(self);
        self.end_date =   QDateEdit(self)
        self.start_date.setVisible(False);
        self.end_date.setVisible(False);
        self.start_date.setDate(QDate.currentDate());
        self.end_date.setDate(QDate.currentDate());
        self.start_date.setDisplayFormat("dd-MM-yyyy");
        self.end_date.setDisplayFormat("dd-MM-yyyy");
        lbl_start_date = QLabel("Start Date");
        lbl_end_date = QLabel("End Date");
        CustomVLayout.widget_linha(self, self.layout_principal, [lbl_start_date, self.start_date, self.btn_start_date_enable] );
        CustomVLayout.widget_linha(self, self.layout_principal, [lbl_end_date, self.end_date, self.btn_end_date_enable] );
        self.combo_format_date = QComboBox();
        self.combo_format_date.addItem("yyyy-MM-dd");
        self.combo_format_date.addItem("yyyy-MM");
        self.combo_format_date.addItem("yyyy");
        self.combo_format_date.currentTextChanged.connect(self.combo_format_date_changed)
        CustomVLayout.widget_linha(self, self.layout_principal, [self.combo_format_date] );
        CustomVLayout.widget_linha(self, self.layout_principal, [self.cmb_type, btn_alterar_type] );
        
    def ui_search_classification(self):
        layout_server = QGridLayout()
        layout_server.setContentsMargins(20, 20, 20, 20)
        layout_server.setSpacing(10)
        lbl_name = QLabel("Name:")
        lbl_name.setProperty("class", "normal")
        layout_server.addWidget(lbl_name, 1, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setMinimumWidth(500);
        layout_server.addWidget(self.txt_name, 1, 1);
        self.txt_name.editingFinished.connect(self.txt_name_finish);   
        self.layout_principal.addLayout( "search", layout_server );

    def ui_tabela(self):
        layout = QVBoxLayout();
        self.table_classification = CustomVLayout.widget_tabela(self, ["Name"], tamanhos=[QHeaderView.Stretch], double_click=self.table_classification_double);
        layout.addWidget(self.table_classification);
        self.layout_principal.addLayout( "list", layout );

    def txt_name_finish(self):
        c = Classification();
        self.classifications = c.search("%" + self.txt_name.text().strip() + "%");
        self.table_classification.setRowCount( len( self.classifications ) );
        for i in range(len( self.classifications )):
            self.table_classification.setItem( i, 0, QTableWidgetItem( self.classifications[i]["text_label"] ) );
        return;
    
    def table_classification_double(self):
        for buffer in self.classifications[self.table_classification.index()]["itens"]:
            self.cmb_type.addItem( buffer["text_label"] )
        return;
    
    def btn_alterar_type_click(self):
        buffer_end_date = None;
        buffer_start_date = None;
        if self.start_date_flag:
            buffer_start_date = self.start_date.date().toString("yyyy-MM-dd");
        if self.end_date_flag:
            buffer_end_date =    self.end_date.date().toString("yyyy-MM-dd");
        
        if self.entity.addClassification(self.classifications[self.table_classification.index()]["id"] , self.classifications[self.table_classification.index()]["text_label"], self.classifications[self.table_classification.index()]["itens"][self.cmb_type.currentIndex()]["id"], self.classifications[self.table_classification.index()]["itens"][self.cmb_type.currentIndex()]["text_label"], buffer_start_date, buffer_end_date, self.combo_format_date.currentText()):
            self.form.table_class_load();
            self.close();
        return;
    def btn_start_date_enable_click(self):
        if self.start_date_flag:
            self.start_date_flag = False;
            self.start_date.setVisible(False);
            self.btn_start_date_enable.setText("Enable");
        else:
            self.start_date_flag = True;
            self.start_date.setVisible(True);
            self.btn_start_date_enable.setText("Disable");

    def btn_end_date_enable_click(self):
        if self.end_date_flag:
            self.end_date_flag = False;
            self.end_date.setVisible(False);
            self.btn_end_date_enable.setText("Enable");
        else:
            self.end_date_flag = True;
            self.end_date.setVisible(True);
            self.btn_end_date_enable.setText("Disable");

    def combo_format_date_changed(self):
        self.start_date.setDisplayFormat(self.combo_format_date.currentText());
        self.end_date.setDisplayFormat(self.combo_format_date.currentText());