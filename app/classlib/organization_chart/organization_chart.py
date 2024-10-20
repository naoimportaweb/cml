import json, uuid;
import os, sys, inspect;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;

from classlib.relationship.person import Person
from classlib.relationship.organization import Organization
from classlib.configuration import Configuration

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

    def load(self, id):
        return True;

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
        if item.organization_chart_item_parent_id == None and self.root == None:
            self.root = item;
            return item;
        parent = self.__findItem__(self.root, item.organization_chart_item_parent_id);
        if parent != None:
            parent.addItem( item );
            return item;
        return False;

    def __findItem__(self, element, id):
        # Node que estamos procurando
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
#       organization_chart
#           []organization_chart_item { etype, []entity, text_label, 
#                                      organization_chart_item_id, person_id 
#                                      organization_chart_id }
class OrganizationChartItem(ConnectObject):
    def __init__(self, etype="entity", text_label="New item", _id=None, organization_chart_item_parent_id=None, organization_chart_id=None):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if _id != None:
            self.id = _id;
        self.level = 0;
        self.entitys = [];
        self.etype = etype;
        self.text_label = text_label;
        self.organization_chart_id = organization_chart_id;
        self.organization_chart_item_parent_id = organization_chart_item_parent_id;
        self.x = None; self.y = None; self.w = None; self.h = None;
        self.elements = [];
        self.buffer_lines_text  =[];

    def addItem(self, item):
        item.level = self.level + 1;
        self.elements.append(item);

    def addEntity(self, entity):
        self.entitys.append( {"entity" : entity} );
    
    def findByXY(self, x, y):
        if self.x < x and self.x + self.w > x and self.y < y and self.y + self.h > y:
            return self;
        for element in self.elements:
            returned = element.findByXY(x, y);
            if returned != None:
                return returned;
        return None;

    def __size_text__(self, text, painter):
        painter.setFont(QFont(Configuration.instancia().relationshihp_font_family, Configuration.instancia().relationshihp_font_size))
        frame_text = painter.boundingRect(0, 0, 150, 30, 0, text);
        return {"w" :frame_text.width() , "h" : frame_text.height()};

    def recalc(self, painter, posicao_x=0):
        # Tenho que montar um array de linhas, com no máximo 70 caracteres cada linha. E vai quebrando as linhas.
        self.buffer_lines_text = [];
        buffer_string = "";
        for entity in self.entitys:
            buffer_string += entity["entity"].getText() + ", ";
            if len(buffer_string) > 70:
                self.buffer_lines_text.append(buffer_string);
                buffer_string = "";
        if len(buffer_string) > 0:
            self.buffer_lines_text.append(buffer_string);
        
        self.w = self.__size_text__( self.text_label, painter)["w"];
        for line in self.buffer_lines_text:
            buffer_size_line = self.__size_text__( line, painter);
            if buffer_size_line["w"] > self.w:
                self.w = buffer_size_line["w"];
        self.h = 25;
        self.x = posicao_x;
        self.y = (self.level * 50);
        posicao = posicao_x;
        for element in self.elements:
            posicao += element.recalc( painter, posicao );
        return self.w + self.x + 10;
    
    def draw(self, painter):
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle)
        painter.fillRect( self.x, self.y, self.w, self.h + (15 * len(self.buffer_lines_text)) , QBrush(Qt.white));
        painter.drawRect( self.x, self.y, self.w, self.h + (15 * len(self.buffer_lines_text)));
        painter.drawText(QRectF(self.x, self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.text_label);
        for i in range(len( self.buffer_lines_text )):
            painter.drawText(QRectF(self.x, self.y + 15 + (12 * i) , self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.buffer_lines_text[i]);
        for element in self.elements:
            element.draw( painter );
    
    def toJson(self, array):
        buffer = {"id" : self.id, "etype" : self.etype, "text_label" : self.text_label, "organization_chart_id" : self.organization_chart_id, "organization_chart_item_parent_id" : self.organization_chart_item_parent_id, "entitys" : [] };
        for entity in self.entitys:
            buffer["entitys"].append( entity["entity"].toJson() );
        for element in self.elements:
            element.toJson(array);
        array.append( buffer );
