import os, sys, inspect, uuid;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from classlib.connectobject import ConnectObject;


class MapEvent(ConnectObject):
    """Acontecimento marcado a mao numa timeline (tabela diagram_timeline_event).

    Pertence a TIMELINE, nao ao mapa: a mesma investigacao pode ter varias linhas do tempo
    com recortes diferentes, e o evento de uma nao deve poluir a outra. Grava na hora, por
    endpoint proprio (TimelineEvent.save) — nao no save do documento, que teria de mandar a
    lista inteira de volta a cada evento novo.

    A entidade associada e OPCIONAL: evento solto ("estouro da operacao") nao tem dono."""

    def __init__(self, diagram_timeline_id, id_=None):
        super().__init__();
        self.id = uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        if id_ != None:
            self.id = id_;
        self.diagram_timeline_id = diagram_timeline_id;
        self.entity_id = None;
        self.entity_text_label = "";     # so para exibir; vem do LEFT JOIN do Timeline.load
        self.text_label = "";
        self.description = "";
        self.start_date = None;
        self.end_date = None;
        self.format_date = "yyyy-MM-dd";

    @staticmethod
    def from_row(diagram_timeline_id, linha):
        """Monta o evento a partir da linha que veio no Timeline.load — os eventos chegam
        junto com o documento, entao nao ha uma segunda chamada so para busca-los."""
        evento = MapEvent(diagram_timeline_id, id_=linha["id"]);
        evento.entity_id         = linha.get("entity_id");
        evento.entity_text_label = linha.get("entity_text_label") or "";
        evento.text_label        = linha.get("text_label") or "";
        evento.description       = linha.get("description") or "";
        evento.start_date        = linha.get("start_date");
        evento.end_date          = linha.get("end_date");
        evento.format_date       = linha.get("format_date") or "yyyy-MM-dd";
        return evento;

    def save(self):
        js = self.__execute__("TimelineEvent", "save", {
            "id" : self.id,
            "diagram_timeline_id" : self.diagram_timeline_id,
            "entity_id" : self.entity_id,
            "text_label" : self.text_label,
            "description" : self.description,
            "start_date" : self.start_date,
            "end_date" : self.end_date,
            "format_date" : self.format_date });
        if js.get("status"):
            return js["return"];
        self.ultimo_erro = js.get("error") or "O servidor recusou o evento.";
        return False;

    def delete(self):
        js = self.__execute__("TimelineEvent", "delete", {
            "id" : self.id, "diagram_timeline_id" : self.diagram_timeline_id });
        if js.get("status"):
            return js["return"];
        self.ultimo_erro = js.get("error") or "O servidor recusou a remoção.";
        return False;
