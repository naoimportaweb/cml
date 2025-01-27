import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QDate, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QTabWidget, QComboBox, QTableWidgetItem, QHeaderView, QMdiArea, QMessageBox, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from classlib.configuration import Configuration;
from view.ui.customvlayout import CustomVLayout;
from view.dialogreference import DialogReference;
from view.dialog_link_edit import DialogLinkEdit;
from view.ui.qeditorplus import QEditorPlus;

class DialogEntityLink(QDialog):
    def __init__(self, form, link, mapa):
        super().__init__(form)
        #self.resize(800, 660);
        nWidth = int(form.width() * 0.8); nHeight = int(form.height() * 0.6);
        if nWidth > 800:
            nWidth = 800;
        self.setGeometry(form.x() + form.width()/2 - nWidth/2,
            form.y() + form.height()/2 - nHeight/2,
            nWidth, nHeight);

        self.setWindowTitle("Relationship")
        self.link = link;
        self.mapa = mapa;
        self.elements_no_link = [];
        for element in self.mapa.elements:
            if element.entity.etype == "link":
                continue;
            self.elements_no_link.append(element);
        self.elements_no_link.sort(key=lambda x: x.entity.text);
        self.tab = QTabWidget();  
        self.page_rel      = CustomVLayout.widget_tab( self.tab, "Relationship");
        self.page_ent_from = CustomVLayout.widget_tab( self.tab, "Entity From");
        self.page_ent_to   = CustomVLayout.widget_tab( self.tab, "Entity To");
        self.page_ref      = CustomVLayout.widget_tab( self.tab, "References");
        self.page_act = CustomVLayout.widget_tab( self.tab, "Actions");
        # ------------------------------------------
        self.lbl_text = QLabel("Text");
        self.lbl_text.setText( self.link.entity.text ) ;
        self.txt_text = QLineEdit();
        self.txt_text.setFont( Configuration.instancia().getFont() );
        self.txt_text.setText( self.link.entity.text ) ;
        self.txt_text.textChanged.connect(self.txt_text_changed)
        CustomVLayout.widget_linha(self, self.page_rel, [self.lbl_text, self.txt_text] );
        
        self.txt_descricao = QEditorPlus();
        self.txt_descricao.setPlainText( self.link.entity.full_description );
        #self.txt_descricao.setLineWrapMode(QTextEdit.NoWrap);
        #self.txt_descricao.setFont( Configuration.instancia().getFont() );
        self.txt_descricao.textChanged.connect(self.txt_descricao_changed)
        #self.txt_descricao.setLineWrapMode(QTextEdit.WidgetWidth);  
        self.page_rel.addWidget( self.txt_descricao );
        #
        btn_remover = QPushButton("Remove");
        btn_remover.setFont( Configuration.instancia().getFont() );
        btn_remover.clicked.connect(self.btn_remover_click);
        CustomVLayout.widget_linha(self, self.page_act, [btn_remover] );
        # -----------------------------------------
        layout_from = QVBoxLayout();
        self.cmb_combo_from = QComboBox()
        for entity in self.elements_no_link:
            self.cmb_combo_from.addItem( entity.entity.text + "("+ entity.entity.etype +")" );
        
        btn_from_add = QPushButton("Add");
        btn_from_del = QPushButton("Remove");
        btn_from_dat = QPushButton("Date");
        btn_from_add.setFont( Configuration.instancia().getFont() );
        btn_from_del.setFont( Configuration.instancia().getFont() );
        btn_from_add.clicked.connect(self.btn_from_add_click);
        btn_from_del.clicked.connect(self.btn_from_del_click);

        CustomVLayout.widget_linha(self, layout_from, [ QLabel("<b>From:</b>")] );
        CustomVLayout.widget_linha(self, layout_from, [self.cmb_combo_from, btn_from_add, btn_from_del] );
        self.page_ent_from.addWidget( CustomVLayout.layout_to_widget( layout_from ) );
        self.table_from = CustomVLayout.widget_tabela(self, ["Type", "Text"], tamanhos=[QHeaderView.Stretch, QHeaderView.Stretch]);
        self.page_ent_from.addWidget(self.table_from);

        # -----------------------------------------
        layout_to = QVBoxLayout();
        self.cmb_combo_to = QComboBox()
        for entity in self.elements_no_link:
            self.cmb_combo_to.addItem( entity.entity.text + "("+ entity.entity.etype +")" );
        
        btn_to_add = QPushButton("Add");
        btn_to_del = QPushButton("Remove");
        btn_to_add.setFont( Configuration.instancia().getFont() );
        btn_to_del.setFont( Configuration.instancia().getFont() );
        btn_to_add.clicked.connect(self.btn_to_add_click);
        btn_to_del.clicked.connect(self.btn_to_del_click);
        CustomVLayout.widget_linha(self, layout_to, [ QLabel("<b>To:</b>")] );
        CustomVLayout.widget_linha(self, layout_to, [self.cmb_combo_to, btn_to_add] );
        CustomVLayout.widget_linha(self, layout_to, [ btn_to_del] );
        self.page_ent_to.addWidget( CustomVLayout.layout_to_widget( layout_to ) );
        self.table_to = CustomVLayout.widget_tabela(self, ["Type", "Text", "Start", "End"], tamanhos=[QHeaderView.Stretch, QHeaderView.Stretch, QHeaderView.Stretch, QHeaderView.Stretch], double_click=self.tbl_to_double);
        self.page_ent_to.addWidget(self.table_to);

        #-------------------------------------------
        btn_reference_add = QPushButton("Add");
        btn_reference_del = QPushButton("Remove");
        btn_reference_add.setFont( Configuration.instancia().getFont() );
        btn_reference_del.setFont( Configuration.instancia().getFont() );
        btn_reference_add.clicked.connect(self.btn_reference_add_click);
        btn_reference_del.clicked.connect(self.btn_reference_del_click);
        CustomVLayout.widget_linha(self, self.page_ref, [btn_reference_add, btn_reference_del] );
        self.table_reference = CustomVLayout.widget_tabela(self, ["Title"], tamanhos=[QHeaderView.Stretch], double_click=self.table_reference_click);
        self.page_ref.addWidget(self.table_reference);
        
        self.table_from_load();
        self.table_to_load();
        self.table_reference_load();

        layout = QVBoxLayout();
        layout.addWidget( self.tab           );
        self.setLayout(   layout             );

    def table_reference_load(self):
        self.table_reference.setRowCount( len( self.link.entity.references ) );
        for i in range(len( self.link.entity.references )):
            self.table_reference.setItem( i, 0, QTableWidgetItem( self.link.entity.references[i].title ) );
    
    def table_reference_click(self):
        element = self.link.entity.references[ self.table_reference.index() ];
        form = DialogReference(self, self.link, reference=element);
        form.exec();
        self.table_reference_load();

    def btn_reference_del_click(self):
        index = self.table_reference.index();
        self.link.entity.references.pop( index );
        self.table_reference_load();
    
    def btn_reference_add_click(self):
        form = DialogReference(self, self.link, reference=None);
        form.exec();
        self.table_reference_load();

    def table_from_load(self):
        self.table_from.setRowCount( len( self.link.from_entity ) );
        for i in range(len( self.link.from_entity )):
            self.table_from.setItem( i, 0, QTableWidgetItem( self.link.from_entity[i].entity.entity.etype ) );
            self.table_from.setItem( i, 1, QTableWidgetItem( self.link.from_entity[i].entity.entity.text ) );
    
    def table_to_load(self):
        self.table_to.setRowCount( len( self.link.to_entity ) );
        for i in range(len( self.link.to_entity )):
            self.table_to.setItem( i, 0, QTableWidgetItem( self.link.to_entity[i].entity.entity.etype ) );
            self.table_to.setItem( i, 1, QTableWidgetItem( self.link.to_entity[i].entity.entity.text ) );
            self.table_to.setItem( i, 2, QTableWidgetItem( QDate.fromString(self.link.to_entity[i].start_date, "yyyy-MM-dd" ).toString( self.link.to_entity[i].format_date )));
            self.table_to.setItem( i, 3, QTableWidgetItem( QDate.fromString(self.link.to_entity[i].end_date, "yyyy-MM-dd").toString( self.link.to_entity[i].format_date )));

    def btn_from_add_click(self):
        elemento = self.elements_no_link[ self.cmb_combo_from.currentIndex() ];
        if elemento != self.link  and not self.link.hasFrom(elemento)  and not self.link.hasTo(elemento):
            self.link.addFrom( elemento );
            self.table_from_load();
    
    def btn_to_add_click(self):
        elemento = self.elements_no_link[ self.cmb_combo_to.currentIndex() ];
        if elemento != self.link and not self.link.hasTo(elemento) and not self.link.hasFrom(elemento):
            self.link.addTo( elemento );
            self.table_to_load();

    def txt_text_changed(self):
        self.link.entity.text = self.txt_text.text();
    
    def txt_descricao_changed(self):
        self.link.entity.full_description = self.txt_descricao.toPlainText();
#
    def btn_to_del_click(self):
        self.link.delTo( self.table_to.currentRow() );
        self.table_to_load();

    def btn_from_del_click(self):
        self.link.delFrom( self.table_from.currentRow() );
        self.table_from_load();
    
    def btn_remover_click(self):
        self.link.mapa.delEntity(self.link);
        self.close();
    
    def tbl_to_double(self):
        f = DialogLinkEdit(self, self.link.to_entity[ self.table_to.currentRow() ]);
        f.exec();
        if f.ok:
            self.table_to_load();