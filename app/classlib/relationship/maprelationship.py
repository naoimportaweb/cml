import json, uuid;
import os, sys, inspect;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;

from classlib.relationship.person import Person
from classlib.relationship.organization import Organization
from classlib.relationship.other import Other
from classlib.relationship.link import Link

class MapRelationship(ConnectObject):
    def __init__(self, id_=None):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self.name = None;
        self.keyword = None;
        self.elements = [];
        self.lock_list = [];
        self.locked = False;

    def toJson(self):
        return { "id" : self.id,  "name" : self.name, "keyword" : self.keyword, "elements" : []}
    
    def lock_map(self):
        js = self.__execute__("MapRelationship", "lock_map", {"diagram_relationship_id" : self.id });
        if js["status"]:
            self.lock_list = js["return"];
            return True;
        return False;
    
    def unlock_map(self):
        js = self.__execute__("MapRelationship", "unlock_map", {"diagram_relationship_id" : self.id });
        if js["status"]:
            self.lock_list = js["return"];
            return True;
        return False;

    def locked_map(self):
        return;

    def save(self):
        objeto = self.toJson();
        for element in self.elements:
            objeto["elements"].append( element.toJson() );
        js = self.__execute__("MapRelationship", "save", objeto);
        if js["status"]:
            return js["return"];
        return False;
    
    def load_data(self, data):
        self.id = data["id"];
        self.name = data["name"];
        self.keyword = data["keyword"];
        self.person_id = data["person_id"];
        self.lock_list = data["lock"];
        self.locked = data["locked"];
        if data.get("elements") != None:
            for element in data['elements']:
                if element["etype"] == "link":
                    continue;
                x = element["x"]; y = element["y"]; w = element["w"]; h = element["h"];
                buffer = None;
                if element['etype'] == "person":
                    buffer = Person(        x, y, w, h, text=element["text_label"], id_=element["id"], entity_id_=element["entity_id"] );
                    buffer.doxxing = element["data_extra"];
                elif element['etype'] == "other":
                    buffer = Other(        x, y, w, h, text=element["text_label"], id_=element["id"], entity_id_=element["entity_id"] );
                elif element['etype'] == "organization":
                    buffer = Organization(  x, y, w, h, text=element["text_label"], id_=element["id"], entity_id_=element["entity_id"] ) ;
                else:
                    continue;
                for reference in element["references"]:
                    buffer.addReference(reference["title"], reference["link1"], reference["link2"], reference["link3"], id_=reference["id"]);
                buffer.entity.full_description = element["full_description"];
                self.elements.append(  buffer  );
            for element in data['elements']:
                if element["etype"] != "link":
                    continue;
                x = element["x"]; y = element["y"]; w = element["w"]; h = element["h"];
                objeto = Link(x, y, w, h, text=element["text_label"], id_=element["id"], entity_id_=element["entity_id"] );
                for to_ in element["to"]:
                    objeto.addTo( self.findById( self.elements, to_["id"] ) );
                for from_ in element["from"]:
                    objeto.addFrom( self.findById( self.elements, from_["id"] ) );
                for reference in element["references"]:
                    objeto.addReference(reference["title"], reference["link1"], reference["link2"], reference["link3"], id_=reference["id"]);
                self.elements.append(  objeto  );

        return True;
    def findById(self, lista, id_):
        for buffer in lista:
            if buffer.id == id_:
                return buffer;
        return None;

    def load(self, id):
        js = self.__execute__("MapRelationship", "load", {"id" : id });
        return self.load_data(js["return"]);

    def exists(self, name):
        js = self.__execute__("MapRelationship", "exists", {"id" : self.id,  "name" : name });
        if js["status"]:
            return js["return"];
        return False;

    def search(self, name):
        js = self.__execute__("MapRelationship", "search", {"name" : name });
        return js["return"];
    def search_entity(self, name):
        js = self.__execute__("MapRelationship", "search_entity", {"name" : name });
        return js["return"];
    
    def create(self):
        js = self.__execute__("MapRelationship", "create", {"id" : self.id,  "name" : self.name, "keyword" : self.keyword });
        if js["status"]:
            return js["return"];
        return False;