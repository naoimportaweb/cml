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
        self._dirt = False;
        self.etype = None;
        self.text = None;
        self.full_description = None;
        self.data_extra = "";
        self.references = [];
        self.time_slices = [];
        self.wikipedia = "";
        self.classification = [];
        self.small_label = None;
    
    def getText(self):
        return self.text;
    
    def addClassification(self, classification_id, text_label, classification_item_id, text_label_choice, start_date, end_date, format_date):
        for buffer in self.classification:
            if buffer["id"] == classification_id + self.id:
                return False;
        self.classification.append({ "entity_id" : self.id , "id" : classification_id + self.id, "classification_id" : classification_id, "text_label" : text_label, 
            "classification_item_id" : classification_item_id, "text_label_choice" : text_label_choice, "start_date" : start_date,  "end_date" : end_date, "format_date" : format_date });
        return True;
        
    def getDirt(self):
        return self._dirt;
    
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
        return { "id" : self.id, "etype" : self.etype, "name" : self.text, "data_extra" : self.data_extra, "full_description" : self.full_description, "wikipedia" : self.wikipedia, "classification" : self.classification, "small_label" : self.small_label}

    def toType(self, etype):
        js = self.__execute__("Entity", "to_type", {"type" : etype, "id" : self.id});
        if js["status"]:
            self.etype = etype;
            return js["return"];
        return False;

    @staticmethod
    def search(etype, text_label):
        obj = ConnectObject();
        js = obj.__execute__("Entity", "search", {"etype" : etype, "text_label" : text_label});
        if js["status"]:
            return js["return"];
        return False;
    
    @staticmethod    
    def fromJson( js):
        buffer = Entity(id_=js["id"]);
        buffer.id = js["id"];
        buffer.etype = js["etype"];
        buffer.text = js["text_label"];
        buffer.full_description = js.get("full_description");
        buffer.data_extra = js["data_extra"];
        buffer.wikipedia = js["wikipedia"];
        buffer.small_label = js["small_label"];
        return buffer;