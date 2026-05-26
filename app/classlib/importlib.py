import os, sys, inspect, json, uuid, traceback;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;

class ImportLib(ConnectObject):
    def __init__(self, id_=None):
        super().__init__();
    def import_entitys(self, paths):
        columns = ["text_label", "small_label", "description", "etype", "sub_etype", "wikipedia",  "default_url", "icon"];
        try:
            lista_envio = [];
            for path in paths:
                element = json.loads(open(path.strip(), "r").read());
                for column in columns:
                    if element.get(column) == None:
                        raise ValueError("Falta a coluna: " + column);
                lista_envio.append(element);
            js = self.__execute__("Entity", "import_all", { "entitys" : lista_envio });
            if js["status"]:
                return js["return"];
        except:
            traceback.print_exc();
        return False;
