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
        js = self.__execute__("Session", "publickey", {"username" : self.username });
        if js["status"]:
            self.salt = js["return"]["salt"];
            return js["return"]["public"];
        return None;
    def register(self, username, password, email, invitation):
        salt = str(uuid.uuid4());
        password = hashlib.sha256( (password + salt).encode() ).hexdigest();
        js = self.__execute__("Session", "register", {"username" : username, "password" : password, "salt" : salt, "email" : email, "invitation" : invitation}, crypto_v="000");
        if js["return"]["status"]:
            return True;
        raise Exception( js["return"]["mensage"] );

    #def teste(self):
    #    js = self.__execute__("User", "teste", {"username" : self.username}, crypto_v="000");
    #    if js["status"]:
    #        return js["return"]["username"];
    #    return None;
    #def session(self):
    #    js = self.__execute__("Session", "create", {"username" : self.username });
    #    if js["status"]:
    #        self.session_key = js["return"]["session"];
    #        self.salt = js["return"]["salt"];
    #        return True;
    #    return False;

    def login(self, password):
        server = Server();
        if self.salt == None:
            # publickey() devolve salt nulo quando o usuário não existe. Concatenar
            # aqui estouraria TypeError; tratar como credencial inválida também evita
            # revelar se o usuário existe ou não.
            return False;
        password = hashlib.sha256( (password + self.salt).encode() ).hexdigest();
        server.simetric_key = str(uuid.uuid4())[:32]
        js = self.__execute__("Session", "login", {"username" : self.username, "password" : password, "simetric_key" : server.simetric_key }, crypto_v="000");
        if js["status"]:
            # A autenticação recusada volta com status true (o transporte funcionou) e
            # return vazio. Do PHP, array() vira [] no json_encode — uma lista, e
            # indexar por "id" estoura TypeError em vez de sinalizar senha inválida.
            retorno = js["return"];
            if type(retorno) != type({}) or retorno.get("id") == None:
                return False;
            self.user_id = retorno["id"];
            if server.token == "":
                server.token = retorno["token"];
            return True;
        return False;