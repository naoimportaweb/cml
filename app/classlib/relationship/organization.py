import os, sys, inspect, json, uuid;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from PySide6.QtWidgets import (QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QPen,QFont,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);


from classlib.relationship.maprelationship_box import MapRelationshipBox;

class Organization(MapRelationshipBox):
    def __init__(self, mapa, x, y, w, h, text=None, id_=None, entity_id_=None ):
        super().__init__(mapa, x, y, w, h, text=text, id_=id_, entity_id_=entity_id_ );
        self.entity.etype = "organization";
        if text == None:
            text = "Organization";