import json, uuid;
import os, sys, inspect;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;
#from classlib.relationship.person import Person
#from classlib.relationship.organization import Organization
#from classlib.configuration import Configuration
#from classlib.entity import Entity

#from PySide6.QtWidgets import (QWidget,QMainWindow,QApplication,QFileDialog,QStyle,QColorDialog,)
#from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
#from PySide6.QtGui import (QMouseEvent,QPaintEvent,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,QFont);

class OrganizationChartItemEntity(ConnectObject):
    def __init__(self, entity, organization_chart_item_id, _id=None, format_date=None, end_date=None, start_date=None):
        super().__init__();
        self.entity = entity;
        self.organization_chart_item_id = organization_chart_item_id;
        self.format_date = format_date;
        self.start_date = start_date;
        self.end_date = end_date;
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if _id != None:
            self.id = _id;
    def toJson(self):
        return {"id" : self.id, "entity_id" : self.entity.id, "start_date" : self.start_date, "end_date" : self.end_date, "format_date" : self.format_date};
    def getText(self):
        return self.entity.getText();