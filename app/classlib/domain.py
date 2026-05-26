import os, sys, inspect, json, uuid;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;
from classlib.relationship.entitys import Reference, TimeSlice

class Domain(ConnectObject):
    def __init__(self):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
    def list(self):
        js = self.__execute__("Domain", "list", {"id" : self.id});
        if js["status"]:
            return js["return"];
        return False;

