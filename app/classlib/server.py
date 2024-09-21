import os, sys;

from classlib.singletonmeta import SingletonMeta;

class Server(metaclass=SingletonMeta):
    def __init__(self):
        self.status = False;
        self.protocol = "http";
        self.ip = "127.0.0.1";
        self.port = 80;
        self.public_key = None;
    def connect(self, url, proxy=None):
        self.status = True;


