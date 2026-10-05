# Tema do CML: as cores moram AQUI, num lugar so, e valem para o aplicativo inteiro.
#
# Mesmo principio do tema do ghop: por PALETA, nao por folha de estilo gigante. A diferenca
# importa -- o que o Qt desenha sozinho (campo, lista, menu, barra) acompanha o tema sem
# ninguem escrever regra, e folha de estilo fica so para o que a paleta nao alcanca.
#
# O que NAO e tocado e o CANVAS DO MAPA. Ele continua fundo branco com traco preto, e isso nao
# e esquecimento: o desenho e exportado em PDF, PNG e SVG para imprimir e para anexar em
# processo, e mapa com fundo escuro vira mancha de tinta no papel. Quem le na tela tem zoom; o
# que sai do app tem de sair como documento.
#
# A BARRA DE TITULO DA SUBJANELA DO MDI fica com o azul vivo do realce, e nao com um
# escurecido. Nao e descuido: a paleta sozinha nao a alcanca (com folha de estilo ativa quem
# desenha e o QStyleSheetStyle, que a ignora), e a regra 'QMdiSubWindow::title' que funcionaria
# faz o Qt desenhar a decoracao inteira em modo folha de estilo -- e com isso somem os botoes de
# minimizar, maximizar e FECHAR. Barra discreta nao paga o botao de fechar. (Mesma conclusao a
# que o tema do ghop chegou; esta anotado aqui para ninguem tentar de novo.)
#
# Variavel de ambiente:
#   CML_TEMA=sistema   usa o tema do desktop, sem aplicar nada disto

import math, os;

from PySide6.QtCore import QPointF, Qt;
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter, QPalette, QPen,
                           QPixmap);

COR_FUNDO     = "#11151a";
COR_CAMPO     = "#181e25";
COR_ALTERNADA = "#1f262e";
COR_TEXTO     = "#e6eaee";
COR_APAGADO   = "#8d9aa7";
COR_REALCE    = "#3b82f6";   # azul: o vermelho ja tem significado no desenho do mapa
COR_BORDA     = "#2b343e";

# O emblema e a propria coisa que o programa faz: um punhado de entidades e os vinculos entre
# elas. Desenhado em codigo, nao em arquivo -- assim nasce na resolucao que a tela pedir, segue
# a cor do tema e nao ha binario de enfeite para alguem trocar por engano.
#
# As posicoes sao FIXAS (nao sorteadas): emblema que muda a cada abertura parece defeito.
NOS = [(0.50, 0.17), (0.20, 0.36), (0.80, 0.34), (0.34, 0.63), (0.66, 0.62),
       (0.12, 0.80), (0.50, 0.86), (0.88, 0.78)];
ARESTAS = [(0, 1), (0, 2), (1, 3), (2, 4), (3, 4), (3, 5), (4, 6), (4, 7), (6, 7), (1, 6)];
PRINCIPAIS = (0, 4);   # dois nos em destaque: o olho tem onde pousar


def emblema(largura, altura):
    """Pixmap com a constelacao de entidades e vinculos. Sem arquivo externo."""
    pixmap = QPixmap(largura, altura);
    pixmap.fill(Qt.transparent);
    painter = QPainter();
    if not painter.begin(pixmap):
        return pixmap;
    try:
        painter.setRenderHint(QPainter.Antialiasing, True);
        pontos = [QPointF(x * largura, y * altura) for x, y in NOS];
        realce = QColor(COR_REALCE);

        for a, b in ARESTAS:
            # A linha escurece do no de origem para o de destino: da direcao sem precisar de
            # seta, que neste tamanho viraria borrao.
            gradiente = QLinearGradient(pontos[a], pontos[b]);
            gradiente.setColorAt(0.0, QColor(realce.red(), realce.green(), realce.blue(), 170));
            gradiente.setColorAt(1.0, QColor(realce.red(), realce.green(), realce.blue(), 55));
            caneta = QPen(QBrush(gradiente), 1.6);
            painter.setPen(caneta);
            painter.drawLine(pontos[a], pontos[b]);

        for i in range(len(pontos)):
            principal = i in PRINCIPAIS;
            raio = 9.0 if principal else 5.5;
            if principal:
                # Halo: so nos dois principais, para o destaque nao virar ruido.
                painter.setPen(Qt.NoPen);
                painter.setBrush(QColor(realce.red(), realce.green(), realce.blue(), 45));
                painter.drawEllipse(pontos[i], raio * 2.2, raio * 2.2);
            painter.setPen(QPen(realce, 1.6));
            painter.setBrush(QColor(COR_FUNDO) if not principal else realce);
            painter.drawEllipse(pontos[i], raio, raio);
    finally:
        painter.end();
    return pixmap;


def __paleta__():
    paleta = QPalette();
    fundo, campo = QColor(COR_FUNDO), QColor(COR_CAMPO);
    texto, apagado, realce = QColor(COR_TEXTO), QColor(COR_APAGADO), QColor(COR_REALCE);
    paleta.setColor(QPalette.Window, fundo);
    paleta.setColor(QPalette.WindowText, texto);
    paleta.setColor(QPalette.Base, campo);
    paleta.setColor(QPalette.AlternateBase, QColor(COR_ALTERNADA));
    paleta.setColor(QPalette.Text, texto);
    paleta.setColor(QPalette.Button, QColor(COR_ALTERNADA));
    paleta.setColor(QPalette.ButtonText, texto);
    paleta.setColor(QPalette.BrightText, QColor("#ffffff"));
    paleta.setColor(QPalette.ToolTipBase, campo);
    paleta.setColor(QPalette.ToolTipText, texto);
    paleta.setColor(QPalette.Link, realce);
    paleta.setColor(QPalette.Highlight, realce);
    paleta.setColor(QPalette.HighlightedText, QColor("#f7fafc"));
    paleta.setColor(QPalette.Mid, apagado);
    paleta.setColor(QPalette.Dark, QColor(COR_BORDA));
    paleta.setColor(QPalette.Shadow, QColor("#000000"));
    # Desabilitado tem de LER como desabilitado sem sumir no fundo.
    for papel in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        paleta.setColor(QPalette.Disabled, papel, QColor("#5d6872"));
    return paleta;


# Folha de estilo so para o que a paleta nao alcanca.
FOLHA = """
QToolBar { border: 0px; padding: 4px; spacing: 2px; }
QToolBar::separator { background: %(borda)s; width: 1px; margin: 4px 6px; }
QLineEdit, QComboBox, QTextEdit, QPlainTextEdit {
    border: 1px solid %(borda)s; border-radius: 4px; padding: 5px 7px;
    selection-background-color: %(realce)s;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid %(realce)s; }
QPushButton {
    border: 1px solid %(borda)s; border-radius: 4px; padding: 6px 14px;
}
QPushButton:hover  { border: 1px solid %(realce)s; }
QPushButton:default, QPushButton[destaque="sim"] {
    background: %(realce)s; border: 1px solid %(realce)s; color: #ffffff; font-weight: bold;
}
QHeaderView::section {
    background: %(alternada)s; border: 0px; border-right: 1px solid %(borda)s;
    border-bottom: 1px solid %(borda)s; padding: 5px;
}
QTabBar::tab { background: %(alternada)s; border: 1px solid %(borda)s; padding: 6px 12px; }
QTabBar::tab:selected { background: %(campo)s; border-bottom-color: %(realce)s; }
QStatusBar { border-top: 1px solid %(borda)s; }
""" % {"borda": COR_BORDA, "realce": COR_REALCE, "alternada": COR_ALTERNADA, "campo": COR_CAMPO};


def aplicar(app):
    """Aplica o tema. Devolve False se o usuario pediu o tema do sistema."""
    if (os.environ.get("CML_TEMA") or "").strip().lower() == "sistema":
        return False;
    app.setStyle("Fusion");   # o Fusion respeita a paleta em qualquer desktop
    app.setPalette(__paleta__());
    app.setStyleSheet(FOLHA);
    return True;
