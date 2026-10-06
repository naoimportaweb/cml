import os, sys, inspect, json, uuid, math;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from PySide6.QtWidgets import (QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF,QPointF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QFont,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,QPolygonF,);

from classlib.relationship.maprelationship_box import MapRelationshipBox;
from classlib.configuration import Configuration
from classlib.relationship.link_entity import LinkEntity;


class Link(MapRelationshipBox):
    def __init__(self, mapa,  x, y, w, h, text=None, id_=None, entity_id_=None ):
        if text == None:
            text = "Relationship";
        super().__init__( mapa, x, y, w, h, text=text, id_=id_, entity_id_=entity_id_ );
        self.entity.etype = "link";
        self.to_entity = [];
        self.from_entity = [];

    def delTo(self, index):
        self.to_entity.pop( index );
    
    def delFrom(self, index):
        self.from_entity.pop( index );

    def toJson(self):
        objeto = super().toJson();
        objeto["to"] = [];
        objeto["from"] = [];
        for to_ in self.to_entity:
            objeto["to"].append(    {"id" : self.id[:40] + "_" + to_.entity.id[:40] +  "_2", "element_id" : to_.entity.id, "start_date" : to_.start_date, "end_date" : to_.end_date, "format_date" : to_.format_date} );
        for from_ in self.from_entity:
            objeto["from"].append(  {"id" : self.id[:40] + "_" + from_.entity.id[:40] +  "_1", "element_id" : from_.entity.id, "start_date" : from_.start_date, "end_date" : from_.end_date, "format_date" : from_.format_date} );
        return objeto;
    def hasTo(self, element):
        return element in self.to_entity;
    
    def hasFrom(self, element):
        return element in self.from_entity;

    def addTo(self, entity, start_date=None, end_date=None, format_date="yyyy-MM-dd"):
        lentity = LinkEntity(entity, start_date, end_date, format_date);
        for buffer in self.to_entity:
            if buffer.entity.id == lentity.entity.id:
                return True;
        self.to_entity.append( lentity );

    def addFrom(self, entity, start_date=None, end_date=None, format_date="yyyy-MM-dd"):
        # As datas eram descartadas aqui (o addTo ja as recebia): a ponta "from" voltava do
        # load sem periodo e o proximo save zerava a coluna no banco.
        lentity = LinkEntity(entity, start_date, end_date, format_date or "yyyy-MM-dd");
        for buffer in self.from_entity:
            if buffer.entity.id == lentity.entity.id:
                return True;
        self.from_entity.append( lentity );

    def _seta(self, painter, ox, oy, element, cor):
        # Ponta de seta na BORDA da caixa de destino, apontando para dentro dela: mostra a
        # direcao da relacao (from -> vinculo -> to). (ox,oy) e o centro do vinculo (origem
        # da linha); a linha vai ate o centro do alvo, mas a seta fica na borda para nao
        # ficar escondida sob a caixa, que e desenhada depois.
        cx = element.x + element.w / 2;
        cy = element.y + element.h / 2;
        dx = ox - cx;
        dy = oy - cy;   # do centro do alvo de volta para a origem
        if dx == 0 and dy == 0:
            return;
        hw = element.w / 2;
        hh = element.h / 2;
        tx = hw / abs(dx) if dx != 0 else float("inf");
        ty = hh / abs(dy) if dy != 0 else float("inf");
        t = min(tx, ty);                 # onde a linha cruza a borda do alvo
        bx = cx + dx * t;
        by = cy + dy * t;                # ponta da seta, na borda voltada para a origem
        ang = math.atan2(by - oy, bx - ox);   # sentido de avanco: origem -> alvo
        tam = 11;
        abertura = math.radians(22);
        p1 = QPointF( bx - tam * math.cos(ang - abertura), by - tam * math.sin(ang - abertura) );
        p2 = QPointF( bx - tam * math.cos(ang + abertura), by - tam * math.sin(ang + abertura) );
        painter.setPen(QPen(cor, 1, Qt.SolidLine, Qt.RoundCap));
        painter.setBrush(QBrush(cor));
        painter.drawPolygon(QPolygonF([QPointF(bx, by), p1, p2]));
        painter.setBrush(Qt.NoBrush);

    def peso(self):
        """Peso DERIVADO: quantas referencias sustentam este vinculo.

        E o eixo da procedencia (SPEC §1.3) virando desenho -- vinculo com tres fontes aparece
        mais grosso que o de uma. Nao ha coluna no banco: o peso e contado do que ja existe, e
        por isso esta pronto sem migracao. Peso MANUAL, se um dia for preciso, e que exigiria
        coluna nova em diagram_relationship_link."""
        return len(self.entity.references or []);

    def __espessura__(self):
        # Teto de 4: acima disso a linha vira mancha e para de comunicar diferenca.
        return min(4, 1 + self.peso());

    def __data_da_ponta__(self, painter, ox, oy, ponta, cor):
        """Escreve o periodo da ponta ao longo da propria linha.

        A data fica a 72% do caminho (perto da caixa de destino, longe do verbo que esta no
        meio): e a ponta que tem data, nao o vinculo -- as duas podem ter periodos diferentes."""
        inicio = str(getattr(ponta, "start_date", None) or "").strip();
        fim = str(getattr(ponta, "end_date", None) or "").strip();
        if inicio in ("", "0000-00-00"):
            inicio = "";
        if fim in ("", "0000-00-00"):
            fim = "";
        if inicio == "" and fim == "":
            return;
        texto = (inicio + " → " + fim) if (inicio != "" and fim != "") else (inicio + " →" if inicio != "" else "← " + fim);
        alvo = ponta.entity;
        if alvo == None or alvo.w == None:
            return;
        destino_x = alvo.x + (alvo.w or 0) / 2.0;
        destino_y = alvo.y + (alvo.h or 0) / 2.0;
        x = ox + (destino_x - ox) * 0.72;
        y = oy + (destino_y - oy) * 0.72;
        painter.save();
        try:
            fonte = QFont(painter.font());
            fonte.setPointSize(max(6, fonte.pointSize() - 2));
            painter.setFont(fonte);
            painter.setPen(QPen(cor));
            painter.drawText(QPointF(x + 4, y - 3), texto);
        finally:
            painter.restore();

    def draw(self, painter):
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle)
        ox = self.x + int( self.w / 2 );
        oy = self.y + int( self.h / 2 );
        espessura = self.__espessura__();
        painter.setPen(QPen(Qt.red, espessura, Qt.DashDotLine, Qt.RoundCap));
        for buffer_entity in self.to_entity:
            element = buffer_entity.entity;
            painter.drawLine( ox, oy, element.x + int( element.w / 2), element.y + int( element.h / 2 ) );
        for buffer_entity in self.to_entity:
            self._seta( painter, ox, oy, buffer_entity.entity, Qt.red );
            self.__data_da_ponta__( painter, ox, oy, buffer_entity, Qt.darkRed );
        painter.setPen(QPen(Qt.blue, espessura, Qt.DashDotLine, Qt.RoundCap));
        for buffer_entity in self.from_entity:
            element = buffer_entity.entity;
            painter.drawLine( ox, oy, element.x + int( element.w / 2), element.y + int( element.h / 2 ) );
        for buffer_entity in self.from_entity:
            self.__data_da_ponta__( painter, ox, oy, buffer_entity, Qt.darkBlue );
        painter.setPen(QPen(Qt.blue, 1, Qt.DashDotLine, Qt.RoundCap));
        painter.fillRect(self.x, self.y, self.w, self.h, QBrush(Qt.white));
        painter.drawText(QRectF(self.x , self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.entity.text);
