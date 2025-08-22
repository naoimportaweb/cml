import os, sys, inspect, json, uuid, traceback;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;

class ImportLib(ConnectObject):
    def __init__(self, id_=None):
        super().__init__();
    def import_entitys(self, path):
        columns = ["text_label", "small_label", "description", "etype", "sub_etype", "wikipedia",  "default_url", "icon"];
        try:
            elements = json.loads(open(path, "r").read());
            for element in elements:
                for column in columns:
                    if element.get(column) == None:
                        raise ValueError("Falta a coluna: " + column);
            js = self.__execute__("Entity", "import_all", { "entitys" : elements });
            if js["status"]:
                return js["return"];
        except:
            traceback.print_exc();
        return False;
