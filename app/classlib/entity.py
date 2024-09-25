import os, sys, inspect, json, uuid;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;
from classlib.relationship.entitys import Reference, TimeSlice

class Entity(ConnectObject):
    def __init__(self, id_=None):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self.etype = None;
        self.text = None;
        self.full_description = None;
        self.data_extra = "";
        self.references = [];
        self.time_slices = [];

    def addReference(self, title, link1, link2 = "", link3 = "", id_=None):
        if link1 == "":
            return None;
        self.references.append( Reference( title, link1, link2, link3, id_=id_ ) );
        return self.references[-1];

    def addTimeSlice(self, text_label, date_start=None, date_end=None, id_=None):
        if text_label == "":
            return None;
        self.time_slices.append( TimeSlice( text_label, date_start, date_end, id_=id_ ) );
        return self.time_slices[-1];
        
    def toJson(self):
        return { "id" : self.id,  "name" : self.name}

    def toType(self):
        js = self.__execute__("Entity", "to_type", {});
        if js["status"]:
            return js["return"];
        return False;
    