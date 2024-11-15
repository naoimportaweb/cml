import json, uuid;
import os, sys, inspect;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;
#from classlib.relationship.person import Person
#from classlib.relationship.organization import Organization
from classlib.configuration import Configuration
from classlib.entity import Entity
from classlib.organization_chart.organization_chart_item_entity import OrganizationChartItemEntity;

from PySide6.QtWidgets import (QWidget,QMainWindow,QApplication,QFileDialog,QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,QFont);



class OrganizationChartItem(ConnectObject):
    def __init__(self, etype="entity", text_label="New item", _id=None, organization_chart_item_parent_id=None, organization_chart_id=None):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if _id != None:
            self.id = _id;
        self.level = 0;
        self.sequencia = 0; # usado no banco de dados para ordenar a sequencia de carregamento.
        self.entitys = [];
        self.etype = etype;
        self.text_label = text_label;
        self.organization_chart_id = organization_chart_id;
        self.organization_chart_item_parent_id = organization_chart_item_parent_id;
        self.x = 0; self.y = None; self.w = None; self.h = None;
        self.elements = [];
        self.buffer_lines_text  =[];

    def addItem(self, item):
        item.level = self.level + 1;
        self.elements.append(item);

    def addEntity(self, entity, _id=None, start_date=None, end_date=None, format_date=None):
        self.entitys.append( OrganizationChartItemEntity( entity, self.id, start_date=start_date, end_date=end_date, format_date=format_date, _id=_id)  );
    
    def setX(self, x):
        if x == None:
            self.x = x;
        else:
            self.x = int(x); # O banco de dados está retornando string, mesmo sendo int no banco de dados, naó sei a merda que deu.
    
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
            buffer_string += entity.getText() + ", ";
            if len(buffer_string) > 70:
                self.buffer_lines_text.append(buffer_string);
                buffer_string = "";
        if len(buffer_string) > 0:
            self.buffer_lines_text.append(buffer_string);
        
        self.w = self.__size_text__( self.text_label, painter)["w"] + 10;
        for line in self.buffer_lines_text:
            buffer_size_line = self.__size_text__( line, painter);
            if buffer_size_line["w"] > self.w:
                self.w = buffer_size_line["w"];
        self.h = 25;
        self.y = (self.level * 75);
        posicao = posicao_x;
        for element in self.elements:
            posicao += element.recalc( painter, posicao );
        return self.w + self.x + 10;
    
    def draw(self, painter):
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle)
        
        for element in self.elements:
            painter.drawLine( self.x + int( self.w / 2 ) , self.y  + int( self.h / 2 ) , element.x + int( element.w / 2), element.y + int( element.h / 2 ) );

        painter.fillRect( self.x, self.y, self.w, self.h + (15 * len(self.buffer_lines_text)) , QBrush(Qt.white));
        painter.drawRect( self.x, self.y, self.w, self.h + (15 * len(self.buffer_lines_text)));
        painter.drawText(QRectF(self.x, self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.text_label);
        for i in range(len( self.buffer_lines_text )):
            painter.drawText(QRectF(self.x + 5, self.y + 15 + (12 * i) , self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.buffer_lines_text[i]);
        for element in self.elements:
            element.draw( painter );
    
    def toJson(self, array):
        self.sequencia = len(array);
        buffer = {"id" : self.id, "x" : self.x, "etype" : self.etype, "text_label" : self.text_label, "organization_chart_id" : self.organization_chart_id, "organization_chart_item_parent_id" : self.organization_chart_item_parent_id, "entitys" : [], "sequencia" : self.sequencia };
        for entity in self.entitys:
            buffer["entitys"].append( entity.toJson() );
        array.append( buffer );
        for element in self.elements:
            element.toJson(array);
        
