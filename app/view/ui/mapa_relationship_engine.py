# CADA MAPA POSSUI UMA FORMA DE DESENHAR, CLICAR, SELECIONAR, ISSO FICA AQUI
#
# Canvas do mapa de vinculos. Era um QWidget com setFixedSize(5000, 3000) e um QPixmap do mesmo
# tamanho (~57 MB) refeito INTEIRO a cada mouseMoveEvent; como o MdiMap so embrulha a timeline
# numa area rolavel, o mapa nao rolava nem dava zoom e caixa arrastada para fora da parte
# visivel ficava inalcancavel. Agora e um QGraphicsView (SPEC.md §3.1): rolagem e zoom vem do
# framework, e so o que mudou e repintado.
#
# O que NAO mudou de proposito: as regras de desenho continuam no modelo (draw(painter) de cada
# element), o sorteio de clique continua sendo o do mapa (ultimo elemento por cima) e a API que
# o MdiMap e os dialogos usam -- redraw(), addEntity(), addExistEntity(), getElement(), mapa --
# segue igual.

from PySide6.QtWidgets import (QGraphicsItem, QGraphicsScene, QGraphicsView, QMenu);
from PySide6.QtCore import Qt, QRectF;
from PySide6.QtGui import (QMouseEvent, QPainter, QPainterPath, QPixmap, QTransform);

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( CURRENTDIR ) ) );

from classlib.entity import Entity;
from classlib.exportar_diagrama import fonte_do_diagrama;
from classlib.relationship.comandos import ComandoMapa, mudou, tirar_instantaneo;

ZOOM_MIN = 0.15;
ZOOM_MAX = 4.0;
ZOOM_PASSO = 1.15;
FOLGA_CENA = 60;    # respiro em volta do conteudo, para dar onde arrastar e onde soltar


class ItemElemento(QGraphicsItem):
    """Um item por element do mapa. Nao guarda geometria propria: le x/y/w/h do modelo e
    desenha com o draw() dele. O item fica sempre em (0,0) e pinta em coordenada absoluta --
    assim nao existem duas verdades sobre onde a caixa esta (a do Qt e a do modelo)."""

    def __init__(self, elemento):
        super().__init__();
        self.elemento = elemento;
        self.setFlag(QGraphicsItem.ItemIsSelectable, True);

    def __retangulo__(self):
        e = self.elemento;
        return QRectF(e.x or 0, e.y or 0, e.w or 1, e.h or 1);

    def boundingRect(self):
        # Area PINTADA. O vinculo e hiper-aresta: desenha linhas da caixa do verbo ate cada
        # ponta, entao o retangulo dele tem de cobrir as pontas, senao o Qt corta as linhas.
        retangulo = self.__retangulo__();
        if self.elemento.entity.etype == "link":
            for ponta in list(self.elemento.to_entity) + list(self.elemento.from_entity):
                alvo = ponta.entity;
                if alvo == None or alvo.w == None or alvo.h == None:
                    continue;
                retangulo = retangulo.united(QRectF(alvo.x or 0, alvo.y or 0, alvo.w, alvo.h));
        return retangulo.adjusted(-8, -8, 8, 8);

    def shape(self):
        # Area CLICAVEL: so o retangulo do proprio element, inclusive para o vinculo (clica-se
        # na caixa do verbo, nao na linha). E o mesmo criterio do getElement de antes -- se
        # fosse o boundingRect, o vinculo engoliria o clique de tudo que esta entre as pontas.
        caminho = QPainterPath();
        caminho.addRect(self.__retangulo__());
        return caminho;

    def paint(self, painter, option, widget=None):
        # O draw() do modelo nao define fonte: quem abre o painter e que define.
        painter.setFont(fonte_do_diagrama());
        self.elemento.draw(painter);

    def atualizar(self):
        self.prepareGeometryChange();
        self.update();


class MapaRelationshipEngine(QGraphicsView):
    def __init__(self, parent=None, mapa=None, form=None, max_width=5000, max_height=3000):
        # max_width/max_height sobrevivem so por compatibilidade de assinatura: o tamanho agora
        # e o do conteudo, nao uma moldura fixa.
        super().__init__(parent);
        self.form = form;
        self.mapa = mapa;
        self.itens = [];
        self.escala = 1.0;
        self.selected_element = None;
        self.previous_pos = None;
        self.diff = [0, 0];
        self.antes_arrasto = None;

        self.cena = QGraphicsScene(self);
        self.setScene(self.cena);
        self.setBackgroundBrush(Qt.white);
        self.setRenderHint(QPainter.Antialiasing, True);
        self.setRenderHint(QPainter.TextAntialiasing, True);
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded);
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded);
        # Zoom ancorado no ponteiro: o que esta sob o mouse continua sob o mouse.
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse);
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter);

    # ---------------------------------------------------------------- modelo

    def getElement(self, x, y):
        for element in reversed(self.mapa.elements):
            if element.x < x and element.x + element.w > x and element.y < y and element.y + element.h > y:
                return element;
        return None;

    def addEntity(self, ptype, x, y):
        return self.mapa.addEntity( ptype, x, y);

    def delEntity(self, element):
        return self.mapa.delEntity( element );

    def addExistEntity(self, entity, x, y):
        buffer = self.mapa.addEntity( entity["etype"], x, y, text=entity["text_label"], entity_id_=entity["id"], wikipedia=entity["wikipedia"] );
        if entity["etype"] == "person":
            buffer.doxxing = entity["data_extra"];
        buffer.entity = Entity.fromJson( entity );

    # ---------------------------------------------------------------- desenho

    def __recalcular__(self):
        # O recalc define w/h de cada caixa a partir da metrica da fonte, entao precisa de um
        # painter aberto -- um pixmap de 1x1 serve, porque so a metrica interessa.
        rascunho = QPixmap(1, 1);
        painter = QPainter();
        if not painter.begin(rascunho):
            return;
        try:
            painter.setFont(fonte_do_diagrama());
            for elemento in self.mapa.elements:
                elemento.recalc(painter);
        finally:
            painter.end();

    def redraw(self):
        # Refaz a cena a partir do modelo. Continua sendo o metodo que todo mundo chama depois
        # de mexer no mapa (MdiMap.redesenhar, os bots, o aplicador de transform).
        self.__recalcular__();
        self.cena.clear();
        self.itens = [];
        for elemento in self.mapa.elements:
            item = ItemElemento(elemento);
            # Vinculo por baixo, caixa por cima: mesma ordem dos dois lacos do redraw antigo.
            item.setZValue(0 if elemento.entity.etype == "link" else 1);
            self.cena.addItem(item);
            self.itens.append(item);
        self.__ajustar_cena__();
        self.viewport().update();

    def __ajustar_cena__(self):
        area = self.cena.itemsBoundingRect();
        if area.isEmpty():
            area = QRectF(0, 0, 800, 600);
        self.cena.setSceneRect(area.adjusted(-FOLGA_CENA, -FOLGA_CENA, FOLGA_CENA, FOLGA_CENA));

    def clear(self):
        self.cena.clear();
        self.itens = [];
        self.viewport().update();

    # ---------------------------------------------------------------- zoom

    def __aplicar_zoom__(self, escala):
        self.escala = max(ZOOM_MIN, min(ZOOM_MAX, escala));
        self.setTransform(QTransform().scale(self.escala, self.escala));

    def zoom_mais(self):
        self.__aplicar_zoom__(self.escala * ZOOM_PASSO);

    def zoom_menos(self):
        self.__aplicar_zoom__(self.escala / ZOOM_PASSO);

    def zoom_normal(self):
        self.__aplicar_zoom__(1.0);

    def ajustar_a_janela(self):
        area = self.cena.itemsBoundingRect();
        if area.isEmpty():
            return;
        self.fitInView(area.adjusted(-20, -20, 20, 20), Qt.KeepAspectRatio);
        self.escala = self.transform().m11();

    def wheelEvent(self, event):
        # Ctrl+roda da zoom; roda sozinha rola, que e o que o QGraphicsView ja faz.
        if event.modifiers() & Qt.ControlModifier:
            self.__aplicar_zoom__(self.escala * (ZOOM_PASSO if event.angleDelta().y() > 0 else 1 / ZOOM_PASSO));
            event.accept();
            return;
        super().wheelEvent(event);

    # ---------------------------------------------------------------- mouse

    def __posicao__(self, ponto):
        # View -> cena. Corta em zero: com rolagem e zoom da para clicar em coordenada
        # negativa, e o modelo (e o banco) sempre trabalhou com x/y positivos.
        cena = self.mapToScene(ponto);
        return max(0, int(cena.x())), max(0, int(cena.y()));

    def mousePressEvent(self, event: QMouseEvent):
        self.previous_pos = event.position().toPoint();
        x, y = self.__posicao__(self.previous_pos);
        self.selected_element = self.getElement(x, y);
        if self.selected_element != None:
            self.diff = [x - self.selected_element.x, y - self.selected_element.y];
            # Um arrasto inteiro = UM passo de desfazer, por isso o antes e tirado aqui e o
            # passo so e empilhado ao soltar (e nao a cada pixel do mouseMove).
            self.antes_arrasto = tirar_instantaneo(self.mapa);
            return;
        # Clique no vazio arrasta a tela (a maozinha do Qt), em vez de nao fazer nada.
        self.setDragMode(QGraphicsView.ScrollHandDrag);
        super().mousePressEvent(event);

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.selected_element == None:
            super().mouseMoveEvent(event);
            return;
        if self.mapa.getLocked():
            return;
        x, y = self.__posicao__(event.position().toPoint());
        # O "(y % 2) == 0" de antes era freio para o repinte do pixmap de 57 MB; aqui so o item
        # mexido e repintado, entao o arrasto pode ser continuo (antes andava aos saltos).
        self.selected_element.setX( x - self.diff[0] );
        self.selected_element.setY( y - self.diff[1] );
        for item in self.itens:
            # O vinculo precisa acompanhar a caixa que se moveu: a linha dele sai de uma ponta
            # a outra, entao a geometria dele muda junto.
            item.atualizar();

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.previous_pos = None;
        if self.selected_element != None:
            self.__ajustar_cena__();
            self.__empilhar_arrasto__();
        self.selected_element = None;
        super().mouseReleaseEvent(event);
        self.setDragMode(QGraphicsView.NoDrag);

    def __empilhar_arrasto__(self):
        if self.antes_arrasto == None:
            return;
        depois = tirar_instantaneo(self.mapa);
        if mudou(self.antes_arrasto, depois):
            self.mapa.desfazer.push(ComandoMapa(self.mapa, self.antes_arrasto, depois, "Mover caixa"));
        self.antes_arrasto = None;

    def mouseDoubleClickEvent(self, event):
        x, y = self.__posicao__(event.position().toPoint());
        buffer = self.getElement(x, y);
        if self.form != None:
            if buffer == None:
                self.form.map_double_click( self, x, y );
            else:
                self.form.entity_double_click( buffer );
            self.redraw();

    def contextMenuEvent(self, event):
        # Botao direito numa caixa: menu de transforms (estilo Maltego). So o mapa de vinculos
        # tem; o form decide o que mostrar conforme o tipo da caixa.
        x, y = self.__posicao__(event.pos());
        buffer = self.getElement(x, y);
        if buffer != None:
            if self.form != None and hasattr(self.form, "menu_transforms"):
                self.form.menu_transforms(buffer, event.globalPos());
            return;
        # No vazio, o menu do proprio canvas: e onde o zoom fica descobrivel por quem nao
        # adivinha o Ctrl+roda.
        menu = QMenu(self);
        menu.addAction("Zoom +", self.zoom_mais);
        menu.addAction("Zoom −", self.zoom_menos);
        menu.addAction("Zoom 100%", self.zoom_normal);
        menu.addAction("Ajustar à janela", self.ajustar_a_janela);
        menu.exec(event.globalPos());
