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
    
    def switchType(self, box_element, etype):
        if etype == "person" or etype == "other" or etype == "organization":
            if box_element.entity.toType(etype):
                self.elements.pop( self.elements.index( box_element ) );
                buffer = self.addEntity(etype, box_element.x, box_element.y, text=box_element.entity.text, id_=box_element.id, entity_id_=box_element.entity.id);
                for i in range(len(self.elements)):
                    if self.elements[i].entity.etype == "link":
                        for j in range(len( self.elements[i].to_entity )):
                            if self.elements[i].to_entity[j] == box_element:
                                self.elements[i].to_entity[j] = buffer;
                        for j in range(len( self.elements[i].from_entity )):
                            if self.elements[i].from_entity[j] == box_element:
                                self.elements[i].from_entity[j] = buffer;
                return buffer;
        return False;
    
    def delEntity(self, element):
        if element.entity.etype == "link" and (len(element.to_entity) > 0 or len(element.from_entity)):
            raise Exception("O relacionamento possui links para entidades.");
        for k in range(len(self.elements)):
            if self.elements[k].entity.etype == "link":
                for buffer_ref in self.elements[k].to_entity:
                    if buffer_ref.id == element.id:
                       raise Exception("O elemento existe em um relacionamento, exclua o relacionamento."); 
                for buffer_ref in self.elements[k].from_entity:
                    if buffer_ref.id == element.id:
                       raise Exception("O elemento existe em um relacionamento, exclua o relacionamento."); 

        for i in range(len(self.elements)):
            if self.elements[i].id == element.id:
                self.elements.pop(i);
                return;

    def addEntity(self, ptype, x, y, text=None, id_=None, entity_id_=None, wikipedia=None):
        if ptype == "person":
            self.elements.append(  Person(self,     x, y, 100, 20 , text=text, id_=id_, entity_id_=entity_id_)  );
        elif ptype == "other":
            self.elements.append(  Other( self,     x, y, 100, 20 , text=text, id_=id_, entity_id_=entity_id_)  );
        elif ptype == "organization":
            self.elements.append(  Organization( self, x, y, 100, 20 , text=text, id_=id_, entity_id_=entity_id_)  );
        elif ptype == "link":
            self.elements.append(  Link(  self,  x, y, 100, 20 , text=text, id_=id_, entity_id_=entity_id_)  );
        buffer = self.elements[-1];
        buffer.entity.wikipedia = wikipedia;
        return buffer;
    
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
                if element['etype'] == "person" or element['etype'] == "other" or element['etype'] == "organization":
                    x = int(element["x"]); y = int(element["y"]); w = int(element["w"]); h = int(element["h"]);
                    buffer = self.addEntity( element['etype'], x, y, text=element["text_label"], id_=element["id"], entity_id_=element["entity_id"], wikipedia=element["wikipedia"] );
                    if element['etype'] == "person":
                        buffer.doxxing = element["data_extra"];
                    for reference in element["references"]:
                        buffer.addReference(reference["title"], reference["link1"], reference["link2"], reference["link3"], id_=reference["id"]);
                    buffer.entity.full_description = element["full_description"];
                    buffer.entity.classification = element["classification"];
                    buffer.entity.small_label = element["small_label"];
            for element in data['elements']:
                if element["etype"] == "link":
                    x = int(element["x"]); y = int(element["y"]); w = int(element["w"]); h = int(element["h"]);
                    objeto = self.addEntity( "link",  x, y, text=element["text_label"], id_=element["id"], entity_id_=element["entity_id"], wikipedia=element["wikipedia"]);
                    for to_ in element["to"]:
                        objeto.addTo( self.findById( self.elements, to_["id"] ), start_date=to_["start_date"], end_date=to_["end_date"], format_date=to_["format_date"] );
                    for from_ in element["from"]:
                        objeto.addFrom( self.findById( self.elements, from_["id"] ) );
                    for reference in element["references"]:
                        objeto.addReference(reference["title"], reference["link1"], reference["link2"], reference["link3"], id_=reference["id"]);
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
        js = self.__execute__("Map", "search", {"name" : name });
        return js["return"];
    
    def search_entity(self, name):
        js = self.__execute__("MapRelationship", "search_entity", {"name" : name });
        return js["return"];
    
    def create(self):
        js = self.__execute__("MapRelationship", "create", {"id" : self.id,  "name" : self.name, "keyword" : self.keyword });
        if js["status"]:
            return js["return"];
        return False;