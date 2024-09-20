from PySide6.QtWidgets import (QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);
import sys
import uuid


class Reference():
    def __init__(self, title, link1, link2, link3, id_=None):
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self.title = title;
        self.link1 = link1;
        self.link2 = link2;
        self.link3 = link3;
    
    def toJson(self):
        return {"id" : self.id, "title" : self.title, "link1" : self.link1, "link2" : self.link2, "link3" : self.link3};

class Rectangle():
    def __init__(self, x, y, w, h, text=None, id_=None, entity_id_=None):
        self.id =         uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        self.entity_id =  uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        if entity_id_ != None:
            self.entity_id = entity_id_;
        self.x = x;
        self.y = y;
        self.w = w;
        self.h = h;
        #self.map = map;
        self.text = text;
        self.full_description = "";
        self.references = [];
    
    def toJson(self):
        objeto = { "id" : self.id, "entity_id": self.entity_id , "x" : self.x, "y" : self.y, "w" : self.w, "h" : self.h, "text" : self.text, "full_description" : self.full_description, "etype" : self.etype, "references" : []  };
        for reference in self.references:
            buffer = reference.toJson();
            buffer["entity_id"] = self.entity_id;
            objeto["references"].append( buffer );
        return objeto;
            
    def addReference(self, title, link1, link2 = "", link3 = ""):
        if link1 == "":
            return None;
        self.references.append( Reference( title, link1, link2, link3 ) );
        return self.references[-1];
    
    def draw(self, painter):
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle)
        frame_text = painter.boundingRect(0, 0, 150, 30, 0, self.text);
        self.w = frame_text.width() + 10;
        self.h = frame_text.height() + 2;
        painter.fillRect( self.x, self.y, self.w, self.h, QBrush(Qt.white));
        painter.drawRect( self.x, self.y, self.w, self.h);
        if self.text != None:
            painter.drawText(QRectF(self.x , self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.text)

class Person(Rectangle):
    def __init__(self, x, y, w, h, text=None, id_=None, entity_id_=None):
        super().__init__( x, y, w, h, text=text, id_=id_, entity_id_=entity_id_ );
        self.etype = "person";
        self.doxxing = "";

class Organization(Rectangle):
    def __init__(self, x, y, w, h, text=None, id_=None, entity_id_=None ):
        super().__init__( x, y, w, h, text=text, id_=id_, entity_id_=entity_id_ );
        self.etype = "organization";

class Link(Rectangle):
    def __init__(self,  x, y, w, h, text=None, id_=None, entity_id_=None ):
        super().__init__( x, y, w, h, text=text, id_=id_, entity_id_=entity_id_ );
        self.etype = "link";
        self.to_entity = [];
        self.from_entity = [];

    def toJson(self):
        objeto = super().toJson();
        objeto["to"] = [];
        objeto["from"] = [];
        for to_ in self.to_entity:
            objeto["to"].append(    {"id" : self.id + "_2", "element_id" : to_.id} );
        for from_ in self.from_entity:
            objeto["from"].append(  {"id" : self.id + "_1", "element_id" : from_.id} );
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
        frame_text = painter.boundingRect(0, 0, 150, 30, 0, self.text);
        self.w = frame_text.width() + 10;
        self.h = frame_text.height() + 2;
        painter.setPen(QPen(Qt.blue, 1, Qt.DashDotLine, Qt.RoundCap));
        for element in self.to_entity:
            painter.drawLine( self.x + int( self.w / 2 ) , self.y  + int( self.h / 2 ) , element.x + int( element.w / 2), element.y + int( element.h / 2 ) );
        for element in self.from_entity:
            painter.drawLine( self.x + int( self.w / 2 ) , self.y  + int( self.h / 2 ) , element.x + int( element.w / 2), element.y + int( element.h / 2 ) );
        painter.fillRect(self.x, self.y, self.w, self.h, QBrush(Qt.white));
        painter.drawText(QRectF(self.x , self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.text);
