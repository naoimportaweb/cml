import os, sys, inspect, json, base64, hashlib;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;

class Document(ConnectObject):
    # O servidor recusa acima disto (Document::MAX_BYTES). Conferir aqui evita subir
    # 30MB pela rede so para receber um erro do outro lado.
    MAX_BYTES = 33554432;

    def __init__(self, id_=None):
        super().__init__();
        self.id = id_;
        self.sha256 = None;
        self.title = None;
        self.bytes = 0;

    @staticmethod
    def __ler__(path):
        with open(path, "rb") as f:
            return f.read();

    def upload_file(self, path, diagram_relationship_id, title=None, description=None, origem="upload"):
        conteudo = Document.__ler__(path);
        if len(conteudo) == 0:
            raise Exception("Arquivo vazio.");
        if len(conteudo) > Document.MAX_BYTES:
            raise Exception("Arquivo tem " + str(len(conteudo)) + " bytes; o limite é " + str(Document.MAX_BYTES) + ".");
        if conteudo[:5] != b"%PDF-":
            raise Exception("O arquivo não é um PDF.");
        return self.upload_bytes(conteudo, diagram_relationship_id,
                                 title if title != None else os.path.basename(path),
                                 description, origem);

    def upload_bytes(self, conteudo, diagram_relationship_id, title, description=None, origem="upload"):
        js = self.__execute__("Document", "upload", {
            "diagram_relationship_id" : diagram_relationship_id,
            "title" : title,
            "description" : description,
            "origem" : origem,
            "base64" : base64.b64encode(conteudo).decode()
        });
        if js["status"]:
            self.id     = js["return"]["id"];
            self.sha256 = js["return"]["sha256"];
            self.bytes  = js["return"]["bytes"];
            return js["return"];
        return False;

    def download_to(self, document_id, path):
        js = self.__execute__("Document", "download", {"document_id" : document_id});
        if not js["status"]:
            return False;
        conteudo = base64.b64decode( js["return"]["base64"] );
        with open(path, "wb") as f:
            f.write(conteudo);
        return {"path" : path, "bytes" : len(conteudo), "title" : js["return"]["title"]};

    def link_map(self, document_id, diagram_relationship_id):
        js = self.__execute__("Document", "link_map", {
            "document_id" : document_id, "diagram_relationship_id" : diagram_relationship_id});
        return js["return"] if js["status"] else False;

    def unlink_map(self, document_id, diagram_relationship_id):
        js = self.__execute__("Document", "unlink_map", {
            "document_id" : document_id, "diagram_relationship_id" : diagram_relationship_id});
        return js["return"] if js["status"] else False;

    @staticmethod
    def list_by_map(diagram_relationship_id):
        obj = ConnectObject();
        js = obj.__execute__("Document", "list_by_map", {"diagram_relationship_id" : diagram_relationship_id});
        if js["status"]:
            return js["return"];
        return [];
