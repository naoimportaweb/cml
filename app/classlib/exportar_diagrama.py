# Exporta qualquer um dos tres diagramas (mapa de vinculos, organograma, timeline) para
# arquivo: PDF vetorial, PNG em alta e SVG.
#
# Nao depende do canvas e nao precisa da migracao para QGraphicsView (SPEC.md §3.1): o modelo
# desenha com draw(painter), e QPdfWriter, QSvgGenerator e QImage sao todos QPainter. Era o
# unico jeito de a entrega sair do app ainda nesta rodada -- com o report morto (SPEC.md §8),
# o diagrama exportado E a entrega do trabalho.
#
# LEI DO PROJETO (CLAUDE.md, SPEC.md §3.2): o SVG daqui sai SO para arquivo local do analista.
# Nunca aceitar SVG de fora, nunca anexar SVG como Document, nunca servir SVG inline -- o
# perigo e SVG de procedencia desconhecida, nao o formato.

import os, sys, inspect, re, datetime;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

from PySide6.QtCore import Qt, QRect, QSize, QMarginsF;
from PySide6.QtGui import (QPainter, QImage, QPixmap, QFont, QPen, QColor, QPdfWriter,
                           QPageSize, QPageLayout);
from PySide6.QtSvg import QSvgGenerator;

from classlib.configuration import Configuration;

MARGEM = 20;            # respiro em volta do conteudo, em px logicos
ALTURA_RODAPE = 40;     # faixa do rodape (nome, data, legenda de cor)
RESOLUCAO = 96;         # DPI do PDF: iguala a metrica de fonte a da tela, para o desenho sair
                        # igual ao que o analista ve. Resolucao alta mudaria o boundingRect do
                        # recalc e as caixas nao baterian mais com as posicoes gravadas (x/y).
PAPEIS = {"A4": QPageSize.A4, "A3": QPageSize.A3, "A2": QPageSize.A2};
FORMATOS = ("pdf", "png", "svg");


class ErroExportacao(Exception):
    pass;


def nome_de_arquivo(mapa):
    # Nome sugerido no dialogo de salvar: o nome do diagrama, sem o que atrapalha em path.
    bruto = (mapa.getName() or "diagrama").strip();
    limpo = re.sub(r"[^\w\s().-]", "", bruto, flags=re.UNICODE).strip();
    limpo = re.sub(r"\s+", "_", limpo);
    return limpo or "diagrama";


def __fonte__():
    cfg = Configuration.instancia();
    # O nome do atributo tem typo desde sempre (relationshihp_); mexer nele e outra tarefa.
    return QFont(cfg.relationshihp_font_family, cfg.relationshihp_font_size);


def __tipo__(mapa):
    return mapa.__class__.__name__;


def __itens_organograma__(item, saida):
    if item == None:
        return saida;
    saida.append(item);
    for filho in getattr(item, "elements", []):
        __itens_organograma__(filho, saida);
    return saida;


def __medir__(mapa, painter):
    # Retangulo do CONTEUDO (sem margem). O recalc precisa acontecer antes de medir, porque e
    # ele quem define w/h de cada caixa a partir da metrica da fonte.
    tipo = __tipo__(mapa);
    painter.setFont(__fonte__());

    if tipo == "Timeline":
        largura, altura = mapa.tamanho();
        return QRect(0, 0, max(1, int(largura)), max(1, int(altura)));

    if tipo == "OrganizationChart":
        if getattr(mapa, "root", None) == None:
            raise ErroExportacao("O organograma está vazio.");
        mapa.root.recalc(painter);
        itens = __itens_organograma__(mapa.root, []);
        caixas = [];
        for item in itens:
            if item.w == None or item.h == None or item.y == None:
                continue;
            # A altura efetiva cresce com as linhas de texto extra, como no draw do item.
            altura = item.h + (15 * len(getattr(item, "buffer_lines_text", [])));
            caixas.append((item.x, item.y, item.w, altura));
        return __envolver__(caixas);

    # MapRelationship
    elementos = getattr(mapa, "elements", None);
    if not elementos:
        raise ErroExportacao("O mapa não tem nenhuma caixa para exportar.");
    for elemento in elementos:
        elemento.recalc(painter);
    return __envolver__([(e.x, e.y, e.w, e.h) for e in elementos]);


def __envolver__(caixas):
    caixas = [c for c in caixas if None not in c];
    if len(caixas) == 0:
        raise ErroExportacao("Não há nada desenhado para exportar.");
    x1 = min(c[0] for c in caixas);
    y1 = min(c[1] for c in caixas);
    x2 = max(c[0] + c[2] for c in caixas);
    y2 = max(c[1] + c[3] for c in caixas);
    return QRect(int(x1), int(y1), max(1, int(x2 - x1)), max(1, int(y2 - y1)));


def __desenhar__(mapa, painter):
    # Mesma ordem do redraw de cada engine -- se divergir, o arquivo sai diferente da tela.
    tipo = __tipo__(mapa);
    painter.setFont(__fonte__());
    if tipo in ("Timeline", "OrganizationChart"):
        mapa.draw(painter);
        return;
    for elemento in mapa.elements:
        elemento.recalc(painter);
    for elemento in mapa.elements:
        if elemento.entity.etype == "link":
            elemento.draw(painter);
    for elemento in mapa.elements:
        if elemento.entity.etype in ("person", "organization", "other"):
            elemento.draw(painter);


def __rodape__(mapa, painter, conteudo):
    # Desenhado no mesmo sistema de coordenadas do conteudo, logo abaixo dele: um transform so
    # serve para os dois, e o rodape acompanha a escala do "caber na pagina".
    y = conteudo.bottom() + 14;
    painter.save();
    try:
        fonte = QFont(__fonte__());
        fonte.setPointSize(max(7, fonte.pointSize() - 1));
        painter.setPen(QPen(QColor(90, 90, 90)));
        painter.setFont(fonte);
        quando = datetime.datetime.now().strftime("%Y-%m-%d %H:%M");
        titulo = (mapa.getName() or "").strip();
        painter.drawText(conteudo.left(), y, "%s  ·  exportado em %s  ·  CML" % (titulo, quando));
        if __tipo__(mapa) == "MapRelationship":
            # A segunda entrada entra DEPOIS da primeira, medida na fonte: com deslocamento
            # fixo as duas se escreviam uma por cima da outra em fonte larga (Courier).
            primeira = "— vínculo PARA a entidade";
            painter.setPen(QPen(Qt.red));
            painter.drawText(conteudo.left(), y + 14, primeira);
            painter.setPen(QPen(Qt.blue));
            painter.drawText(conteudo.left() + painter.fontMetrics().horizontalAdvance(primeira) + 20,
                             y + 14, "— vínculo DE a entidade");
    finally:
        painter.restore();


def __area__(mapa, legenda):
    # Mede com um painter de rascunho (metrica de fonte igual a da tela) e devolve a area total,
    # ja com margem e rodape.
    rascunho = QPixmap(1, 1);
    painter = QPainter();
    if not painter.begin(rascunho):
        raise ErroExportacao("Não foi possível preparar o desenho para medir.");
    try:
        conteudo = __medir__(mapa, painter);
        # O rodape pode ser mais largo que o desenho (mapa de duas caixas, nome comprido): sem
        # medir, ele saia cortado na borda direita.
        largura_rodape = __largura_rodape__(mapa, painter) if legenda else 0;
    finally:
        painter.end();
    largura = max(conteudo.width() + (MARGEM * 2), largura_rodape + (MARGEM * 2));
    total = QRect(conteudo.left() - MARGEM, conteudo.top() - MARGEM, largura,
                  conteudo.height() + (MARGEM * 2) + (ALTURA_RODAPE if legenda else 0));
    return conteudo, total;


def __largura_rodape__(mapa, painter):
    fonte = QFont(__fonte__());
    fonte.setPointSize(max(7, fonte.pointSize() - 1));
    painter.setFont(fonte);
    metrica = painter.fontMetrics();
    quando = datetime.datetime.now().strftime("%Y-%m-%d %H:%M");
    linhas = ["%s  ·  exportado em %s  ·  CML" % ((mapa.getName() or "").strip(), quando)];
    if __tipo__(mapa) == "MapRelationship":
        primeira = "— vínculo PARA a entidade";
        linhas.append(primeira + "    " + "— vínculo DE a entidade");
    return max(metrica.horizontalAdvance(linha) for linha in linhas);


def __pintar__(mapa, painter, conteudo, total, legenda, fundo_branco):
    painter.setRenderHint(QPainter.Antialiasing, True);
    painter.setRenderHint(QPainter.TextAntialiasing, True);
    if fundo_branco:
        painter.fillRect(total, Qt.white);
    painter.translate(-total.left(), -total.top());
    __desenhar__(mapa, painter);
    if legenda:
        __rodape__(mapa, painter, conteudo);


def para_png(mapa, caminho, escala=2, legenda=True):
    conteudo, total = __area__(mapa, legenda);
    imagem = QImage(total.width() * escala, total.height() * escala, QImage.Format_RGB32);
    imagem.fill(Qt.white);
    painter = QPainter();
    if not painter.begin(imagem):
        raise ErroExportacao("Não foi possível abrir a imagem para desenhar.");
    try:
        painter.scale(escala, escala);
        __pintar__(mapa, painter, conteudo, total, legenda, False);
    finally:
        painter.end();
    if not imagem.save(caminho, "PNG"):
        raise ErroExportacao("O PNG não pôde ser gravado em %s." % caminho);


def para_svg(mapa, caminho, legenda=True):
    conteudo, total = __area__(mapa, legenda);
    gerador = QSvgGenerator();
    gerador.setFileName(caminho);
    gerador.setSize(QSize(total.width(), total.height()));
    gerador.setViewBox(QRect(0, 0, total.width(), total.height()));
    gerador.setTitle(mapa.getName() or "Diagrama");
    gerador.setDescription("Exportado pelo CML");
    painter = QPainter();
    if not painter.begin(gerador):
        raise ErroExportacao("Não foi possível abrir o SVG para desenhar.");
    try:
        # SVG nasce transparente: o fundo branco e desenhado, nao herdado.
        __pintar__(mapa, painter, conteudo, total, legenda, True);
    finally:
        painter.end();


def para_pdf(mapa, caminho, papel="A4", legenda=True):
    if papel not in PAPEIS:
        raise ErroExportacao("Papel desconhecido: %s" % papel);
    conteudo, total = __area__(mapa, legenda);
    escritor = QPdfWriter(caminho);
    escritor.setPageSize(QPageSize(PAPEIS[papel]));
    # Deitado quando o desenho e mais largo que alto -- diagrama quase sempre e.
    escritor.setPageOrientation(QPageLayout.Landscape if total.width() >= total.height()
                                else QPageLayout.Portrait);
    escritor.setResolution(RESOLUCAO);
    escritor.setPageMargins(QMarginsF(8, 8, 8, 8), QPageLayout.Millimeter);
    escritor.setTitle(mapa.getName() or "Diagrama");
    pagina = escritor.pageLayout().paintRectPixels(RESOLUCAO);
    painter = QPainter();
    if not painter.begin(escritor):
        raise ErroExportacao("Não foi possível abrir o PDF para desenhar.");
    try:
        # "Caber na página": nunca amplia, so reduz. Escala 1:1 em N paginas e pendencia do
        # bloco A (SPEC.md §3.2) -- exige paginar o desenho, nao so escalar.
        fator = min(1.0, pagina.width() / float(total.width()),
                    pagina.height() / float(total.height()));
        painter.scale(fator, fator);
        __pintar__(mapa, painter, conteudo, total, legenda, False);
    finally:
        painter.end();


def exportar(mapa, caminho, formato=None, escala=2, papel="A4", legenda=True):
    # Ponto de entrada unico. Sem formato, decide pela extensao do caminho.
    if mapa == None:
        raise ErroExportacao("Nenhum diagrama aberto.");
    if formato == None:
        formato = os.path.splitext(caminho)[1].lstrip(".").lower();
    formato = (formato or "").lower();
    if formato not in FORMATOS:
        raise ErroExportacao("Formato não suportado: %s (use pdf, png ou svg)." % (formato or "?"));
    if os.path.splitext(caminho)[1].lstrip(".").lower() != formato:
        caminho = caminho + "." + formato;
    if formato == "png":
        para_png(mapa, caminho, escala=escala, legenda=legenda);
    elif formato == "svg":
        para_svg(mapa, caminho, legenda=legenda);
    else:
        para_pdf(mapa, caminho, papel=papel, legenda=legenda);
    return caminho;
