import os, sys, inspect, json, uuid;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from PySide6.QtWidgets import (QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QFont,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);


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
            objeto["to"].append(    {"id" : self.id[:40] + "_" + to_.entity.id[:40] +  "_2", "element_id" : to_.entity.id, "start_date" : to_.start_date, "end_date" : to_.end_date} );
        for from_ in self.from_entity:
            objeto["from"].append(  {"id" : self.id[:40] + "_" + from_.entity.id[:40] +  "_1", "element_id" : from_.entity.id, "start_date" : from_.start_date, "end_date" : from_.end_date} );
        print("Enviar:", objeto);
        return objeto;
    def hasTo(self, element):
        return element in self.to_entity;
    
    def hasFrom(self, element):
        return element in self.from_entity;

    def addTo(self, entity, start_date=None, end_date=None):
        lentity = LinkEntity(entity, start_date, end_date);
        for buffer in self.to_entity:
            if buffer.entity.id == lentity.entity.id:
                return True;
        self.to_entity.append( lentity );

    def addFrom(self, entity):
        lentity = LinkEntity(entity, None, None);
        for buffer in self.from_entity:
            if buffer.entity.id == lentity.entity.id:
                return True;
        self.from_entity.append( lentity );

    def draw(self, painter):
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle)
        painter.setPen(QPen(Qt.red, 1, Qt.DashDotLine, Qt.RoundCap));
        for buffer_entity in self.to_entity:
            element = buffer_entity.entity;
            painter.drawLine( self.x + int( self.w / 2 ) , self.y  + int( self.h / 2 ) , element.x + int( element.w / 2), element.y + int( element.h / 2 ) );
        painter.setPen(QPen(Qt.blue, 1, Qt.DashDotLine, Qt.RoundCap));
        for buffer_entity in self.from_entity:
            element = buffer_entity.entity;
            painter.drawLine( self.x + int( self.w / 2 ) , self.y  + int( self.h / 2 ) , element.x + int( element.w / 2), element.y + int( element.h / 2 ) );
        painter.setPen(QPen(Qt.blue, 1, Qt.DashDotLine, Qt.RoundCap));
        painter.fillRect(self.x, self.y, self.w, self.h, QBrush(Qt.white));
        painter.drawText(QRectF(self.x , self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.entity.text);
