import os, sys;

from classlib.singletonmeta import SingletonMeta;

class Server(metaclass=SingletonMeta):
    def __init__(self):
        self.status = False;
    def connect(self, url, proxy=None):
        self.status = True;


