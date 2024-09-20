# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause

from PySide6.QtWidgets import (QWidget,QMainWindow,QApplication,QFileDialog,QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);

import os, sys, inspect, json, uuid;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( CURRENTDIR ) ) );

from classlib.entitys import Person, Organization, Link, Rectangle

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

    def addExistEntity(self, entity, x, y):
        buffer = None;
        if entity["etype"] == "person":
            buffer = Person(  x, y, 100, 20 , text=entity["text_label"], entity_id_=entity["id"]);
        elif entity["etype"] == "organization":
            buffer = Organization(  x, y, 100, 20 , text=entity["text_label"], entity_id_=entity["id"])  ;
        elif entity["etype"] == "link":
            buffer =  Link(  x, y, 100, 20 , text=entity["text_label"], entity_id_=entity["id"])  ;
        self.mapa.elements.append(  buffer  );
    
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

