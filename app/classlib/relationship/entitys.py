from PySide6.QtWidgets import (QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);
import sys
import uuid
import os, inspect, json;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;
from classlib.relationship.relationship_info import RelatinshipInfo;

class TimeSlice():
    def __init__(self, text_label, description, date_start, date_end, id_=None ):
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self.text_label = text_label;
        self.date_start = date_start;
        self.date_end = date_end;
        self.description = description;

    def toJson(self):
        return {"id" : self.id, "text_label" : self.text_label, "date_start" : self.date_start, "date_end" : self.date_end};

class Reference():
    def __init__(self, title, description, link1, link2, link3, id_=None):
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self.description = description;
        self.title = title;
        self.link1 = link1;
        self.link2 = link2;
        self.link3 = link3;
    
    def __str__(self):
        return self.title;
    
    def getErros(self, arr):
        if self.link1.strip() == "" and self.link2.strip() == "" and self.link3.strip() == "":
            arr.append( RelatinshipInfo.referenceHasNoLink( self ) );

    def getWarnings(self, arr):
        if self.description == None or self.description.strip() == "":
            arr.append( RelatinshipInfo.referenceHasNoDescription( self ) );
        if not self.hasWaybackMachine():
            arr.append( RelatinshipInfo.referenceHasWaybackMachine( self ) );
        
    def toJson(self):
        return {"id" : self.id, "description" : self.description, "title" : self.title, "link1" : self.link1, "link2" : self.link2, "link3" : self.link3};

    def hasWaybackMachine(self):
        if self.link1.find("web.archive.org") > 0:
            return True;
        if self.link2.find("web.archive.org") > 0:
            return True;
        if self.link3.find("web.archive.org") > 0:
            return True;
        return False;

    def getUrl(self):
        if self.link1.find("web.archive.org") > 0:
            return self.link1;
        if self.link2.find("web.archive.org") > 0:
            return self.link2;
        if self.link3.find("web.archive.org") > 0:
            return self.link3;
        if self.link1.strip() != "":
            return self.link1;
        if self.link2.strip() != "":
            return self.link2;
        if self.link3.strip() != "":
            return self.link3;
        return "";

    def citation(self):
        return "[] " + self.title + ". URL: " + self.getUrl();