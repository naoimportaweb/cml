import os, sys, inspect, json, uuid;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from PySide6.QtWidgets import (QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QFont,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);

from classlib.configuration import Configuration
from classlib.entity import Entity

class MapRelationshipBox():
    def __init__(self, mapa, x, y, w, h, text=None, id_=None, entity_id_=None):
        self.id =         uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        self.mapa = mapa;
        if id_ != None:
            self.id = id_;
        self.entity = Entity(entity_id_);
        self.entity.text = text;
        self.entity.full_description = "";
        self._dirt = False;
        self.x = x;
        self.y = y;
        self.w = w;
        self.h = h;
    
    def getDirt(self):
        return self._dirt or self.entity.getDirt();
    
    def setX(self, x):
        self.x = x;
        self._dirt = True;

    def setY(self, y):
        self.y = y;
        self._dirt = True;

    def toJson(self):
        objeto = { "id" : self.id, "entity_id": self.entity.id , "x" : self.x, "y" : self.y, "w" : self.w, "h" : self.h, "text" : self.entity.text, "full_description" : self.entity.full_description, "etype" : self.entity.etype, "references" : [], "time_slices" : [], "data_extra" : self.entity.data_extra, "wikipedia" : self.entity.wikipedia, "classification" : self.entity.classification  };
        
        for reference in self.entity.references:
            buffer = reference.toJson();
            buffer["entity_id"] = self.entity.id;
            objeto["references"].append( buffer );
        
        for time_slice in self.entity.time_slices:
            buffer = time_slice.toJson();
            buffer["entity_id"] = self.entity.id;
            objeto["time_slices"].append( buffer );
        return objeto;
            
    def setType(self, etype):
        if etype == self.entity.etype:
            return True;
        return self.mapa.switchType(self, etype);

    def addReference(self, title, link1, link2 = "", link3 = "", id_=None):
        return self.entity.addReference(title, link1, link2, link3, id_);

    def addTimeSlice(self, text_label, date_start=None, date_end=None, id_=None):
        return self.entity.addTimeSlice(text_label, date_start, date_end, id_);
    
    def recalc(self, painter):
        painter.setFont(QFont(Configuration.instancia().relationshihp_font_family, Configuration.instancia().relationshihp_font_size))
        frame_text = painter.boundingRect(0, 0, 150, 30, 0, self.entity.text);
        self.w = frame_text.width() + 10;
        self.h = frame_text.height() + 2;
    def draw(self, painter):
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle)
        #painter.setFont(QFont(Configuration.instancia().relationshihp_font_family, Configuration.instancia().relationshihp_font_size))
        #frame_text = painter.boundingRect(0, 0, 150, 30, 0, self.entity.text);
        #self.w = frame_text.width() + 10;
        #self.h = frame_text.height() + 2;
        painter.fillRect( self.x, self.y, self.w, self.h, QBrush(Qt.white));
        painter.drawRect( self.x, self.y, self.w, self.h);
        if self.entity.text != None:
            painter.drawText(QRectF(self.x , self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.entity.text)
