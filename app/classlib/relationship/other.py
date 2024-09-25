import os, sys, inspect, json, uuid;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from PySide6.QtWidgets import (QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);


from classlib.relationship.maprelationship_box import MapRelationshipBox;

class Other(MapRelationshipBox):
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
