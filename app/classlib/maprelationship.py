import json, uuid;
import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append(CURRENTDIR);
sys.path.append( os.path.dirname( CURRENTDIR ));

from classlib.connectobject import ConnectObject;
from classlib.entitys import Person, Organization, Link, Rectangle

class MapRelationship(ConnectObject):
    def __init__(self, id_=None):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self.name = None;
        self.keyword = None;
        self.elements = [];

    def toJson(self):
        return { "id" : self.id,  "name" : self.name, "keyword" : self.keyword, "elements" : []}
    
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
        if data.get("elements") != None:
            for element in data['elements']:
                if element["etype"] == "link":
                    continue;
                x = element["x"]; y = element["y"]; w = element["w"]; h = element["h"];
                buffer = None;
                if element['etype'] == "person":
                    buffer = Person(        x, y, w, h, text=element["text_label"], id_=element["id"], entity_id_=element["entity_id"] );
                elif element['etype'] == "organization":
                    buffer = Organization(  x, y, w, h, text=element["text_label"], id_=element["id"], entity_id_=element["entity_id"] ) ;
                else:
                    continue;
                for reference in element["references"]:
                    buffer.addReference(reference["title"], reference["link1"], reference["link1"], reference["link1"]);
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
                    objeto.addReference(reference["title"], reference["link1"], reference["link1"], reference["link1"]);
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
    
    def create(self):
        js = self.__execute__("MapRelationship", "create", {"id" : self.id,  "name" : self.name, "keyword" : self.keyword });
        if js["status"]:
            return js["return"];
        return False;