# CADA MAPA POSSUI UMA FORMA DE DESENHAR, CLICAR, SELECIONAR, ISSO FICA AQUI
#
# Canvas do organograma. Era o ultimo preso ao QPixmap de 5000x3000 sem rolagem nem zoom, com o
# duplo clique DESLIGADO (o metodo era so um "return") e o arrasto movendo o x de um item solto
# -- que o proximo redraw jogava fora, porque o layout recalculava a posicao do zero.
#
# Agora e QGraphicsView, como o do mapa de vinculos: rolagem, zoom, arrastar a tela. E a posicao
# NAO se arrasta de proposito: num organograma o lugar da caixa e consequencia da hierarquia, e
# nao escolha do analista. Quem muda o desenho muda a arvore (novo filho, remover, reordenar).

from PySide6.QtWidgets import (QGraphicsItem, QGraphicsScene, QGraphicsView, QMenu, QMessageBox);
from PySide6.QtCore import Qt, QRectF;
from PySide6.QtGui import QPainter, QPainterPath, QPixmap, QTransform;

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( CURRENTDIR ) ) );

from view.dialog_organization_item import DialogOrganizationItem;
from classlib.exportar_diagrama import fonte_do_diagrama;

ZOOM_MIN = 0.15;
ZOOM_MAX = 4.0;
ZOOM_PASSO = 1.15;
FOLGA_CENA = 60;


class ItemOrganograma(QGraphicsItem):
    """Um item por caixa do organograma. Como no mapa de vinculos, nao guarda geometria propria:
    le x/y/w/h do modelo e pinta com o draw() dele.

    So a RAIZ desenha, e desenha a arvore inteira: o draw() do modelo e recursivo e ja pinta os
    conectores dos filhos. Um item por caixa existe para o CLIQUE caber na caixa certa -- se a
    area clicavel fosse a da raiz, ela engoliria o organograma inteiro."""

    def __init__(self, item, raiz=False):
        super().__init__();
        self.item = item;
        self.raiz = raiz;
        self.setZValue(1 if raiz else 0);

    def __retangulo__(self):
        return QRectF(self.item.x or 0, self.item.y or 0, self.item.w or 1, self.item.h or 1);

    def boundingRect(self):
        if not self.raiz:
            return self.__retangulo__().adjusted(-4, -4, 4, 4);
        # A raiz pinta tudo, entao a area dela cobre a arvore inteira.
        itens = [i for i in self.item.todos() if i.w != None and i.y != None];
        retangulo = self.__retangulo__();
        for outro in itens:
            retangulo = retangulo.united(QRectF(outro.x, outro.y, outro.w, outro.h));
        return retangulo.adjusted(-30, -30, 30, 30);

    def shape(self):
        caminho = QPainterPath();
        caminho.addRect(self.__retangulo__());
        return caminho;

    def paint(self, painter, option, widget=None):
        if not self.raiz:
            return;   # quem pinta e a raiz, uma vez so
        painter.setFont(fonte_do_diagrama());
        self.item.draw(painter);


class MapaOrganizationChartEngine(QGraphicsView):
    def __init__(self, parent=None, mapa=None, form=None, max_width=5000, max_height=3000):
        super().__init__(parent);
        self.form = form;
        self.parent = parent;
        self.mapa = mapa;
        self.itens = [];
        self.escala = 1.0;
        self.pan_inicio = None;
        self.previous_pos = None;
        self.selected_element = None;

        self.cena = QGraphicsScene(self);
        self.setScene(self.cena);
        self.setBackgroundBrush(Qt.white);
        self.setRenderHint(QPainter.Antialiasing, True);
        self.setRenderHint(QPainter.TextAntialiasing, True);
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse);
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter);
        self.setDragMode(QGraphicsView.NoDrag);

    # ---------------------------------------------------------------- modelo

    def getElement(self, x, y):
        return self.mapa.findByXY( x, y);

    # ---------------------------------------------------------------- desenho

    def redraw(self):
        # O layout roda dentro do draw() do modelo, e ele precisa de um painter para medir a
        # fonte: um pixmap de 1x1 serve, porque so a metrica interessa.
        rascunho = QPixmap(1, 1);
        painter = QPainter();
        if painter.begin(rascunho):
            try:
                painter.setFont(fonte_do_diagrama());
                if self.mapa.root != None:
                    self.mapa.root.recalc(painter);
            finally:
                painter.end();
        self.cena.clear();
        self.itens = [];
        if self.mapa.root != None:
            for item in self.mapa.root.todos():
                grafico = ItemOrganograma(item, raiz=(item is self.mapa.root));
                self.cena.addItem(grafico);
                self.itens.append(grafico);
        self.__ajustar_cena__();
        self.viewport().update();

    def __ajustar_cena__(self):
        area = self.cena.itemsBoundingRect();
        if area.isEmpty():
            area = QRectF(0, 0, 600, 400);
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
        if event.modifiers() & Qt.ControlModifier:
            self.__aplicar_zoom__(self.escala * (ZOOM_PASSO if event.angleDelta().y() > 0 else 1 / ZOOM_PASSO));
            event.accept();
            return;
        super().wheelEvent(event);

    # ---------------------------------------------------------------- mouse

    def __posicao__(self, ponto):
        cena = self.mapToScene(ponto);
        return int(cena.x()), int(cena.y());

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.pan_inicio = event.position().toPoint();
            self.setCursor(Qt.ClosedHandCursor);
            return;
        self.previous_pos = event.position().toPoint();
        x, y = self.__posicao__(self.previous_pos);
        self.selected_element = self.getElement(x, y);
        super().mousePressEvent(event);

    def mouseMoveEvent(self, event):
        if self.pan_inicio != None:
            ponto = event.position().toPoint();
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - (ponto.x() - self.pan_inicio.x()));
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - (ponto.y() - self.pan_inicio.y()));
            self.pan_inicio = ponto;
            return;
        super().mouseMoveEvent(event);

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self.pan_inicio != None:
            self.pan_inicio = None;
            self.unsetCursor();
            return;
        super().mouseReleaseEvent(event);

    def mouseDoubleClickEvent(self, event):
        # Era "return": abrir o item com duplo clique simplesmente nao existia, e so o menu do
        # botao direito chegava ao dialogo.
        x, y = self.__posicao__(event.position().toPoint());
        item = self.getElement(x, y);
        if item == None:
            return;
        self.__abrir__(item);

    def contextMenuEvent(self, event):
        x, y = self.__posicao__(event.pos());
        item = self.getElement(x, y);
        menu = QMenu(self);
        if item != None:
            menu.addAction("Abrir / configurar", lambda: self.__abrir__(item));
            menu.addAction("Novo item abaixo", lambda: self.__novo_filho__(item));
            menu.addSeparator();
            menu.addAction("Remover", lambda: self.__remover__(item));
        elif self.mapa.root == None:
            menu.addAction("Novo item (raiz)", self.__nova_raiz__);
        else:
            menu.addAction("Zoom +", self.zoom_mais);
            menu.addAction("Zoom −", self.zoom_menos);
            menu.addAction("Zoom 100%", self.zoom_normal);
            menu.addAction("Ajustar à janela", self.ajustar_a_janela);
        menu.exec(event.globalPos());

    # ---------------------------------------------------------------- acoes

    def __janela_pai__(self):
        return self.parent if self.parent != None else self;

    def __abrir__(self, item):
        DialogOrganizationItem( self.__janela_pai__(), item, self.mapa ).exec();
        self.redraw();

    def __nova_raiz__(self):
        item = self.mapa.addEntityItem("Novo item");
        if item == False or item == None:
            return;
        self.__abrir__(item);

    def __novo_filho__(self, pai):
        item = self.mapa.addEntityItem("Novo item", organization_chart_item_parent_id=pai.id);
        if item == False or item == None:
            return;
        self.__abrir__(item);

    def __remover__(self, item):
        quantos = len(item.todos());
        pergunta = "Remover \"%s\"?" % str(item.text_label or "");
        if quantos > 1:
            pergunta = pergunta + "\n\nOs %d itens abaixo dele sobem um nível — não são apagados." % (quantos - 1);
        if QMessageBox.question(self, "Remover", pergunta,
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return;
        try:
            self.mapa.removerItem(item);
        except Exception as erro:
            QMessageBox.warning(self, "Remover", str(erro));
            return;
        self.redraw();

    def save(self, filename: str):
        self.mapa.save();
