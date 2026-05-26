import os, sys;

from classlib.singletonmeta import SingletonMeta;

class Server(metaclass=SingletonMeta):
    def __init__(self):
        self.status = False;
        self.protocol = "http";
        self.ip = "";
        self.port = 80;
        self.public_key = None;
        self.simetric_key = None;
        self.token = "";
        self.domain = "";
    def connect(self, url, proxy=None):
        self.status = True;
    @staticmethod
    def instancia():
        return Server();
