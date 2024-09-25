from PySide6.QtWidgets import (QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);
import sys
import uuid
import os, inspect, json;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append(CURRENTDIR);
sys.path.append( os.path.dirname( CURRENTDIR ));


from classlib.connectobject import ConnectObject;

class Entity(ConnectObject):
    def __init__(self, id_=None):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self.etype = None;
        self.text = None;
        self.full_description = None;
        self.data_extra = "";
        self.references = [];
        self.time_slices = [];

    def addReference(self, title, link1, link2 = "", link3 = "", id_=None):
        if link1 == "":
            return None;
        self.references.append( Reference( title, link1, link2, link3, id_=id_ ) );
        return self.references[-1];

    def addTimeSlice(self, text_label, date_start=None, date_end=None, id_=None):
        if text_label == "":
            return None;
        self.time_slices.append( TimeSlice( text_label, date_start, date_end, id_=id_ ) );
        return self.time_slices[-1];
        
    def toJson(self):
        return { "id" : self.id,  "name" : self.name}

    def toType(self):
        js = self.__execute__("Entity", "to_type", {});
        if js["status"]:
            return js["return"];
        return False;
    

class TimeSlice():
    def __init__(self, text_label, date_start, date_end, id_=None ):
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self.text_label = text_label;
        self.date_start = date_start;
        self.date_end = date_end;

    def toJson(self):
        return {"id" : self.id, "text_label" : self.text_label, "date_start" : self.date_start, "date_end" : self.date_end};

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
        if id_ != None:
            self.id = id_;
        self.entity = Entity(entity_id_);
        self.entity.text = text;
        self.entity.full_description = "";
        self.x = x;
        self.y = y;
        self.w = w;
        self.h = h;        
    
    def toJson(self):
        objeto = { "id" : self.id, "entity_id": self.entity.id , "x" : self.x, "y" : self.y, "w" : self.w, "h" : self.h, "text" : self.entity.text, "full_description" : self.entity.full_description, "etype" : self.entity.etype, "references" : [], "time_slices" : [], "data_extra" : self.entity.data_extra  };
        
        for reference in self.entity.references:
            buffer = reference.toJson();
            buffer["entity_id"] = self.entity.id;
            objeto["references"].append( buffer );
        
        for time_slice in self.entity.time_slices:
            buffer = time_slice.toJson();
            buffer["entity_id"] = self.entity.id;
            objeto["time_slices"].append( buffer );
        return objeto;
            
    def addReference(self, title, link1, link2 = "", link3 = "", id_=None):
        return self.entity.addReference(title, link1, link2, link3, id_);

    def addTimeSlice(self, text_label, date_start=None, date_end=None, id_=None):
        return self.entity.addTimeSlice(text_label, date_start, date_end, id_);
    
    def draw(self, painter):
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle)
        frame_text = painter.boundingRect(0, 0, 150, 30, 0, self.entity.text);
        self.w = frame_text.width() + 10;
        self.h = frame_text.height() + 2;
        painter.fillRect( self.x, self.y, self.w, self.h, QBrush(Qt.white));
        painter.drawRect( self.x, self.y, self.w, self.h);
        if self.entity.text != None:
            painter.drawText(QRectF(self.x , self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.entity.text)

class Person(Rectangle):
    def __init__(self, x, y, w, h, text=None, id_=None, entity_id_=None):
        super().__init__( x, y, w, h, text=text, id_=id_, entity_id_=entity_id_ );
        self.entity.etype = "person";
        self.doxxing = "";
    
    def toJson(self):
        objeto = super().toJson();
        objeto["data_extra"] = self.doxxing;
        return objeto;  

    def draw(self, painter):
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle)
        frame_text = painter.boundingRect(0, 0, 150, 30, 0, self.entity.text);
        self.w = frame_text.width() + 10;
        self.h = frame_text.height() + 2;
        painter.fillRect( self.x, self.y, self.w, self.h, QBrush(Qt.white));
        painter.drawRoundedRect(self.x, self.y, self.w, self.h, 5, 5);
        if self.entity.text != None:
            painter.drawText(QRectF(self.x , self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.entity.text)
        #path.addRoundedRect(QRectF(10, 10, 100, 50), 10, 10);

class Organization(Rectangle):
    def __init__(self, x, y, w, h, text=None, id_=None, entity_id_=None ):
        super().__init__( x, y, w, h, text=text, id_=id_, entity_id_=entity_id_ );
        self.entity.etype = "organization";

class Other(Rectangle):
    def __init__(self, x, y, w, h, text=None, id_=None, entity_id_=None ):
        super().__init__( x, y, w, h, text=text, id_=id_, entity_id_=entity_id_ );
        self.entity.etype = "other";
    def draw(self, painter):
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle)
        frame_text = painter.boundingRect(0, 0, 150, 30, 0, self.entity.text);
        self.w = frame_text.width() + 10;
        self.h = frame_text.height() + 2;
        painter.fillRect( self.x, self.y, self.w, self.h, QBrush(Qt.yellow));
        if self.entity.text != None:
            painter.drawText(QRectF(self.x , self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.entity.text)

class Link(Rectangle):
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
