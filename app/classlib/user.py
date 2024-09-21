import json, hashlib;
import os, sys, inspect
import random
import string
import uuid

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append(CURRENTDIR);
sys.path.append( os.path.dirname( CURRENTDIR ));

from classlib.server import Server;
from classlib.connectobject import ConnectObject;


class User (ConnectObject):
    def __init__(self, username):
        super().__init__();
        self.user_id = None;
        self.username = username;
        self.session_key = None;
        #self.simetric_key = None;
        self.salt = None;
    # chama o publickey(), depois o session() depois o login() para logar.....;
    def publickey(self):
        js = self.__execute__("Session", "publickey", {});
        if js["status"]:
            self.salt = js["return"]["salt"];
            return js["return"]["public"];
        return None;

    def teste(self):
        js = self.__execute__("User", "teste", {"username" : self.username}, crypto_v="000");
        if js["status"]:
            return js["return"]["username"];
        return None;
    #def session(self):
    #    js = self.__execute__("Session", "create", {"username" : self.username });
    #    if js["status"]:
    #        self.session_key = js["return"]["session"];
    #        self.salt = js["return"]["salt"];
    #        return True;
    #    return False;

    def login(self, password):
        server = Server();
        password = hashlib.sha256( (password + self.salt).encode() ).hexdigest();
        server.simetric_key = str(uuid.uuid4())[:32]
        js = self.__execute__("Session", "login", {"username" : self.username, "password" : password, "simetric_key" : server.simetric_key }, crypto_v="000");
        if js["status"]:
            self.user_id = js["return"]["id"];
            if server.token == "":
                server.token = js["return"]["token"];
                print("Nova token: ", server.token);
            return True;
        return False;