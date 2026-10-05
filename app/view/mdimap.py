# CADA MAPA PRECISA DEUMA CASCA, UMA PONTE ENTRE OS DADOS E A TELA.

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append(ROOT);

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QMdiArea, QMessageBox, QScrollArea, QTextEdit, QWidget, QHBoxLayout, QStackedWidget)

from view.ui.mapa_relationship_engine import MapaRelationshipEngine;
from view.ui.mapa_organization_chart_engine import MapaOrganizationChartEngine;
from view.ui.mapa_timeline_engine import MapaTimelineEngine;
from view.dialogentitylink import DialogEntityLink;
from view.dialog_entity_organization import DialogEntityOrganization;
from view.dialog_entity_person import DialogEntityPerson;
from view.dialog_entity_other import DialogEntityOther;
from view.dialogchoice import DialogChoiceEntity;
from view.ui.lista_diagrama import ListaDiagrama;
from classlib.relationship.comandos import Operacao;

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
        # do eixo (pode passar de dez mil px). O mapa de vinculos e o organograma NAO precisam:
        # os dois sao QGraphicsView, que ja e area rolavel com zoom proprio.
        if mapa.__class__.__name__ == "Timeline":
            area = QScrollArea();
            area.setWidget( self.painter_widget );
            area.setWidgetResizable(False);
            desenho = area;
        else:
            desenho = self.painter_widget;
        # Desenho e lista sao duas VISTAS do mesmo mapa (a List View do Maltego, SPEC.md §3.3),
        # por isso uma pilha na mesma janela em vez de um dialogo separado: alternar nao fecha
        # nada nem perde o que estava aberto. A lista so existe para o mapa de vinculos --
        # organograma e timeline tem outra estrutura.
        self.pilha = QStackedWidget();
        self.pilha.addWidget( desenho );
        self.lista = None;
        if mapa.__class__.__name__ == "MapRelationship":
            self.lista = ListaDiagrama( self, mapa );
            self.pilha.addWidget( self.lista );
        layout.addWidget( self.pilha );
        self.setLayout(layout)
        # A pilha de desfazer e do DOCUMENTO; a janela so escuta para redesenhar. Assim
        # nenhuma das cinco rotinas que mexem no mapa precisa saber que ha uma janela aberta.
        if getattr(mapa, "desfazer", None) != None:
            mapa.desfazer.indexChanged.connect( self.redesenhar );
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
            with Operacao(self.mapa, "Criar caixa"):
                map.addEntity( form.ptype, x, y );
        else:                   # ITEM EXISTENTE É AQUI
            if form.search_entity != None:
                with Operacao(self.mapa, "Trazer entidade para o mapa"):
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

    def apagar_selecionados(self):
        """Apaga as caixas/vinculos selecionados no canvas, avisando o que foi barrado."""
        if self.lista != None and self.mostrando_lista():
            return;
        selecionados = self.painter_widget.selecionados();
        if len(selecionados) == 0:
            return;
        resposta = QMessageBox.question(self, "Apagar",
                                        "Apagar %d item(ns) selecionado(s) do mapa?" % len(selecionados),
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No);
        if resposta != QMessageBox.Yes:
            return;
        try:
            apagados, barrados = self.painter_widget.apagar_selecionados();
        except Exception as erro:
            QMessageBox.warning(self, "Apagar", str(erro));
            return;
        self.redesenhar();
        if barrados > 0:
            QMessageBox.information(self, "Apagar",
                "%d apagado(s). %d não foi/foram apagado(s) por participar(em) de vínculo que ficou "
                "fora da seleção — selecione o vínculo junto, ou apague-o primeiro." % (apagados, barrados));

    def mostrando_lista(self):
        return self.lista != None and self.pilha.currentWidget() is self.lista;

    def alternar_lista(self):
        """Troca entre o desenho e a tabela. Devolve True se ficou na tabela, para a acao da
        barra saber em que estado marcar o botao."""
        if self.lista == None:
            return False;
        if self.mostrando_lista():
            self.pilha.setCurrentIndex(0);
            return False;
        self.lista.atualizar();
        self.pilha.setCurrentWidget( self.lista );
        return True;

    def redesenhar(self):
        """Refaz o pixmap a partir do modelo. Quem mexe no mapa por fora de um evento de
        mouse (os bots, por exemplo) precisa chamar isto: o redraw() so acontece na
        construcao do MdiMap e no mouseReleaseEvent do engine — sem ele, a entidade entra
        no modelo e a tela nao mostra nada."""
        self.painter_widget.redraw();
        self.painter_widget.update();
        # A lista le o modelo na hora de montar, entao tem de ser refeita junto -- senao ela
        # mostra o mapa de antes da alteracao.
        if self.lista != None:
            self.lista.atualizar();
        # O rotulo de Desfazer/Refazer na barra mostra QUAL acao sera desfeita, entao precisa
        # acompanhar o que acabou de acontecer na janela, nao so a troca de janela.
        atualizar = getattr(self.form_principal, "__atualizar_desfazer__", None);
        if atualizar != None:
            atualizar();

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
