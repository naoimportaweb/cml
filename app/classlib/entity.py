import os, sys, inspect, json, uuid;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;
from classlib.relationship.entitys import Reference, TimeSlice
from classlib.relationship.relationship_info import RelatinshipInfo;

class Entity(ConnectObject):
    def __init__(self, id_=None):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self._dirt = False;
        self.etype = None;
        self.text = None;
        self.full_description = None;
        self.data_extra = "";
        self.references = [];
        self.time_slices = [];
        self.wikipedia = "";
        self.classification = [];
        self.small_label = None;
        self.start_date = None;
        self.end_date = None;
        self.format_date = "yyyy-MM-dd";
        self.default_url = None;
        self.icon = None;
        self.images = [];   # lista de {"id":..., "png_base64":...} — carregada sob demanda
        self.face = None;   # PNG do rosto em base64, ou None
        self.sub_etype_id = None;    # subtipo (so entidades Other), chave = md5(nome) no server
        self.sub_etype_name = None;  # nome do subtipo, para o combo
        self.subtype_face = None;    # rosto default do subtipo (badge no mapa), resolvido no load

    #def getWarnings(self, arr):
    #    if self.full_description == None or self.full_description.strip() == "":
    #        if self.etype == "link":
    #            arr.append( RelatinshipInfo.linkHasNoDescription( self ) );
    #    for reference in self.references:
    #        reference.getWarnings(arr);
    #def getErros(self, arr):
    #    if self.full_description == None or self.full_description.strip() == "":
    #        if self.etype != "link":
    #            arr.append( RelatinshipInfo.entityHasNoDescription( self ) );
    #    for reference in self.references:
    #        reference.getErros(arr);
    
    def __str__(self):
        return self.text;
    
    def getText(self):
        return self.text;
    
    def addClassification(self, classification_id, text_label, classification_item_id, text_label_choice, start_date, end_date, format_date):
        for buffer in self.classification:
            if buffer["id"] == classification_id + self.id:
                return False;
        self.classification.append({ "start_date" : self.start_date, "end_date" : self.end_date, "format_date" : self.format_date, "default_url" : self.default_url,  "entity_id" : self.id , "id" : classification_id + self.id, "classification_id" : classification_id, "text_label" : text_label, 
            "classification_item_id" : classification_item_id, "text_label_choice" : text_label_choice, "start_date" : start_date,  "end_date" : end_date, "format_date" : format_date });
        return True;
        
    def getDirt(self):
        return self._dirt;
    
    def addReference(self, title, link1, link2 = "", link3 = "", id_=None, descricao = ""):
        if link1 == "":
            return None;
        self.references.append( Reference( title, descricao, link1, link2, link3, id_=id_ ) );
        return self.references[-1];

    def addTimeSlice(self, text_label, date_start=None, date_end=None, id_=None):
        if text_label == "":
            return None;
        self.time_slices.append( TimeSlice( text_label, date_start, date_end, id_=id_ ) );
        return self.time_slices[-1];
        
    def toJson(self):
        return { "id" : self.id, "icon" : self.icon, "etype" : self.etype, "name" : self.text, "data_extra" : self.data_extra, "full_description" : self.full_description, "wikipedia" : self.wikipedia, "classification" : self.classification, "small_label" : self.small_label}

    # Imagens (endpoint dedicado Entity.load_images/save_images; base64 no banco). Carregadas
    # sob demanda quando o diagolo abre, nao no load do mapa, para nao pesar o mapa.
    def load_images(self):
        js = self.__execute__("Entity", "load_images", {"entity_id" : self.id});
        if js["status"] and js["return"] != None:
            self.images = js["return"].get("images") or [];
            face = js["return"].get("face") or "";
            self.face = face if face != "" else None;
        return self.images;

    def save_images(self):
        # Manda text_label/etype junto: o servidor garante a linha em entity (FK de
        # entity_image) com um upsert nao-destrutivo caso a caixa ainda nao tenha sido salva.
        return self.__execute__("Entity", "save_images", { "entity_id" : self.id,
            "text_label" : self.text or "", "etype" : self.etype or "",
            "images" : self.images, "face" : self.face or "" });

    def add_image(self, png_base64):
        img = { "id" : uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex, "png_base64" : png_base64 };
        self.images.append( img );
        return img;

    def remove_image(self, index):
        if index >= 0 and index < len( self.images ):
            self.images.pop( index );

    def set_face(self, png_base64):
        self.face = png_base64;

    def clear_face(self):
        self.face = None;

    # --- subtipo (Other) ---
    def load_subetypes(self):
        # Lista de {id, name, face_default} para o combo do subtipo. [] se falhar.
        js = self.__execute__("Entity", "load_subetypes", {});
        if js["status"] and js["return"] != None:
            return js["return"];
        return [];

    def set_subetype(self, name):
        # Define/limpa o subtipo desta entidade (name vazio = sem subtipo).
        self.sub_etype_name = name or None;
        return self.__execute__("Entity", "set_subetype", { "entity_id" : self.id,
            "text_label" : self.text or "", "etype" : self.etype or "", "sub_etype_name" : name or "" });

    def set_subetype_face(self, name, png_base64):
        # Define/remove o rosto default do SUBTIPO (compartilhado por todas as Others dele).
        return self.__execute__("Entity", "set_subetype_face", { "sub_etype_name" : name or "", "face" : png_base64 or "" });

    def create_subetype(self, name):
        # Cria um subtipo valido (tela global). Nao atribui a nenhuma entidade.
        return self.__execute__("Entity", "create_subetype", { "name" : name or "" });

    def delete_subetype(self, name):
        # Remove um subtipo valido e desvincula as entidades que o usavam.
        return self.__execute__("Entity", "delete_subetype", { "name" : name or "" });

    def toType(self, etype):
        js = self.__execute__("Entity", "to_type", {"type" : etype, "id" : self.id});
        if js["status"]:
            self.etype = etype;
            return js["return"];
        return False;

    def duplicate(self):
        # "Person"/"Organization"/"Other" sao os rotulos que uma caixa recem-criada carrega
        # antes de ser nomeada: procurar duplicata deles acharia todas as caixas em branco.
        if self.text == "Person" or self.text == "Organization" or self.text == "Other":
            return [];
        # O etype era fixo em "person" e o servidor filtra por ele (WHERE ent.etype = ?):
        # uma Organization duplicada nunca era encontrada, porque a busca procurava uma
        # PESSOA com aquele nome. A tela de merge abria vazia para tudo que nao fosse
        # pessoa — ou seja, para quase toda a base.
        js = self.__execute__("Entity", "duplicate", { "etype" : self.etype, "text_label" : self.text, "id" : self.id});
        if js["status"]:
            return js["return"];
        return False;
    
    def merge_to(self, old_entity_id):
        js = self.__execute__("Entity", "merge_to", { "old_entity_id" : old_entity_id, "new_entity_id" : self.id});
        if js["status"]:
            return js["return"];
        return False;

    @staticmethod
    def search(etype, text_label, proxy=False):
        filt = None;
        if etype == "":
            etype = "person";
        if etype.find(","):
            filt = etype.split(",");
            etype = "";
        else:
            filt = [ etype ];
        obj = ConnectObject();
        js = obj.__execute__("Entity", "search", {"etype" : etype, "text_label" : text_label});
        out = [];
        if js["status"]:
            for element in js["return"]:
                if element["etype"] in filt:
                    element["server"] = "local";
                    out.append( element );
        if proxy:
            js = obj.__proxy__("Entity", "search", {"etype" : etype, "text_label" : text_label});
            for arr in js["return"]:
                for element in arr["return"]:
                    if element["etype"] in filt:
                        element["server"] = arr["name"];
                        out.append( element );
        return out;
    
    @staticmethod    
    def fromJson( js):
        buffer = Entity(id_=js["id"]);
        buffer.id = js["id"];
        buffer.etype = js["etype"];
        buffer.text = js["text_label"];
        buffer.icon = js.get("icon");
        buffer.full_description = js["description"];
        buffer.default_url = js["default_url"];
        buffer.data_extra = js["data_extra"];
        buffer.wikipedia = js["wikipedia"];
        buffer.small_label = js["small_label"];
        if js.get("references") != None:
            for reference in js["references"]:
                buffer.addReference(reference["title"], reference["link1"], reference["link2"], reference["link3"], id_=reference["id"], descricao=reference["descricao"]);
        if js.get("classification") != None:
            for classification in js["classification"]:
                buffer.addClassification( classification["id"], classification["text_label"], classification["classification_item_id"], classification["text_label_choice"], classification["start_date"], classification["end_date"], classification["format_date"] );
        return buffer;
