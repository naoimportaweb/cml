import json, uuid;
import os, sys, inspect;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;

from classlib.relationship.person import Person
from classlib.relationship.organization import Organization


class OrganizationChart(ConnectObject):
    def __init__(self, organization_id, id_=None):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self.organization_id = organization_id;
        self.text_label = "New Organizatin Chart";
        self.organization = None;
        self.elements = [];
    
    def getLocked(self):
        return False;    
    
    def getName(self):
        return self.text_label;

    def load(self, id):
        return True;

    def save(self):
        objeto = self.toJson();
        for element in self.elements:
            objeto["elements"].append( element.toJson() );
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
        for item in self.elements:
            buffer["elements"].append( item.toJson() );
        return buffer;

    def addEntityItem(self, text_label, organization_chart_item_parent_id=None, _id=None ):
        self.elements.append( OrganizationChartItem(  etype="entity", text_label=text_label, organization_chart_item_parent_id=organization_chart_item_parent_id, _id=_id) );
        return self.elements[-1];
    
    def addChartItem(self, text_label, organization_chart_id, organization_chart_item_parent_id=None, _id=None ):
        self.elements.append( OrganizationChartItem(  etype="chart", text_label=text_label, organization_chart_item_parent_id=organization_chart_item_parent_id , organization_chart_id=organization_chart_id, _id=_id) );
        return self.elements[-1];
    
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
        self.entitys = [];
        self.etype = etype;
        self.text_label = text_label;
        self.organization_chart_id = organization_chart_id;
        self.organization_chart_item_parent_id = organization_chart_item_parent_id;
        self.x = None;
        self.h = None;

    def addEntity(self, entity):
        self.entitys.append( {"entity" : entity} );
    
    def recalc(self, painter):
        painter.setFont(QFont(Configuration.instancia().relationshihp_font_family, Configuration.instancia().relationshihp_font_size))
        frame_text = painter.boundingRect(0, 0, 150, 30, 0, self.text_label);
        self.w = frame_text.width() + 10;
        self.h = frame_text.height() + 2;
        return;
    
    def draw(self):
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle)
        painter.fillRect( 10, 10, self.w, self.h, QBrush(Qt.white));
        painter.drawRect( 10, 10, self.w, self.h);
        if self.entity.text != None:
            painter.drawText(QRectF(10, 10, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.entity.text)
    
    def toJson(self):
        buffer = {"id" : self.id, "etype" : self.etype, "text_label" : self.text_label, "organization_chart_id" : self.organization_chart_id, "organization_chart_item_parent_id" : self.organization_chart_item_parent_id, "entetys" : [] };
        for entity in self.entitys:
            buffer["entitys"].append( entity.toJson() );
        return buffer;
