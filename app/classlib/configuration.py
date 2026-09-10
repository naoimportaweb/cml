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
            try:
                self.config_ = json.loads( open( self.path_config, "r").read() );
            except:
                print("Erro de má formação de Json. Assumindo dados padrões.");
                self.config_ = {};
        self.font_size =                             self.__getParameter__(self.config_,  "form.font.size", 12);
        self.font_family =                           self.__getParameter__(self.config_,  "form.font.family", "Courier");
        self.relationshihp_font_size =               self.__getParameter__(self.config_,  "relationshihp.font.size", 10);
        self.relationshihp_font_scale =              self.__getParameter__(self.config_,  "relationshihp.font.scale", 1);
        self.relationshihp_font_family =             self.__getParameter__(self.config_,  "relationshihp.font.family", "Courier");
        self.login_username =                        self.__getParameter__(self.config_,  "login.username", "");
        self.login_server =                          self.__getParameter__(self.config_,  "login.server", "http://localhost");
        # Tamanho das janelas que o usuario redimensionou, por nome. Fica num dicionario e
        # nao em campos fixos porque toda janela nova precisaria mexer aqui e no __save__ —
        # e o __save__ remonta o JSON do zero, entao chave esquecida some no proximo save.
        self.janelas =                               self.__getParameter__(self.config_,  "janelas", {});

    def __getParameter__(self, js, name, default):
        if name.find(".") > 0:
            if js.get( name[:name.find(".") ] ) == None:
                js[name[:name.find(".") ]] = {};
            return self.__getParameter__(js[name[:name.find(".") ]], name[ name.find(".") + 1:], default);
        else:
            if js.get(name) == None:
                js[name] = default;
            return js[name];

    def __save__(self):
        self.config_ = {"form" : {"font" : {"size" :  self.font_size, "family" : self.font_family}}, "relationshihp" : {"font" : {"size" : self.relationshihp_font_size, "scale" : self.relationshihp_font_scale, "family" : self.relationshihp_font_family}}, "login" : {"username" : self.login_username, "server" : self.login_server}, "janelas" : self.janelas }
        with open(self.path_config, "w") as f:
            f.write( json.dumps(self.config_) );
            return True;
        return False;

    def save(self):
        self.__save__();

    def getTamanhoJanela(self, nome, largura_padrao, altura_padrao):
        """Tamanho memorizado de uma janela, ou o padrao dela na primeira vez."""
        buffer = (self.janelas or {}).get(nome) or {};
        try:
            largura = int(buffer.get("w") or largura_padrao);
            altura  = int(buffer.get("h") or altura_padrao);
        except (TypeError, ValueError):
            return (largura_padrao, altura_padrao);
        # Config antiga ou editada a mao nao pode abrir uma janela invisivel.
        if largura < 200 or altura < 150:
            return (largura_padrao, altura_padrao);
        return (largura, altura);

    def setTamanhoJanela(self, nome, largura, altura, gravar=True):
        if self.janelas == None:
            self.janelas = {};
        atual = self.janelas.get(nome) or {};
        if atual.get("w") == int(largura) and atual.get("h") == int(altura):
            return False;   # nada mudou: nao reescreve o arquivo a toa
        self.janelas[nome] = {"w" : int(largura), "h" : int(altura)};
        if gravar:
            self.save();
        return True;

    def getFont(self):
        font = QFont()
        font.setPointSize(self.font_size);
        font.setFamily(self.font_family );
        return font;

    @staticmethod
    def instancia():
        return Configuration();