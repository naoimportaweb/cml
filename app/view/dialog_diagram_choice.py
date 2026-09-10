import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QHeaderView, QTableWidgetItem, QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from classlib.entity import Entity;
from view.ui.customvlayout import CustomVLayout;
from view.dialogentityload import DialogEntityLoad;
from classlib.relationship.maprelationship import MapRelationship;
from classlib.organization_chart.organization_chart import OrganizationChart;
from classlib.timeline.timeline import Timeline;

class DialogDiagramChoice(QDialog):
    def __init__(self, form):
        super().__init__(form)
        self.option = 0;
        self.ptype = None;
        self.map = None;
        self.search_entity = None;
        self.entitys = None;
        self.setWindowTitle("Digram type")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.painel_new();
        self.painel_relatinship();
        self.painel_organization_chart();
        self.painel_timeline();
        self.layout_principal.pad();
        self.layout_principal.disable("organization");
        self.layout_principal.disable("relationship");
        self.layout_principal.disable("timeline");
        self.lbl_message = QLabel("");
        self.layout_principal.addWidget( self.lbl_message ) ;


    def painel_new(self):
        layout = QGridLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        btn_relationship = QPushButton("Relationship Diagram")
        btn_organzation_chart = QPushButton("Organization Chart Diagram")
        btn_timeline = QPushButton("Timeline (linha do tempo de um mapa)")
        btn_cancel = QPushButton("Cancel")
        layout.addWidget(btn_relationship, 1, 0)
        layout.addWidget(btn_organzation_chart, 2, 0)
        layout.addWidget(btn_timeline, 3, 0)
        layout.addWidget(btn_cancel, 6, 0)
        btn_relationship.clicked.connect(self.btn_relationship_click)
        btn_organzation_chart.clicked.connect(self.btn_organization_chart_click)
        btn_timeline.clicked.connect(self.btn_timeline_click)
        btn_cancel.clicked.connect(self.btn_cancel_click)
        self.layout_principal.addLayout( "new", layout );

    def btn_cancel_click(self):
        self.ptype = None;
        self.close();
    
    def btn_relationship_click(self):
        self.layout_principal.enable("relationship");
        self.layout_principal.disable("new");
        return;

    def btn_organization_chart_click(self):
        self.layout_principal.enable("organization");
        self.layout_principal.disable("new");
        return;

    def btn_timeline_click(self):
        self.layout_principal.enable("timeline");
        self.layout_principal.disable("new");
        return;

    #--------------------------------------------------------------
    # TIMELINE: e um documento como os outros dois (tem nome e entra na lista de abrir). O
    # mapa de origem e OPCIONAL: com mapa, a timeline projeta as datas dele; sem mapa, ela
    # mostra so os eventos que o analista marcar.
    def painel_timeline(self):
        layout = QVBoxLayout();
        lbl_name = QLabel("Timeline name:");
        lbl_name.setProperty("class", "normal");
        self.txt_timeline_name = QLineEdit();
        self.txt_timeline_name.setMinimumWidth(500);
        CustomVLayout.widget_linha(self, layout, [lbl_name, self.txt_timeline_name] );

        lbl_key = QLabel("Keyword:");
        lbl_key.setProperty("class", "normal");
        self.txt_timeline_key = QLineEdit();
        self.txt_timeline_key.setMinimumWidth(500);
        CustomVLayout.widget_linha(self, layout, [lbl_key, self.txt_timeline_key] );

        lbl_mapa = QLabel("Mapa de origem (opcional):");
        lbl_mapa.setProperty("class", "normal");
        self.txt_timeline_mapa = QLineEdit();
        self.txt_timeline_mapa.setMinimumWidth(500);
        self.txt_timeline_mapa.editingFinished.connect(self.txt_timeline_mapa_finish);
        CustomVLayout.widget_linha(self, layout, [lbl_mapa, self.txt_timeline_mapa] );

        self.table_timeline_search = CustomVLayout.widget_tabela(self, ["Mapa", "Keyword"],
            tamanhos=[QHeaderView.Stretch, QHeaderView.ResizeToContents], double_click=self.table_timeline_double);
        layout.addWidget( self.table_timeline_search );

        self.lbl_timeline_escolhido = QLabel("Nenhum mapa escolhido — a timeline terá só os eventos marcados.");
        CustomVLayout.widget_linha(self, layout, [self.lbl_timeline_escolhido] );

        btn_new_timeline = QPushButton("Create new Timeline");
        btn_new_timeline.clicked.connect(self.btn_new_timeline_click);
        CustomVLayout.widget_linha(self, layout, [btn_new_timeline] );

        self.layout_principal.addLayout( "timeline", layout );
        self.mapas_timeline = [];
        self.timeline_mapa_id = None;

    def txt_timeline_mapa_finish(self):
        resultado = MapRelationship().search( "%" + self.txt_timeline_mapa.text().strip() + "%" );
        # So mapa de relacionamento: organograma nao tem as datas que a timeline projeta.
        self.mapas_timeline = (resultado or {}).get("relationship") or [];
        self.table_timeline_search.setRowCount( len(self.mapas_timeline) );
        for i in range(len(self.mapas_timeline)):
            self.table_timeline_search.setItem( i, 0, QTableWidgetItem( str(self.mapas_timeline[i].get("name") or "") ) );
            self.table_timeline_search.setItem( i, 1, QTableWidgetItem( str(self.mapas_timeline[i].get("keyword") or "") ) );
        return;

    def table_timeline_double(self):
        indice = self.table_timeline_search.currentRow();
        if indice < 0 or indice >= len(self.mapas_timeline):
            return;
        # Duplo clique so ESCOLHE o mapa; quem cria a timeline e o botao.
        self.timeline_mapa_id = self.mapas_timeline[indice]["id"];
        self.lbl_timeline_escolhido.setText( "Mapa de origem: " + str(self.mapas_timeline[indice].get("name") or "") );
        if self.txt_timeline_name.text().strip() == "":
            self.txt_timeline_name.setText( "Timeline - " + str(self.mapas_timeline[indice].get("name") or "") );
        return;

    def btn_new_timeline_click(self):
        if self.txt_timeline_name.text().strip() == "":
            self.lbl_message.setText( "Enter a name." );
            return False;
        t = Timeline();
        if t.exists( self.txt_timeline_name.text().strip() ):
            self.lbl_message.setText( "This timeline already exists." );
            return False;
        t.name = self.txt_timeline_name.text().strip();
        t.keyword = self.txt_timeline_key.text().strip();
        t.diagram_relationship_id = self.timeline_mapa_id;
        if not t.create():
            self.lbl_message.setText( str(getattr(t, "ultimo_erro", "") or "Não foi possível criar.") );
            return False;
        # Recem-criada: carrega pelo mesmo caminho do abrir, para ja vir com o mapa projetado.
        t.load( t.id );
        self.map = t;
        self.close();
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
        self.entitys = Entity.search("organization", "%" + self.txt_organization_name.text() + "%");
        self.table_organization_search.setRowCount( len( self.entitys ) );
        for i in range(len( self.entitys )):
            self.table_organization_search.setItem( i, 0, QTableWidgetItem( self.entitys[i]["text_label"] ) );
        return;

    def table_organization_double(self):
        o = OrganizationChart(self.entitys[ self.table_organization_search.currentRow() ]["id"]);
        if o.create():
            self.map = o;
            self.close();
        return;

    # --------------------- RELATINSHIP MAP
    def painel_relatinship(self):
        layout = QVBoxLayout();
        lbl_name = QLabel("Organization Name:")
        lbl_name.setProperty("class", "normal")
        self.txt_relationship_name = QLineEdit()
        self.txt_relationship_name.setMinimumWidth(500);
        self.txt_relationship_name.editingFinished.connect(self.txt_relationship_name_finish);
        CustomVLayout.widget_linha(self, layout, [lbl_name, self.txt_relationship_name] );

        lbl_key = QLabel("Keyword:")
        lbl_key.setProperty("class", "normal");
        self.txt_relationship_key = QLineEdit()
        self.txt_relationship_key.setMinimumWidth(500);
        CustomVLayout.widget_linha(self, layout, [lbl_key, self.txt_relationship_key] );

        btn_new_relationship = QPushButton("Create new Diagram Relationship")
        btn_new_relationship.clicked.connect(self.btn_new_relationship_click)
        CustomVLayout.widget_linha(self, layout, [btn_new_relationship] );

        self.layout_principal.addLayout( "relationship", layout );
    def txt_relationship_name_finish(self):
        return;
    
    def btn_new_relationship_click(self):
        r = MapRelationship();
        if self.txt_relationship_name.text().strip() == "" or self.txt_relationship_key.text().strip() == "":
            self.lbl_message.setText( "Enter name and keyword." );
            return False;
        if r.exists(self.txt_relationship_name.text()):
            self.lbl_message.setText( "This diraggram already exists." );
            return False;

        r.name = self.txt_relationship_name.text();
        r.keyword = self.txt_relationship_key.text();
        if r.create():
            self.map = r;
            self.close();
        return;
