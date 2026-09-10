# CADA MAPA POSSUI UMA FORMA DE DESENHAR, CLICAR, SELECIONAR, ISSO FICA AQUI

from PySide6.QtWidgets import (QFileDialog, QMenu, QToolTip, QWidget)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import (QCursor, QMouseEvent, QPaintEvent, QPainter, QPixmap)

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( CURRENTDIR ) ) );

from view.dialog_timeline_event import DialogTimelineEvent;


class MapaTimelineEngine(QWidget):
    """Casca da timeline: mouse, pixmap e menu. O desenho e o layout ficam na Timeline —
    mesmo arranjo do organograma, onde o engine tambem so delega o draw ao modelo.

    Diferenca para os outros dois engines: nao ha arrastar elemento. A posicao de cada evento
    e a data dele, entao mover com o mouse nao faria sentido; o que se ajusta e o ZOOM, que
    estica ou comprime o eixo."""

    ZOOM_MIN = 0.25;
    ZOOM_MAX = 8.0;

    def __init__(self, parent=None, mapa=None, form=None):
        super().__init__(parent);
        self.form = form;
        self.parent = parent;
        self.mapa = mapa;                  # Timeline
        self.pixmap = None;
        self.previous_pos = QPoint(0, 0);
        self.setMouseTracking(True);       # o tooltip precisa do movimento sem botao apertado
        self.setContextMenuPolicy(Qt.CustomContextMenu);
        self.customContextMenuRequested.connect(self.menu_contexto);
        self.__ajustar_tamanho__();

    def __ajustar_tamanho__(self):
        largura, altura = self.mapa.tamanho();
        self.setFixedSize( largura, altura );
        self.pixmap = QPixmap( self.size() );
        self.pixmap.fill( Qt.white );

    def redraw(self):
        # Zoom e eventos novos mudam o TAMANHO do desenho, entao o pixmap e refeito a cada
        # redraw (nao da para so repintar por cima, como no mapa de relacionamento).
        self.__ajustar_tamanho__();
        painter = QPainter();
        painter.begin( self.pixmap );
        try:
            painter.setRenderHint(QPainter.Antialiasing, True);
            self.mapa.draw( painter );
        finally:
            painter.end();
        self.update();

    def paintEvent(self, event: QPaintEvent):
        with QPainter(self) as painter:
            painter.drawPixmap(0, 0, self.pixmap);

    # ------------------------------------------------------------------ mouse
    def mousePressEvent(self, event: QMouseEvent):
        QWidget.mousePressEvent(self, event);
        self.previous_pos = event.position().toPoint();
        self.mapa.selecionado = self.mapa.findByXY( self.previous_pos.x(), self.previous_pos.y() );
        self.redraw();

    def mouseMoveEvent(self, event: QMouseEvent):
        QWidget.mouseMoveEvent(self, event);
        ponto = event.position().toPoint();
        evento = self.mapa.findByXY( ponto.x(), ponto.y() );
        if evento == None:
            QToolTip.hideText();
            return;
        # O rotulo desenhado e uma linha so; o resto (subtitulo, duracao, origem, descricao)
        # aparece aqui em vez de poluir o canvas.
        QToolTip.showText( event.globalPosition().toPoint(), evento.tooltip(), self );

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        ponto = event.position().toPoint();
        evento = self.mapa.findByXY( ponto.x(), ponto.y() );
        if evento != None and evento.editavel():
            self.__editar__( evento );

    def wheelEvent(self, event):
        # Ctrl+roda = zoom, como em qualquer visualizador. Sem Ctrl, deixa o scroll da area
        # rolar normalmente.
        if event.modifiers() & Qt.ControlModifier:
            self.__zoom__( 1.25 if event.angleDelta().y() > 0 else 0.8 );
            event.accept();
            return;
        event.ignore();

    # ------------------------------------------------------------------ menu
    def menu_contexto(self, ponto):
        self.previous_pos = ponto;
        evento = self.mapa.findByXY( ponto.x(), ponto.y() );
        menu = QMenu();

        item_novo = menu.addAction("Novo evento…");
        item_novo.triggered.connect( self.item_novo_click );

        if evento != None and evento.editavel():
            item_editar = menu.addAction("Editar evento…");
            item_editar.triggered.connect( self.item_editar_click );
            item_remover = menu.addAction("Remover evento");
            item_remover.triggered.connect( self.item_remover_click );
        elif evento != None:
            # Projecao: a data mora no vinculo/classificacao/referencia, e e la que se edita.
            item_origem = menu.addAction("Vem de: " + evento.tooltip().split("\n")[0]);
            item_origem.setEnabled(False);

        menu.addSeparator();
        menu.addAction("Aumentar (Ctrl+roda)").triggered.connect( lambda: self.__zoom__(1.25) );
        menu.addAction("Diminuir").triggered.connect( lambda: self.__zoom__(0.8) );
        menu.addAction("Zoom normal").triggered.connect( self.item_zoom_normal_click );
        menu.addSeparator();
        menu.addAction("Atualizar do servidor").triggered.connect( self.item_atualizar_click );
        menu.addAction("Exportar PNG…").triggered.connect( self.item_exportar_click );
        menu.exec_( QCursor.pos() );

    def item_novo_click(self):
        f = DialogTimelineEvent( self.parent, self.mapa.id );
        f.exec();
        if f.gravou:
            # Ja gravou no servidor; entra na lista local para nao precisar recarregar tudo.
            self.mapa.add_marcado( f.evento );
            self.redraw();

    def item_editar_click(self):
        evento = self.mapa.findByXY( self.previous_pos.x(), self.previous_pos.y() );
        if evento != None and evento.editavel():
            self.__editar__( evento );

    def __editar__(self, evento):
        f = DialogTimelineEvent( self.parent, self.mapa.id, evento=evento.obj );
        f.exec();
        if f.removeu:
            self.mapa.del_marcado( evento.obj );
            self.redraw();
        elif f.gravou:
            self.mapa.coletar();
            self.redraw();

    def item_remover_click(self):
        evento = self.mapa.findByXY( self.previous_pos.x(), self.previous_pos.y() );
        if evento == None or not evento.editavel():
            return;
        if evento.obj.delete():
            self.mapa.del_marcado( evento.obj );
            self.redraw();

    def item_zoom_normal_click(self):
        self.mapa.zoom = 1.0;
        self.redraw();

    def item_atualizar_click(self):
        self.mapa.recarregar();
        self.redraw();

    def item_exportar_click(self):
        nome = (self.mapa.getName() or "timeline").strip().replace(" ", "_") + ".png";
        caminho, _ = QFileDialog.getSaveFileName(self, "Exportar timeline", nome, "PNG (*.png)");
        if caminho == None or caminho.strip() == "":
            return;
        if not caminho.lower().endswith(".png"):
            caminho = caminho + ".png";
        self.pixmap.save( caminho, "PNG" );

    def __zoom__(self, fator):
        novo = self.mapa.zoom * fator;
        if novo < self.ZOOM_MIN:
            novo = self.ZOOM_MIN;
        if novo > self.ZOOM_MAX:
            novo = self.ZOOM_MAX;
        self.mapa.zoom = novo;
        self.redraw();

    # ------------------------------------------------------------------ contrato do MdiMap
    def save(self, filename: str):
        return;

    def load(self, filename: str):
        return;

    def clear(self):
        return;
