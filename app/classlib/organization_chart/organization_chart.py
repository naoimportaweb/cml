import json, uuid;
import os, sys, inspect;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;

from classlib.relationship.person import Person
from classlib.relationship.organization import Organization
from classlib.configuration import Configuration
from classlib.entity import Entity
from classlib.organization_chart.organization_chart_item import OrganizationChartItem;

from PySide6.QtWidgets import (QWidget,QMainWindow,QApplication,QFileDialog,QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,QFont);

class OrganizationChart(ConnectObject):
    def __init__(self, organization_id, id_=None):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self.organization_id = organization_id;
        self.text_label = "New Organizatin Chart";
        self.organization = None;
        self.root = None;
    
    def draw(self, painter):
        if self.root != None:
            self.root.recalc( painter );
            self.root.draw( painter );

    def getLocked(self):
        return False;    
    
    def getName(self):
        return self.text_label;
    
    def load_data(self, data):
        self.id = data["id"];
        self.organization_id = data["organization_id"];
        self.text_label = data["text_label"];
        self.organization = Entity.fromJson(data["organization"]);
        if data.get("elements") != None:
            for element in data['elements']:
                item = self.addChartItem(element["text_label"], element["organization_chart_id"], 
                    organization_chart_item_parent_id=element["organization_chart_item_parent_id"], _id=element["id"] );
                item.x = element["x"];
                for buffer in element["entitys"]:
                    item.addEntity( Entity.fromJson( buffer["entity"]), _id=buffer["id"] , start_date=buffer["start_date"], end_date=buffer["end_date"], format_date=buffer["format_date"]   );

        return True;
    def load(self, id):
        js = self.__execute__("OrganizationChart", "load", {"id" : id });
        return self.load_data(js["return"]);

    def save(self):
        objeto = self.toJson();
        js = self.__execute__("OrganizationChart", "save", objeto);
        if js["status"]:
            return js["return"];
        return False;

    def create(self):
        js = self.__execute__("OrganizationChart", "create", {"id" : self.id,  "organization_id" : self.organization_id, "text_label" : self.text_label });
        if js["status"]:
            return js["return"];
        return False;

    def toJson(self):
        buffer = {"id" : self.id, "organization_id" : self.organization_id, "text_label" : self.text_label, "elements" : []};
        elements = [];
        if self.root != None:
            self.root.toJson( elements );
        buffer["elements"] = elements;
        return buffer;

    def findByXY(self, x, y):
        if self.root != None:
            return self.root.findByXY(x, y);
        return None;

    def __addItem__(self, item ):
        # tentar adicionar um RAIZ, SO PODE TER 1 RAIZ NO CHART
        print( item.text_label );
        if item.organization_chart_item_parent_id == None and self.root == None:
            self.root = item;
            return item;
        parent = self.__findItem__(self.root, item.organization_chart_item_parent_id);
        if parent != None:
            parent.addItem( item );
            return item;
        return item;

    def __findItem__(self, element, id):
        # Node que estamos procurando
        if element == None:
            return None;
        if element.id == id:
            return element;
        for buffer in element.elements:
            returned = self.__findItem__(buffer, id);
            if returned != None:
                return returned;
        return None;

    def addEntityItem(self, text_label, organization_chart_item_parent_id=None, _id=None ):
        return self.__addItem__( OrganizationChartItem(  etype="entity", text_label=text_label, organization_chart_item_parent_id=organization_chart_item_parent_id, _id=_id) );
        
    
    def addChartItem(self, text_label, organization_chart_id, organization_chart_item_parent_id=None, _id=None ):
        return self.__addItem__( OrganizationChartItem(  etype="chart", text_label=text_label, organization_chart_item_parent_id=organization_chart_item_parent_id , organization_chart_id=organization_chart_id, _id=_id) );
        
    def loadOrganization(self):
        js = self.__execute__("OrganizationChart", "load", {"_id" : self.id });
        if js["status"]:
            self.organization = Entity.fromJson(js["return"]["organization"]);
            self.text_label =   js["return"]["text_label"];
            self.organization_chart_id = js["return"]["organization_chart_id"];
            self.organization_id = js["return"]["organization_id"];
            return True;
        return False;
