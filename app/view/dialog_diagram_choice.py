import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QHeaderView, QTableWidgetItem, QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton, QSpinBox, QListWidget)

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
        self.painel_estrela();
        self.painel_regional();
        self.layout_principal.pad();
        self.layout_principal.disable("organization");
        self.layout_principal.disable("relationship");
        self.layout_principal.disable("timeline");
        self.layout_principal.disable("estrela");
        self.layout_principal.disable("regional");
        self.lbl_message = QLabel("");
        self.layout_principal.addWidget( self.lbl_message ) ;


    def painel_new(self):
        layout = QGridLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        btn_relationship = QPushButton("Relationship Diagram")
        btn_organzation_chart = QPushButton("Organization Chart Diagram")
        btn_timeline = QPushButton("Timeline (linha do tempo de um mapa)")
        btn_estrela = QPushButton("Estrela (uma entidade e o que se liga a ela)")
        btn_regional = QPushButton("Regional (um grupo por país)")
        btn_cancel = QPushButton("Cancel")
        layout.addWidget(btn_relationship, 1, 0)
        layout.addWidget(btn_organzation_chart, 2, 0)
        layout.addWidget(btn_timeline, 3, 0)
        layout.addWidget(btn_estrela, 4, 0)
        layout.addWidget(btn_regional, 5, 0)
        layout.addWidget(btn_cancel, 6, 0)
        btn_relationship.clicked.connect(self.btn_relationship_click)
        btn_organzation_chart.clicked.connect(self.btn_organization_chart_click)
        btn_timeline.clicked.connect(self.btn_timeline_click)
        btn_estrela.clicked.connect(self.btn_estrela_click)
        btn_regional.clicked.connect(self.btn_regional_click)
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

    def btn_estrela_click(self):
        self.layout_principal.enable("estrela");
        self.layout_principal.disable("new");
        return;

    #--------------------------------------------------------------
    # ESTRELA: ao contrario dos outros, ela NAO comeca vazia. O analista escolhe uma entidade
    # e o servidor traz o que se liga a ela no banco INTEIRO (Entity.neighborhood) -- vinculo
    # de qualquer mapa e associacao global do MISP. O resultado e um MAPA DE VINCULOS comum,
    # desenhado em estrela: salva, reabre, exporta e se edita como qualquer outro. Nao e um
    # quarto tipo de documento, e por isso nao precisou de tabela nova.

    def painel_estrela(self):
        layout = QGridLayout();
        layout.setContentsMargins(20, 20, 20, 20);
        layout.setSpacing(10);
        layout.addWidget(QLabel("Entidade do centro:"), 0, 0);
        self.lbl_estrela_entidade = QLabel("— nenhuma escolhida —");
        layout.addWidget(self.lbl_estrela_entidade, 0, 1);
        btn_buscar = QPushButton("Buscar...");
        btn_buscar.clicked.connect(self.btn_estrela_buscar_click);
        layout.addWidget(btn_buscar, 0, 2);

        layout.addWidget(QLabel("Diagram name:"), 1, 0);
        self.txt_estrela_name = QLineEdit();
        layout.addWidget(self.txt_estrela_name, 1, 1, 1, 2);
        layout.addWidget(QLabel("Keyword:"), 2, 0);
        self.txt_estrela_key = QLineEdit();
        layout.addWidget(self.txt_estrela_key, 2, 1, 1, 2);

        layout.addWidget(QLabel("Níveis:"), 3, 0);
        self.spin_estrela_niveis = QSpinBox();
        self.spin_estrela_niveis.setRange(1, 4);
        self.spin_estrela_niveis.setValue(1);
        self.spin_estrela_niveis.setToolTip("1 = só quem se liga direto a ela; 2 = os vizinhos dos vizinhos...");
        layout.addWidget(self.spin_estrela_niveis, 3, 1);

        layout.addWidget(QLabel("Teto por nível:"), 4, 0);
        self.spin_estrela_limite = QSpinBox();
        self.spin_estrela_limite.setRange(5, 300);
        self.spin_estrela_limite.setValue(60);
        self.spin_estrela_limite.setToolTip("Sem teto, o nível 2 de uma entidade movimentada traz meio banco.");
        layout.addWidget(self.spin_estrela_limite, 4, 1);

        btn_criar = QPushButton("Create star diagram");
        btn_criar.clicked.connect(self.btn_new_estrela_click);
        layout.addWidget(btn_criar, 5, 1);
        btn_voltar = QPushButton("Cancel");
        btn_voltar.clicked.connect(self.btn_cancel_click);
        layout.addWidget(btn_voltar, 5, 2);
        self.estrela_entidade = None;
        self.layout_principal.addLayout( "estrela", layout );

    def btn_estrela_buscar_click(self):
        # O DialogEntityFind devolve um objeto Entity (fromJson), nao o dicionario da busca --
        # dai os atributos .text/.etype/.id em vez de .get("text_label").
        from view.dialog_entity_find import DialogEntityFind;
        janela = DialogEntityFind(self);
        janela.exec();
        if janela.entity == None:
            return;
        self.estrela_entidade = janela.entity;
        nome = str(janela.entity.text or "");
        self.lbl_estrela_entidade.setText(nome + "  (" + str(janela.entity.etype or "") + ")");
        if self.txt_estrela_name.text().strip() == "":
            self.txt_estrela_name.setText("Estrela - " + nome);
        if self.txt_estrela_key.text().strip() == "":
            self.txt_estrela_key.setText(nome);

    def btn_new_estrela_click(self):
        from classlib.relationship import layouts;
        if self.estrela_entidade == None:
            self.lbl_message.setText("Escolha a entidade do centro.");
            return False;
        if self.txt_estrela_name.text().strip() == "" or self.txt_estrela_key.text().strip() == "":
            self.lbl_message.setText("Enter name and keyword.");
            return False;
        mapa = MapRelationship();
        if mapa.exists( self.txt_estrela_name.text().strip() ):
            self.lbl_message.setText("This diagram already exists.");
            return False;

        centro_id = self.estrela_entidade.id;
        entidades, vinculos, cortados = Entity.neighborhood(
            centro_id, self.spin_estrela_niveis.value(), self.spin_estrela_limite.value() );
        if entidades == None:
            self.lbl_message.setText( str(cortados) );   # na falha, o terceiro traz o motivo
            return False;

        mapa.name = self.txt_estrela_name.text().strip();
        mapa.keyword = self.txt_estrela_key.text().strip();
        if not mapa.create():
            self.lbl_message.setText("Não foi possível criar o diagrama.");
            return False;

        caixas = {};
        for dados in entidades:
            caixa = mapa.addEntity( dados.get("etype") or "other", 0, 0,
                                    text=dados.get("text_label"), entity_id_=dados.get("id"),
                                    wikipedia=dados.get("wikipedia") );
            caixa.entity = Entity.fromJson( dados );
            caixas[ dados.get("id") ] = caixa;
        for v in vinculos:
            de, para = caixas.get(v.get("de")), caixas.get(v.get("para"));
            if de == None or para == None:
                continue;   # ponta cortada pelo teto: vinculo pela metade nao entra
            # Associacao global do MISP vem sem verbo: dizer "associado a" e honesto, deixar
            # em branco faria o vinculo parecer um cadastro malfeito.
            elo = mapa.addEntity("link", 0, 0, text=(str(v.get("verbo") or "").strip() or "associado a"));
            elo.addFrom(de); elo.addTo(para);

        centro = caixas.get(centro_id);
        layouts.aplicar( mapa, "estrela", centro=centro, niveis=self.spin_estrela_niveis.value() );
        if cortados > 0:
            QMessageBox.information(self, "Estrela",
                "O teto por nível cortou %d entidade(s). Aumente o teto se precisar de mais."
                % cortados);
        self.map = mapa;
        self.close();
        return True;

    def btn_regional_click(self):
        self.layout_principal.enable("regional");
        self.layout_principal.disable("new");
        return;

    #--------------------------------------------------------------
    # REGIONAL: como a estrela, nao comeca vazio. O analista escolhe os PAISES e o servidor traz
    # quem se liga a cada um (Entity.neighborhood). Sai um mapa de vinculos comum, desenhado com
    # um grupo por pais -- e a vista "Mapa regional" (tabela com bandeiras) le o mesmo
    # documento. Nao e projecao geografica: o porque esta em classlib/relationship/regional.py.
    #
    # Pede os ROSTOS ao servidor (rosto=True) porque num mapa regional a bandeira e o desenho,
    # e por isso o mapa ja nasce com show_face ligado.

    def painel_regional(self):
        layout = QGridLayout();
        layout.setContentsMargins(20, 20, 20, 20);
        layout.setSpacing(10);
        layout.addWidget(QLabel("Países:"), 0, 0);
        self.lst_regional = QListWidget();
        self.lst_regional.setMinimumHeight(110);
        layout.addWidget(self.lst_regional, 0, 1, 2, 1);
        btn_add = QPushButton("Adicionar...");
        btn_add.clicked.connect(self.btn_regional_add_click);
        layout.addWidget(btn_add, 0, 2);
        btn_del = QPushButton("Remover");
        btn_del.clicked.connect(self.btn_regional_del_click);
        layout.addWidget(btn_del, 1, 2);

        layout.addWidget(QLabel("Diagram name:"), 2, 0);
        self.txt_regional_name = QLineEdit();
        layout.addWidget(self.txt_regional_name, 2, 1, 1, 2);
        layout.addWidget(QLabel("Keyword:"), 3, 0);
        self.txt_regional_key = QLineEdit();
        layout.addWidget(self.txt_regional_key, 3, 1, 1, 2);

        layout.addWidget(QLabel("Níveis:"), 4, 0);
        self.spin_regional_niveis = QSpinBox();
        self.spin_regional_niveis.setRange(1, 4);
        self.spin_regional_niveis.setValue(1);
        self.spin_regional_niveis.setToolTip("1 = só quem se liga direto ao país.");
        layout.addWidget(self.spin_regional_niveis, 4, 1);

        layout.addWidget(QLabel("Teto por nível:"), 5, 0);
        self.spin_regional_limite = QSpinBox();
        self.spin_regional_limite.setRange(5, 300);
        self.spin_regional_limite.setValue(60);
        self.spin_regional_limite.setToolTip("Vale por país: um país muito citado traria meio banco.");
        layout.addWidget(self.spin_regional_limite, 5, 1);

        self.lbl_regional_aviso = QLabel("");
        self.lbl_regional_aviso.setWordWrap(True);
        layout.addWidget(self.lbl_regional_aviso, 6, 0, 1, 3);

        btn_criar = QPushButton("Create regional map");
        btn_criar.clicked.connect(self.btn_new_regional_click);
        layout.addWidget(btn_criar, 7, 1);
        btn_voltar = QPushButton("Cancel");
        btn_voltar.clicked.connect(self.btn_cancel_click);
        layout.addWidget(btn_voltar, 7, 2);
        self.regional_paises = [];
        self.layout_principal.addLayout( "regional", layout );

    def btn_regional_add_click(self):
        from classlib.relationship import regional as paises_;
        from view.dialog_entity_find import DialogEntityFind;
        janela = DialogEntityFind(self);
        janela.exec();
        if janela.entity == None:
            return;
        if len([p for p in self.regional_paises if p.id == janela.entity.id]) > 0:
            return;   # o mesmo pais duas vezes nao acrescenta nada
        self.regional_paises.append( janela.entity );
        self.lst_regional.addItem( str(janela.entity.text or "") );
        # Entidade sem o sub-tipo "country" e AVISO, nao recusa: quem cadastrou a mao antes do
        # country_seed.py pode ter usado outra grafia, e o dono sabe o que tem no banco dele.
        # Mas sem o sub-tipo a vista com bandeiras nao a reconhece, e isso tem de ser dito.
        if len([p for p in self.regional_paises if not paises_.eh_pais_entidade(p)]) > 0:
            self.lbl_regional_aviso.setText(
                "Aviso: há entidade sem o sub-tipo “country”. Ela entra no mapa, mas a vista "
                "“Mapa regional” só agrupa por quem tem o sub-tipo (rode o script/country_seed.py).");
        if self.txt_regional_name.text().strip() == "":
            self.txt_regional_name.setText("Regional - " + str(janela.entity.text or ""));
        if self.txt_regional_key.text().strip() == "":
            self.txt_regional_key.setText("regional");

    def btn_regional_del_click(self):
        linha = self.lst_regional.currentRow();
        if linha < 0 or linha >= len(self.regional_paises):
            return;
        self.regional_paises.pop(linha);
        self.lst_regional.takeItem(linha);

    def btn_new_regional_click(self):
        from classlib.relationship import layouts;
        if len(self.regional_paises) == 0:
            self.lbl_message.setText("Escolha ao menos um país.");
            return False;
        if self.txt_regional_name.text().strip() == "" or self.txt_regional_key.text().strip() == "":
            self.lbl_message.setText("Enter name and keyword.");
            return False;
        mapa = MapRelationship();
        if mapa.exists( self.txt_regional_name.text().strip() ):
            self.lbl_message.setText("This diagram already exists.");
            return False;

        # Uma consulta por pais, e as respostas se juntam pelo id da entidade: a mesma pessoa
        # ligada a dois paises tem de virar UMA caixa com dois vinculos, nao duas caixas.
        entidades, vinculos, cortados = {}, [], 0;
        for pais in self.regional_paises:
            achadas, elos, corte = Entity.neighborhood(
                pais.id, self.spin_regional_niveis.value(), self.spin_regional_limite.value(),
                rosto=True );
            if achadas == None:
                self.lbl_message.setText( str(corte) );   # na falha, o terceiro traz o motivo
                return False;
            for dados in achadas:
                entidades.setdefault( dados.get("id"), dados );
            vinculos = vinculos + elos;
            cortados = cortados + int(corte or 0);

        mapa.name = self.txt_regional_name.text().strip();
        mapa.keyword = self.txt_regional_key.text().strip();
        mapa.show_face = True;   # a bandeira do pais E o desenho do mapa regional
        if not mapa.create():
            self.lbl_message.setText("Não foi possível criar o diagrama.");
            return False;

        caixas = {};
        for ident in entidades:
            dados = entidades[ident];
            caixa = mapa.addEntity( dados.get("etype") or "other", 0, 0,
                                    text=dados.get("text_label"), entity_id_=ident,
                                    wikipedia=dados.get("wikipedia") );
            caixa.entity = Entity.fromJson( dados );
            caixas[ ident ] = caixa;

        vistos = set();
        for v in vinculos:
            de, para = caixas.get(v.get("de")), caixas.get(v.get("para"));
            if de == None or para == None:
                continue;   # ponta cortada pelo teto: vinculo pela metade nao entra
            verbo = str(v.get("verbo") or "").strip() or "associado a";
            chave = (v.get("de"), v.get("para"), verbo);
            if chave in vistos:
                continue;   # dois paises podem ter trazido o mesmo vinculo
            vistos.add(chave);
            elo = mapa.addEntity("link", 0, 0, text=verbo);
            elo.addFrom(de); elo.addTo(para);

        layouts.aplicar( mapa, "regional" );
        if cortados > 0:
            QMessageBox.information(self, "Regional",
                "O teto por nível cortou %d entidade(s). Aumente o teto se precisar de mais."
                % cortados);
        self.map = mapa;
        self.close();
        return True;

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
