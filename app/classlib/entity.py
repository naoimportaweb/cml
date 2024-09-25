import os, sys, inspect, json, uuid;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append(CURRENTDIR);
sys.path.append( os.path.dirname( CURRENTDIR ));

from classlib.connectobject import ConnectObject;

class Entity(ConnectObject):
    def __init__(self, id_=None):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self.name = None;
        self.etype = None;
        self.text_label = None;
        self.full_description = None;

    def toJson(self):
        return { "id" : self.id,  "name" : self.name}

    def toType(self):
        js = self.__execute__("Entity", "to_type", {});
        if js["status"]:
            return js["return"];
        return False;
    