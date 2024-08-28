import os, sys;

from api.fsseguro import FsSeguro;
from class.singletonmeta import SingletonMeta;

class Server(metaclass=SingletonMeta):
    def __init__(self, url, proxy=None):
        print();


