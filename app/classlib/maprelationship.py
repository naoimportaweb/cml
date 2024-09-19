import json, uuid;
import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append(CURRENTDIR);
sys.path.append( os.path.dirname( CURRENTDIR ));

from classlib.connectobject import ConnectObject;

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
                if element['etype'] == "person":
                    self.mapa.elements.append(  Person( self, x, y, 100, 20 , text="Person")  );
                elif element['etype'] == "organization":
                    self.mapa.elements.append(  Organization( self, x, y, 100, 20 , text="Organization")  );
                elif element['etype'] == "link":
                    self.mapa.elements.append(  Link( self, x, y, 100, 20 , text="Relationship")  );
                else:
                    self.mapa.elements.append(  Rectangle( self, x, y, 100, 20 , text="?????")  );

        return True;
    
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