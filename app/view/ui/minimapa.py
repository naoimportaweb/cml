# Minimapa do mapa de vinculos (SPEC.md §3.3): o mapa inteiro em miniatura, com o retangulo do
# que esta visivel, e clique para ir ate la.
#
# Nao redesenha nada por conta propria: e um segundo QGraphicsView sobre A MESMA QGraphicsScene
# do canvas. Duas vistas da mesma cena e o que o QGraphicsView da de graca -- clonar os itens
# daria duas verdades sobre o desenho, e cada mudanca teria de ser aplicada nos dois.

from PySide6.QtWidgets import QGraphicsView;
from PySide6.QtCore import Qt, QRectF;
from PySide6.QtGui import QBrush, QColor, QPainter, QPen;

LADO = 190;             # canto do canvas que o minimapa ocupa
COR_FORA = QColor(0, 0, 0, 40);     # escurece o que esta fora da janela
COR_BORDA = QColor(40, 90, 200);


class Minimapa(QGraphicsView):
    def __init__(self, canvas):
        super().__init__(canvas);
        self.canvas = canvas;
        self.setScene(canvas.cena);
        self.setFixedSize(LADO, int(LADO * 0.62));
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff);
        self.setRenderHint(QPainter.Antialiasing, True);
        self.setBackgroundBrush(Qt.white);
        self.setFrameShape(QGraphicsView.Box);
        # O minimapa nao interage com os itens: clicar nele e "me leve ate ali", nunca
        # "selecione" ou "arraste esta caixa".
        self.setInteractive(False);
        self.setDragMode(QGraphicsView.NoDrag);
        self.setToolTip("Minimapa — clique para ir até o ponto");

    def acompanhar(self):
        """Reenquadra a miniatura no conteudo. Chamado pelo canvas a cada redraw."""
        area = self.scene().itemsBoundingRect() if self.scene() != None else QRectF();
        if area.isEmpty():
            return;
        self.fitInView(area.adjusted(-20, -20, 20, 20), Qt.KeepAspectRatio);
        self.viewport().update();

    def drawForeground(self, painter, retangulo):
        # O retangulo do que esta visivel no canvas, desenhado POR CIMA da cena.
        super().drawForeground(painter, retangulo);
        visivel = self.canvas.mapToScene(self.canvas.viewport().rect()).boundingRect();
        if visivel.isEmpty():
            return;
        painter.save();
        try:
            cena = self.scene().sceneRect();
            # Escurece o que ficou de fora, em vez de so contornar o que esta dentro: num mapa
            # grande o contorno some, a sombra nao.
            for fora in (QRectF(cena.left(), cena.top(), cena.width(), visivel.top() - cena.top()),
                         QRectF(cena.left(), visivel.bottom(), cena.width(), cena.bottom() - visivel.bottom()),
                         QRectF(cena.left(), visivel.top(), visivel.left() - cena.left(), visivel.height()),
                         QRectF(visivel.right(), visivel.top(), cena.right() - visivel.right(), visivel.height())):
                if fora.width() > 0 and fora.height() > 0:
                    painter.fillRect(fora, QBrush(COR_FORA));
            caneta = QPen(COR_BORDA);
            # Largura 0 = linha de 1 pixel na TELA, sem escalar junto com a miniatura (que esta
            # reduzida dezenas de vezes; com largura 1 a borda sumiria).
            caneta.setWidth(0);
            painter.setPen(caneta);
            painter.drawRect(visivel);
        finally:
            painter.restore();

    def mousePressEvent(self, event):
        self.__ir_para__(event);

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.__ir_para__(event);

    def __ir_para__(self, event):
        ponto = self.mapToScene(event.position().toPoint());
        self.canvas.centerOn(ponto);
        self.viewport().update();
