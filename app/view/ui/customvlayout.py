

from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
from PySide6.QtGui import QPalette;
from PySide6.QtCore import Qt;
#from PySide6 import QtWidgets;
#from PySide6.QtWidgets import QGridLayout,QTextEdit, QTabWidget, QLineEdit, QDialog, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QTableWidget,
# QTableWidgetItem, QLabel, QAbstractItemView, QHeaderView;

class Table(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent);
        self.lista = [];
        self.total_linhas = 0;
    def cleanList(self):
        self.lista = [];
        self.total_linhas = 0;
        self.setRowCount( 0 );
    def add(self, array_colunas, objeto):
        self.setRowCount( self.total_linhas + 1 );
        for i in range(len(array_colunas)):
            self.setItem( self.total_linhas , i, QTableWidgetItem( array_colunas[i] ) );
        self.lista.append( objeto );
        self.total_linhas += 1;
    def get(self):
        return self.lista[self.currentRow()];
    def index(self):
        return self.currentRow();

class CustomVLayout(QVBoxLayout):
    def __init__(self):
        super().__init__();
        self.layouts = {};

    def pad(self):
        self.addStretch();
    
    def addLayout(self, name, layout):
        widget1 = QWidget();
        widget1.setLayout(   layout );
        self.addWidget(      widget1 );
        self.layouts[ name ] =  widget1 ;

    def __enable_disable__(self, name, active):
        self.layouts[ name ].setVisible( active );
    def disable(self, name):
        self.__enable_disable__(name, False);
    def enable(self, name):
        self.__enable_disable__(name, True);
    #def toWidget(self):
    #    widget1 = QWidget();
    #    widget1_layout = QHBoxLayout();
    #    widget1.setLayout(widget1_layout);
    #    for control in controls:
    #        widget1_layout.addWidget( control );
    #    return widget1;
    
    @staticmethod
    def widget_linha(form, layout, controls, stretch_inicio=False, stretch_fim=False):
        widget1 = QWidget(form);
        widget1_layout = QHBoxLayout();
        widget1.setLayout(widget1_layout);
        if stretch_inicio:
            widget1_layout.addStretch();
        for control in controls:
            if type(control).__name__ == type("").__name__:
                widget1_layout.addStretch();
                continue;
            widget1_layout.addWidget( control );
        if stretch_fim:
            widget1_layout.addStretch();
        layout.addWidget(widget1);
    
    @staticmethod
    def widget_layout(form, controls):
        widget1 = QWidget(form);
        widget1_layout = QHBoxLayout();
        widget1.setLayout(widget1_layout);
        for control in controls:
            widget1_layout.addWidget( control );
        return widget1;

    @staticmethod
    def layout_to_widget(widget1_layout):
        widget1 = QWidget();
        widget1.setLayout(widget1_layout);
        return widget1;

    @staticmethod
    def widget_tab(tab, titulo):
        page = QWidget(tab);
        page_layout=QVBoxLayout()
        page.setLayout(page_layout);
        tab.addTab( page, titulo );
        return page_layout;
    
    @staticmethod
    def widget_tabela(form, colunas, tamanhos=None, double_click=None):
        if tamanhos == None:
            tamanhos = [];
            for i in range(len(colunas)):
                if i == 0:
                    tamanhos.append(QHeaderView.Stretch);
                else:
                    tamanhos.append(QHeaderView.ResizeToContents);
        table = Table(form);
        if double_click != None:
            table.doubleClicked.connect( double_click );
        js = {};
        for coluna in colunas:
            js[coluna] = "";
        table.setSelectionBehavior(QAbstractItemView.SelectRows); 
        table.setColumnCount(len(colunas));
        table.setEditTriggers(QAbstractItemView.NoEditTriggers);
        table.setHorizontalHeaderLabels(js.keys());
        header = table.horizontalHeader() 
        for i in range(len(tamanhos)):
            header.setSectionResizeMode(i, tamanhos[i]);
        table.setRowCount(0)
        return table;
