# CADA MAPA POSSUI UMA FORMA DE DESENHAR, CLICAR, SELECIONAR, ISSO FICA AQUI

from PySide6.QtWidgets import (QWidget,QMainWindow,QApplication,QFileDialog,QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);

import os, sys, inspect, json, uuid;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( CURRENTDIR ) ) );

from classlib.relationship.person import Person
from classlib.relationship.organization import Organization
from classlib.relationship.other import Other
from classlib.relationship.link import Link
from classlib.entity import Entity;

class MapaRelationshipEngine(QWidget):
    def __init__(self, parent=None, mapa=None, form=None, max_width=5000 , max_height=3000):
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
        self.diff = [0 , 0];

    def getElement(self, x, y):
        for element in reversed(self.mapa.elements):
            if element.x < x and element.x + element.w > x and element.y < y and element.y + element.h > y:
                return element;
        return None;

    def addEntity(self, ptype, x, y):
        return self.mapa.addEntity( ptype, x, y);

    def delEntity(self, element):
        return self.mapa.delEntity( element );

    def addExistEntity(self, entity, x, y):
        buffer = self.mapa.addEntity( entity["etype"], x, y, text=entity["text_label"], entity_id_=entity["id"], wikipedia=entity["wikipedia"] );
        if entity["etype"] == "person":
            buffer.doxxing = entity["data_extra"];
        buffer.entity = Entity.fromJson( entity );
        #for reference in entity["references"]:
        #    buffer.addReference(reference["title"], reference["link1"], reference["link2"], reference["link3"], id_=reference["id"], descricao=reference["descricao"]);
    
    def paintEvent(self, event: QPaintEvent):
        with QPainter(self) as painter:
            painter.drawPixmap(0, 0, self.pixmap)

    def mousePressEvent(self, event: QMouseEvent):
        self.previous_pos = event.position().toPoint();
        QWidget.mousePressEvent(self, event);
        current_pos = event.position().toPoint();
        self.selected_element = self.getElement(current_pos.x(), current_pos.y());
        if self.selected_element != None:
            self.diff = [current_pos.x() - self.selected_element.x, current_pos.y() - self.selected_element.y];

    def redraw(self):
        self.painter.begin(self.pixmap);
        self.pixmap.fill(Qt.white);
        for elemento in self.mapa.elements:
            elemento.recalc(self.painter);
        for elemento in self.mapa.elements:
            if elemento.entity.etype == "link":
                elemento.draw( self.painter );
        for elemento in self.mapa.elements:
            if elemento.entity.etype == "person" or elemento.entity.etype == "organization" or elemento.entity.etype == "other":
                elemento.draw( self.painter );
        self.painter.end();
        self.update();

    def mouseDoubleClickEvent(self, event):
        current_pos = event.position().toPoint();
        buffer = self.getElement(current_pos.x(), current_pos.y());
        if self.form != None:
            if buffer == None:
                self.form.map_double_click( self, current_pos.x(), current_pos.y() );
            else:
                self.form.entity_double_click( buffer );
            self.redraw();

    def mouseMoveEvent(self, event: QMouseEvent):
        current_pos = event.position().toPoint()
        QWidget.mouseMoveEvent(self, event);
        if self.mapa.getLocked():
            return;
        if self.selected_element != None and (current_pos.y() % 2) == 0:
            self.selected_element.setX( current_pos.x() - self.diff[0] );
            self.selected_element.setY( current_pos.y() - self.diff[1] );
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

