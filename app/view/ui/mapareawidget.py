# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause

from PySide6.QtWidgets import (QWidget,QMainWindow,QApplication,QFileDialog,QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);
import sys
import uuid

class Reference():
    def __init__(self, title, link1, link2, link3):
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        self.title = title;
        self.link1 = link1;
        self.link2 = link2;
        self.link3 = link3;
    
    def toJson(self):
        return {"id" : self.id, "title" : self.title, "link1" : self.link1, "link2" : self.link2, "link3" : self.link3};

class Rectangle():
    def __init__(self, x, y, w, h, text=None, id_=None, entity_id_=None):
        self.id =         uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        self.entity_id =  uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        if entity_id_ != None:
            self.entity_id = entity_id_;
        self.x = x;
        self.y = y;
        self.w = w;
        self.h = h;
        #self.map = map;
        self.text = text;
        self.full_description = "";
        self.references = [];
    
    def toJson(self):
        objeto = { "id" : self.id, "entity_id": self.entity_id , "x" : self.x, "y" : self.y, "w" : self.w, "h" : self.h, "text" : self.text, "full_description" : self.full_description, "etype" : self.etype, "references" : []  };
        for reference in self.references:
            objeto["references"].append( reference.toJson() );
        return objeto;
            
    def addReference(self, title, link1, link2 = "", link3 = ""):
        if link1 == "":
            return None;
        self.references.append( Reference( title, link1, link2, link3 ) );
        return self.references[-1];
    
    def draw(self, painter):
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle)
        frame_text = painter.boundingRect(0, 0, 150, 30, 0, self.text);
        self.w = frame_text.width() + 10;
        self.h = frame_text.height() + 2;
        painter.fillRect( self.x, self.y, self.w, self.h, QBrush(Qt.white));
        painter.drawRect( self.x, self.y, self.w, self.h);
        if self.text != None:
            painter.drawText(QRectF(self.x , self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.text)

class Person(Rectangle):
    def __init__(self,  x, y, w, h, text=None):
        super().__init__( x, y, w, h, text);
        self.etype = "person";
        self.doxxing = "";

class Organization(Rectangle):
    def __init__(self, x, y, w, h, text=None):
        super().__init__( x, y, w, h, text);
        self.etype = "organization";

class Link(Rectangle):
    def __init__(self,  x, y, w, h, text=None):
        super().__init__( x, y, w, h, text);
        self.etype = "link";
        self.to_entity = [];
        self.from_entity = [];

    def toJson(self):
        objeto = super().toJson();
        objeto["to"] = [];
        objeto["from"] = [];
        for to in self.to_entity:
            objeto["to"].append( {"id" : to.id} );
        for from_ in self.from_entity:
            objeto["from"].append( {"id" : from_.id} );
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
        frame_text = painter.boundingRect(0, 0, 150, 30, 0, self.text);
        self.w = frame_text.width() + 10;
        self.h = frame_text.height() + 2;
        painter.setPen(QPen(Qt.blue, 1, Qt.DashDotLine, Qt.RoundCap));
        for element in self.to_entity:
            painter.drawLine( self.x + int( self.w / 2 ) , self.y  + int( self.h / 2 ) , element.x + int( element.w / 2), element.y + int( element.h / 2 ) );
        for element in self.from_entity:
            painter.drawLine( self.x + int( self.w / 2 ) , self.y  + int( self.h / 2 ) , element.x + int( element.w / 2), element.y + int( element.h / 2 ) );
        painter.fillRect(self.x, self.y, self.w, self.h, QBrush(Qt.white));
        painter.drawText(QRectF(self.x , self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.text);

class MapAreaWidget(QWidget):
    def __init__(self, parent=None, mapa=None, form=None, max_width=15000 , max_height=10000):
        super().__init__(parent)
        self.setFixedSize(max_width, max_height);
        self.form = form;
        
        self.mapa = mapa; # class.map
        self.pixmap = QPixmap(self.size());
        self.pixmap.fill(Qt.white);
        self.previous_pos = None;
        self.painter = QPainter();
        self.pen = QPen();
        self.pen.setWidth(10);
        self.pen.setCapStyle(Qt.RoundCap);
        self.pen.setJoinStyle(Qt.RoundJoin);
        self.selected_element = None;

    def getElement(self, x, y):
        for element in reversed(self.mapa.elements):
            if element.x < x and element.x + element.w > x and element.y < y and element.y + element.h > y:
                return element;
        return None;

    def addEntity(self, ptype, x, y):
        if ptype == "person":
            self.mapa.elements.append(  Person(  x, y, 100, 20 , text="Person")  );
        elif ptype == "organization":
            self.mapa.elements.append(  Organization(  x, y, 100, 20 , text="Organization")  );
        elif ptype == "link":
            self.mapa.elements.append(  Link(  x, y, 100, 20 , text="Relationship")  );
        else:
            self.mapa.elements.append(  Rectangle(  x, y, 100, 20 , text="?????")  );

    def paintEvent(self, event: QPaintEvent):
        with QPainter(self) as painter:
            painter.drawPixmap(0, 0, self.pixmap)

    def mousePressEvent(self, event: QMouseEvent):
        self.previous_pos = event.position().toPoint();
        QWidget.mousePressEvent(self, event);
        current_pos = event.position().toPoint();
        self.selected_element = self.getElement(current_pos.x(), current_pos.y());

    def redraw(self):
        self.painter.begin(self.pixmap);
        self.pixmap.fill(Qt.white);
        for elemento in self.mapa.elements:
            if elemento.etype == "person" or elemento.etype == "organization":
                elemento.draw( self.painter );
        for elemento in self.mapa.elements:
            if elemento.etype == "link":
                elemento.draw( self.painter );
        self.painter.end();
        self.update();

    def mouseDoubleClickEvent(self, event):
        current_pos = event.position().toPoint();
        buffer = self.getElement(current_pos.x(), current_pos.y());
        if self.form != None:
            if buffer == None:
                #self.elements.append(  Rectangle( current_pos.x(), current_pos.y(), 100, 20 , text="?????")  );
                self.form.map_double_click( self, current_pos.x(), current_pos.y() );
            else:
                self.form.entity_double_click( buffer );
            self.redraw();

    def mouseMoveEvent(self, event: QMouseEvent):
        current_pos = event.position().toPoint()
        QWidget.mouseMoveEvent(self, event);
        if self.selected_element != None:
            self.selected_element.x = current_pos.x();
            self.selected_element.y = current_pos.y();
            if (current_pos.x() % 10) == 0: # Questao de desempenho.....
                self.redraw();

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.previous_pos = None
        QWidget.mouseReleaseEvent(self, event);
        if self.selected_element != None:
            self.redraw();
        self.selected_element = None;

    def save(self, filename: str):
        self.mapa.save();

    def load(self, filename: str):
        self.pixmap.load(filename)
        self.pixmap = self.pixmap.scaled(self.size(), Qt.KeepAspectRatio)
        self.update()

    def clear(self):
        self.pixmap.fill(Qt.white)
        self.update()

