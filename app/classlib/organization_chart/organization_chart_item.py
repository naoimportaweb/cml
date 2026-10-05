import json, uuid;
import os, sys, inspect;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;
from classlib.configuration import Configuration
from classlib.entity import Entity
from classlib.organization_chart.organization_chart_item_entity import OrganizationChartItemEntity;

from PySide6.QtCore import Qt, QRectF;
from PySide6.QtGui import QBrush, QColor, QFont, QPen;

# Geometria do organograma. Antes a altura era fixa em 25 e o y era "nivel * 75": caixa com
# tres nomes dentro transbordava por cima da linha de baixo, e caixa vazia deixava buraco.
# Agora a altura e MEDIDA e cada nivel usa a altura do maior item dele.
ESPACO_IRMAO   = 28;   # folga horizontal entre irmaos
ESPACO_NIVEL   = 58;   # folga vertical entre niveis (cabe o cotovelo do conector)
MARGEM_CAIXA   = 10;
ALTURA_TITULO  = 22;
ALTURA_LINHA   = 15;
LARGURA_MINIMA = 120;
LARGURA_MAXIMA = 260;  # acima disto o nome quebra em mais linhas, em vez de esticar a caixa

COR_BORDA      = QColor(60, 70, 85);
COR_FUNDO      = QColor(255, 255, 255);
COR_FUNDO_RAIZ = QColor(232, 238, 248);
COR_CONECTOR   = QColor(110, 122, 140);
COR_SEPARADOR  = QColor(205, 212, 222);
COR_SECUNDARIO = QColor(70, 80, 95);


class OrganizationChartItem(ConnectObject):
    def __init__(self, etype="entity", text_label="New item", _id=None, organization_chart_item_parent_id=None, organization_chart_id=None):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if _id != None:
            self.id = _id;
        self.level = 0;
        self.sequencia = 0; # usado no banco de dados para ordenar a sequencia de carregamento.
        self.entitys = [];
        self.etype = etype;
        self.text_label = text_label;
        self.organization_chart_id = organization_chart_id;
        self.organization_chart_item_parent_id = organization_chart_item_parent_id;
        self.x = 0; self.y = None; self.w = None; self.h = None;
        self.elements = [];
        self.buffer_lines_text  = [];   # nomes das entidades, ja quebrados em linhas
        self.linhas_titulo = [];        # o proprio rotulo, quebrado quando passa da largura

    # ------------------------------------------------------------------ arvore

    def addItem(self, item):
        item.level = self.level + 1;
        item.organization_chart_item_parent_id = self.id;
        self.elements.append(item);
        item.__renivelar__();

    def __renivelar__(self):
        for filho in self.elements:
            filho.level = self.level + 1;
            filho.__renivelar__();

    def remover(self, item):
        """Tira um descendente da arvore. Devolve True se achou.

        Os filhos do removido SOBEM para o lugar dele, em vez de sumirem junto: apagar um
        gerente nao apaga a equipe, e perder meia arvore por um clique e o tipo de coisa que
        nao tem volta depois do save."""
        for i in range(len(self.elements)):
            if self.elements[i] is item:
                for neto in item.elements:
                    neto.level = self.level + 1;
                    neto.organization_chart_item_parent_id = self.id;
                    neto.__renivelar__();
                self.elements[i:i + 1] = item.elements;
                return True;
            if self.elements[i].remover(item):
                return True;
        return False;

    def addEntity(self, entity, _id=None, start_date=None, end_date=None, format_date=None):
        self.entitys.append( OrganizationChartItemEntity( entity, self.id, start_date=start_date, end_date=end_date, format_date=format_date, _id=_id)  );

    def delEntity(self, indice):
        if indice < 0 or indice >= len(self.entitys):
            return False;
        self.entitys.pop(indice);
        return True;

    def setX(self, x):
        if x == None:
            self.x = x;
        else:
            self.x = int(x); # O banco de dados está retornando string, mesmo sendo int no banco de dados, naó sei a merda que deu.

    def findByXY(self, x, y):
        if self.w == None or self.h == None or self.y == None:
            return None;   # ainda nao desenhado: sem geometria nao ha o que acertar
        if self.x < x and self.x + self.w > x and self.y < y and self.y + self.h > y:
            return self;
        for element in self.elements:
            returned = element.findByXY(x, y);
            if returned != None:
                return returned;
        return None;

    def todos(self, saida=None):
        saida = [] if saida == None else saida;
        saida.append(self);
        for element in self.elements:
            element.todos(saida);
        return saida;

    # ------------------------------------------------------------------ medida

    def __fonte__(self, painter, negrito=False):
        fonte = QFont(Configuration.instancia().relationshihp_font_family,
                      Configuration.instancia().relationshihp_font_size);
        fonte.setBold(negrito);
        painter.setFont(fonte);
        return fonte;

    def __quebrar__(self, painter, texto, largura):
        """Quebra o texto em linhas que cabem na largura. O codigo antigo cortava a lista de
        entidades a cada 70 CARACTERES -- conta de maquina de escrever, que com fonte
        proporcional nao tem relacao com o que cabe."""
        palavras = str(texto or "").split();
        if len(palavras) == 0:
            return [];
        metrica = painter.fontMetrics();
        linhas = [];
        atual = "";
        for palavra in palavras:
            tentativa = palavra if atual == "" else atual + " " + palavra;
            if metrica.horizontalAdvance(tentativa) <= largura or atual == "":
                atual = tentativa;
            else:
                linhas.append(atual);
                atual = palavra;
        if atual != "":
            linhas.append(atual);
        return linhas;

    def medir(self, painter):
        """Define w e h a partir do CONTEUDO. Nao mexe em x nem em y -- quem posiciona e o
        layout da arvore, depois que todo mundo ja sabe o proprio tamanho."""
        self.__fonte__(painter, True);
        metrica = painter.fontMetrics();
        largura = max(LARGURA_MINIMA,
                      min(LARGURA_MAXIMA, metrica.horizontalAdvance(str(self.text_label or "")) + MARGEM_CAIXA * 2));
        self.linhas_titulo = self.__quebrar__(painter, self.text_label, largura - MARGEM_CAIXA * 2) or [""];

        self.__fonte__(painter, False);
        nomes = [e.getText() for e in self.entitys if str(e.getText() or "").strip() != ""];
        self.buffer_lines_text = [];
        for nome in nomes:
            self.buffer_lines_text.extend(self.__quebrar__(painter, nome, largura - MARGEM_CAIXA * 2));

        self.w = int(largura);
        self.h = int(MARGEM_CAIXA + ALTURA_TITULO * len(self.linhas_titulo)
                     + (6 + ALTURA_LINHA * len(self.buffer_lines_text) if len(self.buffer_lines_text) > 0 else 0)
                     + MARGEM_CAIXA);
        for element in self.elements:
            element.medir(painter);

    def deslocar(self, dx):
        self.x = int(self.x + dx);
        for element in self.elements:
            element.deslocar(dx);

    def __registrar__(self, limites):
        limites[self.level] = max(limites.get(self.level, 0), self.x + self.w + ESPACO_IRMAO);
        for element in self.elements:
            element.__registrar__(limites);

    def posicionar(self, limites):
        """Layout de arvore arrumada: filhos primeiro, pai centrado sobre eles.

        `limites` guarda, POR NIVEL, o proximo x livre. Tem de ser por nivel: um limite global
        unico empurraria todo mundo para a direita a cada caixa colocada, e um limite que nao
        acompanha o nivel do pai deixa duas caixas irmas encostando -- foi o que aconteceu, e a
        folga entre duas diretorias saiu 8px em vez dos 28 combinados."""
        if len(self.elements) == 0:
            self.x = int(limites.get(self.level, 0));
            self.__registrar__(limites);
            return;
        for element in self.elements:
            element.posicionar(limites);
        primeiro, ultimo = self.elements[0], self.elements[-1];
        centro = (primeiro.x + primeiro.w / 2.0 + ultimo.x + ultimo.w / 2.0) / 2.0;
        self.x = int(centro - self.w / 2.0);
        minimo = int(limites.get(self.level, 0));
        if self.x < minimo:
            # O pai bateria em quem esta a esquerda no mesmo nivel: empurra a subarvore INTEIRA,
            # senao ele sai torto sobre os proprios filhos.
            self.deslocar(minimo - self.x);
        self.__registrar__(limites);

    def alturas_por_nivel(self, alturas):
        alturas[self.level] = max(alturas.get(self.level, 0), self.h or 0);
        for element in self.elements:
            element.alturas_por_nivel(alturas);

    def aplicar_y(self, topo_do_nivel):
        self.y = int(topo_do_nivel.get(self.level, 0));
        for element in self.elements:
            element.aplicar_y(topo_do_nivel);

    def recalc(self, painter, posicao_x=0):
        """Mantido pelo nome antigo (o engine e o exportador chamam assim). Agora e o layout
        inteiro: medir, posicionar em arvore e distribuir os niveis pela altura real."""
        self.medir(painter);
        self.posicionar({self.level: posicao_x});
        alturas = {};
        self.alturas_por_nivel(alturas);
        topo = {};
        corrente = 0;
        for nivel in sorted(alturas.keys()):
            topo[nivel] = corrente;
            corrente = corrente + alturas[nivel] + ESPACO_NIVEL;
        self.aplicar_y(topo);
        return self.x + self.w + ESPACO_IRMAO;

    # ------------------------------------------------------------------ desenho

    def draw(self, painter):
        self.__conectores__(painter);
        self.__caixa__(painter);
        for element in self.elements:
            element.draw(painter);

    def __conectores__(self, painter):
        """Cotovelo, nao linha torta de centro a centro: desce do pai, corre na horizontal e
        desce em cada filho. E o que faz o desenho ser lido como hierarquia."""
        if len(self.elements) == 0:
            return;
        painter.setPen(QPen(COR_CONECTOR, 1.4));
        meio_pai = self.x + self.w / 2.0;
        base = self.y + self.h;
        barra = base + ESPACO_NIVEL / 2.0;
        painter.drawLine(int(meio_pai), int(base), int(meio_pai), int(barra));
        meios = [e.x + e.w / 2.0 for e in self.elements];
        if len(meios) > 1:
            painter.drawLine(int(min(meios)), int(barra), int(max(meios)), int(barra));
        for element in self.elements:
            meio = element.x + element.w / 2.0;
            painter.drawLine(int(meio), int(barra), int(meio), int(element.y));

    def __caixa__(self, painter):
        raiz = self.level == 0;
        painter.setPen(QPen(COR_BORDA, 2 if raiz else 1));
        painter.setBrush(QBrush(COR_FUNDO_RAIZ if raiz else COR_FUNDO));
        painter.drawRoundedRect(QRectF(self.x, self.y, self.w, self.h), 5, 5);

        self.__fonte__(painter, True);
        painter.setPen(QPen(COR_BORDA));
        y = self.y + MARGEM_CAIXA;
        for linha in self.linhas_titulo:
            painter.drawText(QRectF(self.x + MARGEM_CAIXA, y, self.w - MARGEM_CAIXA * 2, ALTURA_TITULO),
                             Qt.AlignHCenter | Qt.AlignVCenter, linha);
            y = y + ALTURA_TITULO;

        if len(self.buffer_lines_text) == 0:
            return;
        # Linha fina separando o cargo (o rotulo) de quem o ocupa (as entidades).
        painter.setPen(QPen(COR_SEPARADOR, 1));
        painter.drawLine(int(self.x + 6), int(y + 2), int(self.x + self.w - 6), int(y + 2));
        y = y + 6;
        self.__fonte__(painter, False);
        painter.setPen(QPen(COR_SECUNDARIO));
        for linha in self.buffer_lines_text:
            painter.drawText(QRectF(self.x + MARGEM_CAIXA, y, self.w - MARGEM_CAIXA * 2, ALTURA_LINHA),
                             Qt.AlignHCenter | Qt.AlignVCenter, linha);
            y = y + ALTURA_LINHA;

    # ------------------------------------------------------------------ dados

    def toJson(self, array):
        self.sequencia = len(array);
        buffer = {"id" : self.id, "x" : self.x, "etype" : self.etype, "text_label" : self.text_label, "organization_chart_id" : self.organization_chart_id, "organization_chart_item_parent_id" : self.organization_chart_item_parent_id, "entitys" : [], "sequencia" : self.sequencia };
        for entity in self.entitys:
            buffer["entitys"].append( entity.toJson() );
        array.append( buffer );
        for element in self.elements:
            element.toJson(array);
