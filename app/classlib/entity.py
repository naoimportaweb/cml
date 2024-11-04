import os, sys, inspect, json, uuid;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;
from classlib.relationship.entitys import Reference, TimeSlice
from classlib.relationship.relationship_info import RelatinshipInfo;

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
        self.start_date = None;
        self.end_date = None;
        self.format_date = "yyyy-MM-dd";
        self.default_url = None;

    #def getWarnings(self, arr):
    #    if self.full_description == None or self.full_description.strip() == "":
    #        if self.etype == "link":
    #            arr.append( RelatinshipInfo.linkHasNoDescription( self ) );
    #    for reference in self.references:
    #        reference.getWarnings(arr);
    #def getErros(self, arr):
    #    if self.full_description == None or self.full_description.strip() == "":
    #        if self.etype != "link":
    #            arr.append( RelatinshipInfo.entityHasNoDescription( self ) );
    #    for reference in self.references:
    #        reference.getErros(arr);
    
    def __str__(self):
        return self.text;
    
    def getText(self):
        return self.text;
    
    def addClassification(self, classification_id, text_label, classification_item_id, text_label_choice, start_date, end_date, format_date):
        for buffer in self.classification:
            if buffer["id"] == classification_id + self.id:
                return False;
        self.classification.append({ "start_date" : self.start_date, "end_date" : self.end_date, "format_date" : self.format_date, "default_url" : self.default_url,  "entity_id" : self.id , "id" : classification_id + self.id, "classification_id" : classification_id, "text_label" : text_label, 
            "classification_item_id" : classification_item_id, "text_label_choice" : text_label_choice, "start_date" : start_date,  "end_date" : end_date, "format_date" : format_date });
        return True;
        
    def getDirt(self):
        return self._dirt;
    
    def addReference(self, title, link1, link2 = "", link3 = "", id_=None, descricao = ""):
        if link1 == "":
            return None;
        self.references.append( Reference( title, descricao, link1, link2, link3, id_=id_ ) );
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

    def duplicate(self):
        if self.text == "Person" or self.text == "Organization" or self.text == "Other":
            return [];
        js = self.__execute__("Entity", "duplicate", { "etype" : "person", "text_label" : self.text, "id" : self.id});
        if js["status"]:
            return js["return"];
        return False;
    
    def merge_to(self, old_entity_id):
        js = self.__execute__("Entity", "merge_to", { "old_entity_id" : old_entity_id, "new_entity_id" : self.id});
        if js["status"]:
            return js["return"];
        return False;

    @staticmethod
    def search(etype, text_label, proxy=False):
        obj = ConnectObject();
        js = obj.__execute__("Entity", "search", {"etype" : etype, "text_label" : text_label});
        out = [];
        if js["status"]:
            out.push( { "name" : "local",  js["return"]  } );
        if proxy:
            js = obj.__proxy__("Entity", "search", {"etype" : etype, "text_label" : text_label});
            print(js);
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