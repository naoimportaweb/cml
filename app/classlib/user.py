import json;
import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append(CURRENTDIR);
sys.path.append( os.path.dirname( CURRENTDIR ));

from classlib.connectobject import ConnectObject;

class User (ConnectObject):
    def __init__(self, user, password):
        super().__init__();
        self.user = user;
        self.password = password;
        self.session_key = None;

    def session(self):
        js = self.__execute__("Session", "create", {"user" : self.user, "password" : self.password });
        if js["status"]:
            self.session_key = js["return"];
            return True;
        return False;