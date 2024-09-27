import os, sys, json;

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );

sys.path.append( ROOT );

from classlib.singletonmeta import SingletonMeta;
from PySide6.QtGui import QFont;

class Configuration(metaclass=SingletonMeta):
    def __init__(self):
        self.path_config = os.path.expanduser('~') + "/.cml.json";
        self.config_ = {};
        if os.path.exists(self.path_config):
            self.config_ = json.loads( open( self.path_config, "r").read() );
        self.font_size = self.__getParameter__(self.config_,   "form.font.size", 12);
        self.font_family = self.__getParameter__(self.config_, "form.font.family", "Courier");
        self.relationshihp_font_size = self.__getParameter__(self.config_,    "relationshihp.font.size", 10);
        self.relationshihp_font_scale = self.__getParameter__(self.config_,   "relationshihp.font.scale", 1);
        self.relationshihp_font_family = self.__getParameter__(self.config_,  "relationshihp.font.family", "Vernana");
    
    def __getParameter__(self, js, name, default):
        if name.find(".") > 0:
            if js.get( name[:name.find(".") ] ) == None:
                js[name[:name.find(".") ]] = {};
            return self.__getParameter__(js[name[:name.find(".") ]], name[ name.find(".") + 1:], default);
        else:
            if js.get(name) == None:
                js[name] = default;
                self.__save__(); ## já salva
            return js[name];

    def __save__(self):
        with open(self.path_config, "w") as f:
            f.write( json.dumps(self.config_) );
            return True;
        return False;

    def getFont(self):
        font = QFont()
        font.setPointSize(self.font_size);
        font.setFamily(self.font_family );
        return font;

    @staticmethod
    def instancia():
        return Configuration();