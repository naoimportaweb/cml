import os, sys;

from classlib.singletonmeta import SingletonMeta;

class Server(metaclass=SingletonMeta):
    def __init__(self):
        self.status = False;
        self.protocol = "http";
        self._ip = "";
        self.port = 80;
        self.public_key = None;
        self.simetric_key = None;
        self.token = "";
        self.domain = "";

    # A URL vem de um campo de texto e costuma vir com barra no fim. Todo consumidor
    # concatena "/cml/..." direto (connectobject, dialog_relationship_edit), entao a barra
    # sobrando produz "//" no meio da URL final. Normalizar aqui pega todos os pontos de
    # atribuicao de uma vez, inclusive os que vierem depois.
    @property
    def ip(self):
        return self._ip;

    @ip.setter
    def ip(self, valor):
        self._ip = str(valor if valor != None else "").strip().rstrip("/");

    def connect(self, url, proxy=None):
        self.status = True;
    @staticmethod
    def instancia():
        return Server();
