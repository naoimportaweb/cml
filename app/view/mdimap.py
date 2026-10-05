# CADA MAPA PRECISA DEUMA CASCA, UMA PONTE ENTRE OS DADOS E A TELA.

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append(ROOT);

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QMdiArea, QMessageBox, QScrollArea, QTextEdit, QWidget, QHBoxLayout)

from view.ui.mapa_relationship_engine import MapaRelationshipEngine;
from view.ui.mapa_organization_chart_engine import MapaOrganizationChartEngine;
from view.ui.mapa_timeline_engine import MapaTimelineEngine;
from view.dialogentitylink import DialogEntityLink;
from view.dialog_entity_organization import DialogEntityOrganization;
from view.dialog_entity_person import DialogEntityPerson;
from view.dialog_entity_other import DialogEntityOther;
from view.dialogchoice import DialogChoiceEntity;

class MdiMap(QWidget):
    def __init__(self, form, mapa):
        super().__init__();
        self.form_principal = form;
        if mapa.__class__.__name__ == "OrganizationChart":
            self.painter_widget = MapaOrganizationChartEngine(parent=form, mapa=mapa, form=self);
        elif mapa.__class__.__name__ == "Timeline":
            self.painter_widget = MapaTimelineEngine(parent=form, mapa=mapa, form=self);
        else:
            self.painter_widget = MapaRelationshipEngine(parent=None, mapa=mapa, form=self);
        self.mapa = mapa;
        layout = QHBoxLayout()
        # A timeline entra numa QScrollArea porque e um QWidget que se redimensiona com o zoom
        # do eixo (pode passar de dez mil px). O mapa de vinculos NAO precisa: virou um
        # QGraphicsView, que ja e uma area rolavel com zoom proprio. O organograma segue sendo
        # o unico ainda preso ao pixmap fixo, sem rolagem (SPEC.md §3.1).
        if mapa.__class__.__name__ == "Timeline":
            area = QScrollArea();
            area.setWidget( self.painter_widget );
            area.setWidgetResizable(False);
            layout.addWidget( area );
        else:
            layout.addWidget( self.painter_widget );
        self.setLayout(layout)
        self.painter_widget.redraw();
        

    def entity_double_click(self, entity):
        if entity.entity.etype == "person":
            form = DialogEntityPerson( self.form_principal,entity);
        elif entity.entity.etype == "other":
            form = DialogEntityOther(  self.form_principal,entity);
        elif entity.entity.etype == "organization":
            form = DialogEntityOrganization(self.form_principal,entity);
        elif entity.entity.etype == "link":
            form = DialogEntityLink(   self.form_principal, entity, self.mapa);
        form.exec();
    
    def map_double_click(self, map, x, y):
        form = DialogChoiceEntity(self.form_principal);
        form.exec();
        if form.ptype != None:  # NOVO ITEM É AQUI
            map.addEntity( form.ptype, x, y );
        else:                   # ITEM EXISTENTE É AQUI
            if form.search_entity != None:
                map.addExistEntity(form.search_entity, x, y);

    def menu_transforms(self, caixa, pos_global):
        """Botao direito numa caixa: lista os transforms que aceitam o tipo dela, agrupados por
        fonte. Os indisponiveis ficam visiveis e desabilitados, com o motivo no rotulo."""
        from PySide6.QtWidgets import QMenu;
        from transform.nucleo import Registro, indisponivel, backend_llm, ROTULO_FONTE, FONTES;
        from view.ui.transform_manager import TransformManager;
        e = caixa.entity;
        if e.etype not in ("person", "organization", "other"):
            return;
        cfgs = Registro().para_entidade(e.etype, e.sub_etype_name or "");
        menu = QMenu(self);
        if not cfgs:
            menu.addAction("Nenhum transform para este tipo").setEnabled(False);
        travado = self.mapa.getLocked();
        for fonte in FONTES:
            grupo = [c for c in cfgs if c["fonte"] == fonte];
            if not grupo:
                continue;
            sub = menu.addMenu(ROTULO_FONTE[fonte] + (" · " + backend_llm() if fonte == "ia" else ""));
            for c in grupo:
                motivo = indisponivel(c, travado);
                acao = sub.addAction(c["nome"] + ((" — " + motivo) if motivo else ""));
                acao.setEnabled(motivo == None);
                if motivo == None:
                    acao.triggered.connect(lambda _c=False, cfg=c: self.executar_transform(cfg, caixa));
        menu.exec(pos_global);

    def entrada_transform(self, caixa):
        e = caixa.entity;
        urls = [];
        for r in e.references:
            for u in (r.link1, r.link2, r.link3):
                if u and u not in urls:
                    urls.append(u);
        return { "id": e.id, "text_label": e.text, "etype": e.etype, "sub_etype": e.sub_etype_name or "",
                 "small_label": e.small_label or "", "description": e.full_description or "",
                 "wikipedia": e.wikipedia, "default_url": e.default_url, "urls": urls,
                 "idioma": getattr(self.mapa, "language", None) or "en" };

    def executar_transform(self, cfg, caixa):
        from view.ui.transform_manager import TransformManager;
        TransformManager.instancia().iniciar(cfg, self.entrada_transform(caixa), self, caixa);

    def redesenhar(self):
        """Refaz o pixmap a partir do modelo. Quem mexe no mapa por fora de um evento de
        mouse (os bots, por exemplo) precisa chamar isto: o redraw() so acontece na
        construcao do MdiMap e no mouseReleaseEvent do engine — sem ele, a entidade entra
        no modelo e a tela nao mostra nada."""
        self.painter_widget.redraw();
        self.painter_widget.update();

    def new_map(self):
        return;

    def load_file(self, fileName):
        return;

    def save(self):
        self.mapa.save();

    def save_as(self):
        return;

    def save_file(self, fileName):
        return;

    def user_friendly_current_file(self):
        return;

    def current_file(self):
        return;

    def closeEvent(self, event):
        return;

    def document_was_modified(self):
        return;

    def maybe_save(self):
        return;

    def set_current_file(self, fileName):
        return;

    def stripped_name(self, fullFileName):
        return;
