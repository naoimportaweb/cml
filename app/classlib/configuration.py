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
        config_ = {"font" : {"family" : "Courier", "size" : 12}};
        if os.path.exists(self.path_config):
            config_ = json.loads( open( self.path_config, "r").read() );
        else:
            with open(self.path_config, "w") as f:
                f.write( json.dumps(config_) );
        self.font_size = config_["font"]["size"];
        self.font_family = config_["font"]["family"];
    
    def getFont(self):
        font = QFont()
        font.setPointSize(self.font_size);
        font.setFamily(self.font_family );
        return font;

    @staticmethod
    def instancia():
        return Configuration();