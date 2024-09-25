import os, sys;

from classlib.singletonmeta import SingletonMeta;

class Configuration(metaclass=SingletonMeta):
    
    def __init__(self):
        self.font_size = 12;
        self.font_family = "Courier";
    
    def getFont(self):
        font = QtGui.QFont()
        font.setPointSize(self.font_size);
        font.setFamily(self.font_family );
        return font;