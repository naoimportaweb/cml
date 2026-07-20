import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QHeaderView, QTableWidgetItem, QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton, QComboBox)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );

sys.path.append( ROOT );
sys.path.append("/opt/cml/app/");

from view.ui.customvlayout import CustomVLayout;
from classlib.server import Server;
from classlib.relationship.maprelationship import MapRelationship;
from classlib.relationship.person import Person
from classlib.relationship.organization import Organization
from classlib.relationship.other import Other
from classlib.relationship.link import Link
from classlib.organization_chart.organization_chart import OrganizationChart

class DialogDiagramLoad(QDialog):
    def __init__(self, form):
        super().__init__(form);
        
        nWidth = int(form.width() * 0.8); nHeight = int(form.height() * 0.6);
        self.setGeometry(form.x() + form.width()/2 - nWidth/2,
            form.y() + form.height()/2 - nHeight/2,
            nWidth, nHeight);

        self.map = None;
        self.setWindowTitle("Connect")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.ui_search_relationship();
        self.ui_tabela();
        
    def ui_search_relationship(self):
        layout_server = QGridLayout()
        layout_server.setContentsMargins(20, 20, 20, 20)
        layout_server.setSpacing(10)
        self.setWindowTitle("Map Search")
        lbl_name = QLabel("Map name:")
        lbl_name.setProperty("class", "normal")
        layout_server.addWidget(lbl_name, 1, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setMinimumWidth(500);
        layout_server.addWidget(self.txt_name, 1, 1);
        self.txt_name.editingFinished.connect(self.txt_name_finish);

        lbl_ordem = QLabel("Sort:");
        lbl_ordem.setProperty("class", "normal");
        layout_server.addWidget(lbl_ordem, 2, 0);
        self.combo_ordem = QComboBox();
        # (rotulo, chave, comeca decrescente?)
        # O DEFAULT e o primeiro item: "Data de edição" (decrescente) — o mapa em que o
        # usuario mexeu por ultimo vem no topo, que e o que se quer ao entrar. Nome/Tipo/
        # Usuario continuam disponiveis no combo.
        self.ordens = [ ("Data de edição",  "data",  True),
                        ("Nome",            "nome",  False),
                        ("Tipo",            "tipo",  False),
                        ("Usuário",         "user",  False) ];
        for rot, _, _ in self.ordens:
            self.combo_ordem.addItem(rot);
        self.combo_ordem.currentIndexChanged.connect(self.__reordenar__);
        layout_server.addWidget(self.combo_ordem, 2, 1);
        self.layout_principal.addLayout( "search", layout_server );

    def ui_tabela(self):
        layout = QVBoxLayout();
        self.linhas = [];
        self.table_maps = CustomVLayout.widget_tabela(self, ["User", "Name", "Map Type", "Edited"], tamanhos=[QHeaderView.ResizeToContents, QHeaderView.Stretch, QHeaderView.ResizeToContents, QHeaderView.ResizeToContents], double_click=self.table_maps_double);
        layout.addWidget(self.table_maps);
        self.layout_principal.addLayout( "list", layout );

    def txt_name_finish(self):
        r = MapRelationship();
        self.mapas = r.search( "%" + self.txt_name.text().strip() + "%");

        # Uma lista PLANA com o dado de cada linha junto. Antes a tabela era montada em dois
        # lacos e o duplo clique descobria o tipo por aritmetica de indice
        # ("if index < len(relationship)"), o que amarrava a ordem da tela a ordem das duas
        # listas — por isso o sort estava comentado: qualquer reordenacao abriria o mapa
        # errado.
        self.linhas = [];
        for m in self.mapas["relationship"]:
            self.linhas.append({
                "kind": "relationship", "id": m["id"],
                "user": str(m.get("username") or ""),
                "nome": str(m.get("name") or ""),
                "tipo": "Relationship Map",
                "data": str(m.get("modification_time") or m.get("creation_time") or ""),
            });
        for m in self.mapas["organization"]:
            self.linhas.append({
                "kind": "organization", "id": m["id"], "organization_id": m["organization_id"],
                "user": str(m.get("username") or ""),
                "nome": str(m.get("organization_text_label") or "") + " - " + str(m.get("name") or ""),
                "tipo": "Organization Chart",
                "data": str(m.get("modification_time") or m.get("creation_time") or ""),
            });
        self.__reordenar__();

    def __reordenar__(self):
        i = self.combo_ordem.currentIndex();
        if i < 0 or i >= len(self.ordens):
            i = 0;
        _, chave, desc = self.ordens[i];

        # Tres passadas, aproveitando que o sort do Python e estavel: cada uma agrupa por
        # cima da anterior. A data vem do MySQL como 'YYYY-MM-DD HH:MM:SS', que ordena certo
        # comparada como string.

        # 1) desempate: dentro do mesmo tipo ou do mesmo usuario, alfabetico. Sem isto a
        #    ordem interna e o resto da ordenacao anterior — parece aleatorio para quem le.
        self.linhas.sort(key=lambda l: str(l.get("nome") or "").lower());

        # 2) o criterio pedido
        self.linhas.sort(key=lambda l: str(l.get(chave) or "").lower(), reverse=desc);

        # 3) sem valor vai para o fim nos DOIS sentidos: um mapa sem data nao e "o mais
        #    antigo", so nao tem a informacao. O reverse do passo 2 os jogaria para o topo.
        self.linhas.sort(key=lambda l: 0 if str(l.get(chave) or "") else 1);
        self.__listar__();

    def __listar__(self):
        self.table_maps.setRowCount( len(self.linhas) );
        for i, l in enumerate(self.linhas):
            self.table_maps.setItem( i, 0, QTableWidgetItem( l["user"] ) );
            self.table_maps.setItem( i, 1, QTableWidgetItem( l["nome"] ) );
            self.table_maps.setItem( i, 2, QTableWidgetItem( l["tipo"] ) );
            self.table_maps.setItem( i, 3, QTableWidgetItem( self.__data__( l["data"] ) ) );

    @staticmethod
    def __data__(s):
        if not s:
            return "—";
        p = str(s).split(" ")[0].split("-");
        return (p[2] + "/" + p[1] + "/" + p[0]) if len(p) == 3 else str(s);

    def table_maps_double(self):
        index = self.table_maps.index();
        if index < 0 or index >= len(self.linhas):
            return;
        # A linha carrega o proprio id e tipo: a ordem da tela nao importa mais.
        l = self.linhas[index];
        if l["kind"] == "relationship":
            r = MapRelationship();
            if r.load( l["id"] ):
                self.map = r;
                self.close();
        else:
            o = OrganizationChart( l["organization_id"] );
            if o.load( l["id"] ):
                self.map = o;
                self.close();


