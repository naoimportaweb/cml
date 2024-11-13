# CADA MAPA POSSUI UMA FORMA DE DESENHAR, CLICAR, SELECIONAR, ISSO FICA AQUI

from PySide6.QtWidgets import (QMenu, QWidget,QMainWindow,QApplication,QFileDialog,QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF
from PySide6.QtGui import (QCursor, QMouseEvent,QPaintEvent,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);

import os, sys, inspect, json, uuid;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( CURRENTDIR ) ) );

from view.dialog_organization_item import DialogOrganizationItem;
from classlib.configuration import Configuration

class MapaOrganizationChartEngine(QWidget):
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
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.emptySpaceMenu)

    #def getElement(self, x, y):
    #    for element in reversed(self.mapa.elements):
    #        if element.x < x and element.x + element.w > x and element.y < y and element.y + element.h > y:
    #            return element;
    #    return None;

    #def addEntity(self, ptype, x, y):
    #    return self.mapa.addEntity( ptype, x, y);

    #def delEntity(self, element):
    #    return self.mapa.delEntity( element );

    #def addExistEntity(self, entity, x, y):
    #    buffer = self.mapa.addEntity( entity["etype"], x, y, text=entity["text_label"], entity_id_=entity["id"], wikipedia=entity["wikipedia"] );
    #    if entity["etype"] == "person":
    #        buffer.doxxing = entity["data_extra"];
    #    buffer.entity.full_description = entity["description"];
    #    for reference in entity["references"]:
    #        buffer.addReference(reference["title"], reference["link1"], reference["link2"], reference["link3"], id_=reference["id"]);
    
    def paintEvent(self, event: QPaintEvent):
        with QPainter(self) as painter:
            painter.drawPixmap(0, 0, self.pixmap)

    def mousePressEvent(self, event: QMouseEvent):
        self.last_pos = event.position().toPoint();
        return;
        #self.previous_pos = event.position().toPoint();
        #QWidget.mousePressEvent(self, event);
        #current_pos = event.position().toPoint();
        #self.selected_element = self.getElement(current_pos.x(), current_pos.y());
        #if self.selected_element != None:
        #    self.diff = [current_pos.x() - self.selected_element.x, current_pos.y() - self.selected_element.y];

    def redraw(self):
        self.painter.begin(self.pixmap);
        self.pixmap.fill(Qt.white);
        self.mapa.draw(self.painter);
        #for elemento in self.mapa.elements:
        #    elemento.recalc(self.painter);
        #for elemento in self.mapa.elements:
        #    elemento.draw( self.painter );
        self.painter.end();
        self.update();

    def mouseDoubleClickEvent(self, event):
        current_pos = event.position().toPoint();
        returned = self.mapa.findByXY(current_pos.x(), current_pos.y());
        if returned == None:
            element = self.mapa.addEntityItem("New Item");
            if element != False:
                f = DialogOrganizationItem( self.form, element, self.mapa );
                f.exec();
        else:
            element = self.mapa.addEntityItem("New Item", organization_chart_item_parent_id=returned.id);
            if element != False:
                f = DialogOrganizationItem( self.form, element, self.mapa );
                f.exec();
        self.redraw();
        return;
        #
        #buffer = self.getElement(current_pos.x(), current_pos.y());
        #if self.form != None:
        #    if buffer == None:
        #        self.form.map_double_click( self, current_pos.x(), current_pos.y() );
        #    else:
        #        self.form.entity_double_click( buffer );
        #    self.redraw();

    def mouseMoveEvent(self, event: QMouseEvent):
        return;
        #current_pos = event.position().toPoint()
        #QWidget.mouseMoveEvent(self, event);
        #if self.mapa.getLocked():
        #    return;
        #if self.selected_element != None and (current_pos.y() % 2) == 0:
        #    self.selected_element.setX( current_pos.x() - self.diff[0] );
        #    self.selected_element.setY( current_pos.y() - self.diff[1] );
        #    self.redraw();
    def emptySpaceMenu(self):
        menu = QMenu()
        item = menu.addAction('Configure');
        item.triggered.connect(self.item_configure_click)
        #self.last_pos = QCursor.pos();
        menu.exec_(QCursor.pos())

    def item_configure_click(self):
        current_pos = self.last_pos;
        print(current_pos);
        returned = self.mapa.findByXY(current_pos.x(), current_pos.y());
        print(returned);
        if returned != None:
            f = DialogOrganizationItem( self.form, returned, self.mapa );
            f.exec();
        self.redraw();
        return;

    def mouseReleaseEvent(self, event: QMouseEvent):

        return;
        #self.previous_pos = None
        #QWidget.mouseReleaseEvent(self, event);
        #if self.selected_element != None:
        #    self.redraw();
        #self.selected_element = None;

    def save(self, filename: str):
        self.mapa.save();

    def load(self, filename: str):
        return;
        #self.pixmap.load(filename)
        #self.pixmap = self.pixmap.scaled(self.size(), Qt.KeepAspectRatio)
        #self.update()

    def clear(self):
        return;
        #self.pixmap.fill(Qt.white)
        #self.update()

