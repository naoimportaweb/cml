import os, sys, inspect, json, uuid;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from PySide6.QtWidgets import (QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QPen,QFont,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);


from classlib.relationship.maprelationship_box import MapRelationshipBox;
from classlib.configuration import Configuration

class Person(MapRelationshipBox):
    def __init__(self, mapa, x, y, w, h, text=None, id_=None, entity_id_=None):
        if text == None:
            text = "Person";
        super().__init__( mapa, x, y, w, h, text=text, id_=id_, entity_id_=entity_id_ );
        self.entity.etype = "person";
        self.doxxing = "";
    
    def toJson(self):
        objeto = super().toJson();
        objeto["data_extra"] = self.doxxing;
        return objeto;  

    def draw(self, painter):
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle);
        painter.fillRect( self.x, self.y, self.w, self.h, QBrush(Qt.white));
        painter.drawRoundedRect(self.x, self.y, self.w, self.h, 5, 5);
        if self.entity.text != None:
            texto = self.entity.text;
            if self.entity.small_label != None and self.entity.small_label.strip() != "":
                texto = self.entity.small_label;
            painter.drawText(QRectF(self.x , self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, texto );

        