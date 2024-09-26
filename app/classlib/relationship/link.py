import os, sys, inspect, json, uuid;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from PySide6.QtWidgets import (QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QFont,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);


from classlib.relationship.maprelationship_box import MapRelationshipBox;
from classlib.configuration import Configuration

class Link(MapRelationshipBox):
    def __init__(self,  x, y, w, h, text=None, id_=None, entity_id_=None ):
        super().__init__( x, y, w, h, text=text, id_=id_, entity_id_=entity_id_ );
        self.entity.etype = "link";
        self.to_entity = [];
        self.from_entity = [];

    def toJson(self):
        objeto = super().toJson();
        objeto["to"] = [];
        objeto["from"] = [];
        for to_ in self.to_entity:
            objeto["to"].append(    {"id" : self.id[:40] + "_" + to_.id[:40] +  "_2", "element_id" : to_.id} );
        for from_ in self.from_entity:
            objeto["from"].append(  {"id" : self.id[:40] + "_" + to_.id[:40] +  "_1", "element_id" : from_.id} );
        return objeto;
    def hasTo(self, element):
        return element in self.to_entity;
    
    def hasFrom(self, element):
        return element in self.from_entity;

    def addTo(self, entity):
        if not entity in self.to_entity:
            self.to_entity.append( entity );

    def addFrom(self, entity):
        if not entity in self.from_entity:
            self.from_entity.append( entity );

    def draw(self, painter):
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle)
        painter.setFont(QFont(Configuration.instancia().relationshihp_font_family, Configuration.instancia().relationshihp_font_size))
        frame_text = painter.boundingRect(0, 0, 150, 30, 0, self.entity.text);
        self.w = frame_text.width() + 10;
        self.h = frame_text.height() + 2;
        painter.setPen(QPen(Qt.red, 1, Qt.DashDotLine, Qt.RoundCap));
        for element in self.to_entity:
            painter.drawLine( self.x + int( self.w / 2 ) , self.y  + int( self.h / 2 ) , element.x + int( element.w / 2), element.y + int( element.h / 2 ) );
        painter.setPen(QPen(Qt.blue, 1, Qt.DashDotLine, Qt.RoundCap));
        for element in self.from_entity:
            painter.drawLine( self.x + int( self.w / 2 ) , self.y  + int( self.h / 2 ) , element.x + int( element.w / 2), element.y + int( element.h / 2 ) );
        painter.setPen(QPen(Qt.blue, 1, Qt.DashDotLine, Qt.RoundCap));
        painter.fillRect(self.x, self.y, self.w, self.h, QBrush(Qt.white));
        painter.drawText(QRectF(self.x , self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.entity.text);
