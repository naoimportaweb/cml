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
    def load(self, id):
        return True;
    def create(self):
        js = self.__execute__("OrganizationChart", "create", {"id" : self.id,  "organization_id" : self.organization_id, "text_label" : self.text_label });
        if js["status"]:
            return js["return"];
        return False;

    def toJson(self):
        buffer = {"id" : self.id, "organization_id" : self.organization_id, "elements" : []};
        for item in self.elements:
            buffer["elements"].append( item.toJson() );
        return buffer;

    def addChartItem(self, text_label, organization_chart_item_parent_id=None, _id=None ):
        self.elements.addItem( OrganizationChartItem(  "entity", text_label, organization_chart_item_parent_id=organization_chart_item_parent_id, _id=_id) );
    
    def addChartItem(self, text_label, organization_chart_id, organization_chart_item_parent_id=None, _id=None ):
        self.elements.addItem( OrganizationChartItem(  "chart", text_label, organization_chart_item_parent_id=organization_chart_item_parent_id , organization_chart_id=organization_chart_id, _id=_id) );

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
    def __init__(self, etype, text_label, id_=None, organization_chart_item_parent_id=None, organization_chart_id=None):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self.entitys = [];
        self.etype = etype;
        self.text_label = text_label;
        self.organization_chart_id = organization_chart_id;
        self.organization_chart_item_parent_id = organization_chart_item_parent_id;
    
    def toJson(self):
        return {"id" : self.id, "etype" : self.etype, "text_label" : self.text_label, "organization_chart_id" : self.organization_chart_id, "organization_chart_item_parent_id" : self.organization_chart_item_parent_id, "entetys" : [] };

