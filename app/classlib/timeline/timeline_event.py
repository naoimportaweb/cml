import os, sys, inspect, datetime;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from PySide6.QtCore import QDate;
from PySide6.QtGui import QColor;

# De onde cada data pode vir. Cinco sao PROJECAO — a timeline nao inventa data nenhuma, so
# desenha o que ja estava cadastrado — e a sexta (evento) e o que o analista marca a mao.
# Manter cor/rotulo aqui (e nao no engine) evita que a legenda e o desenho discordem.
ORIGEM_EVENTO        = "evento";         # diagram_relationship_event (marcado na timeline)
ORIGEM_REFERENCIA    = "referencia";     # diagram_relationship_element_reference.start_date
ORIGEM_VINCULO       = "vinculo";        # diagram_relationship_link.start_date/end_date
ORIGEM_CLASSIFICACAO = "classificacao";  # entity_classification_item.start_date/end_date
ORIGEM_ENTIDADE      = "entidade";       # entity.start_date/end_date (a entidade global)
ORIGEM_ELEMENTO      = "elemento";       # diagram_relationship_element.start_date/end_date

ROTULO_ORIGEM = {
    ORIGEM_EVENTO        : "Evento marcado",
    ORIGEM_REFERENCIA    : "Acontecimento (referência)",
    ORIGEM_VINCULO       : "Vínculo",
    ORIGEM_CLASSIFICACAO : "Classificação",
    ORIGEM_ENTIDADE      : "Entidade",
    ORIGEM_ELEMENTO      : "Caixa no mapa",
};

# Ordem de preferencia quando duas origens dizem a MESMA coisa (mesmo titulo e mesmas datas):
# fica a mais especifica. A caixa do mapa costuma repetir a data da entidade, e um evento
# marcado a mao ganha de qualquer projecao (foi o analista que escreveu).
PRIORIDADE_ORIGEM = [ORIGEM_EVENTO, ORIGEM_REFERENCIA, ORIGEM_VINCULO, ORIGEM_CLASSIFICACAO,
                     ORIGEM_ENTIDADE, ORIGEM_ELEMENTO];

COR_ORIGEM = {
    ORIGEM_EVENTO        : QColor(214, 140,  20),   # ambar: o que foi marcado a mao salta
    ORIGEM_REFERENCIA    : QColor( 42, 132, 148),
    ORIGEM_VINCULO       : QColor(196,  60,  60),   # vermelho: e a cor da seta do vinculo no mapa
    ORIGEM_CLASSIFICACAO : QColor( 92,  92, 176),
    ORIGEM_ENTIDADE      : QColor( 52, 138,  92),
    ORIGEM_ELEMENTO      : QColor(104, 122, 142),
};


def parse_data(valor):
    """Converte o que vem do banco em datetime.date, ou None quando nao ha data utilizavel.

    Tolerante de proposito: o mesmo campo chega como None, "", "0000-00-00" (zero date do
    MySQL), "1998-06-01" ou "1998-06-01 00:00:00" dependendo de onde foi gravado. Data
    invalida vira None (o evento simplesmente nao entra) em vez de estourar no meio do
    desenho do mapa inteiro."""
    if valor == None:
        return None;
    texto = str(valor).strip();
    if texto == "" or texto.startswith("0000"):
        return None;
    texto = texto.split(" ")[0].split("T")[0];
    partes = texto.split("-");
    if len(partes) != 3:
        return None;
    try:
        ano = int(partes[0]); mes = int(partes[1]); dia = int(partes[2]);
        if ano <= 0 or mes <= 0 or dia <= 0:
            return None;
        return datetime.date(ano, mes, dia);
    except Exception:
        return None;


class TimelineEvent():
    """Uma linha da timeline: um periodo (barra) ou uma data unica (marco).

    A geometria (x/y/w/h/nivel) e preenchida pelo recalc da Timeline e lida pelo engine —
    mesmo arranjo do MapRelationshipBox, que tambem guarda a propria caixa."""

    def __init__(self, origem, titulo, subtitulo, inicio, fim, format_date=None, obj=None):
        self.origem = origem;
        self.titulo = titulo;
        self.subtitulo = subtitulo or "";
        self.inicio = inicio;       # datetime.date, sempre preenchido
        self.fim = fim;             # datetime.date ou None (marco)
        self.format_date = format_date or "yyyy-MM-dd";
        self.obj = obj;             # element/entidade de origem, para o tooltip
        self.x = 0; self.y = 0; self.w = 0; self.h = 0; self.nivel = 0;

    @staticmethod
    def novo(origem, titulo, subtitulo, inicio_bruto, fim_bruto, format_date=None, obj=None):
        """Fabrica que aplica as regras de sanidade das datas. Devolve None quando o registro
        nao tem data nenhuma — que e o caso da MAIORIA das entidades, entao isto e o filtro
        que decide o que aparece na timeline."""
        inicio = parse_data(inicio_bruto);
        fim    = parse_data(fim_bruto);
        if inicio == None and fim == None:
            return None;
        if inicio == None:
            # So o fim preenchido: nao da para desenhar barra sem inicio, entao vira marco.
            inicio = fim; fim = None;
        if fim != None and fim < inicio:
            # Cadastro invertido: desenhar assim daria barra de largura negativa.
            inicio, fim = fim, inicio;
        titulo = str(titulo or "").strip();
        if titulo == "":
            titulo = "(sem nome)";
        return TimelineEvent(origem, titulo, subtitulo, inicio, fim, format_date=format_date, obj=obj);

    def pontual(self):
        return self.fim == None or self.fim == self.inicio;

    def chave(self):
        """Identidade para deduplicar: o MESMO fato costuma estar em duas origens (a data da
        entidade repetida na caixa do mapa, por exemplo)."""
        return (self.titulo, self.inicio, self.fim);

    def data_texto(self, data):
        if data == None:
            return "";
        # format_date e um formato Qt (o mesmo que os QDateEdit dos dialogos usam), entao
        # quem escolheu "dd/MM/yyyy" naquele cadastro ve "dd/MM/yyyy" aqui tambem.
        return QDate(data.year, data.month, data.day).toString(self.format_date);

    def periodo_texto(self):
        if self.pontual():
            return self.data_texto(self.inicio);
        return self.data_texto(self.inicio) + " → " + self.data_texto(self.fim);

    def duracao_texto(self):
        if self.pontual():
            return "";
        dias = (self.fim - self.inicio).days;
        if dias >= 730:
            return "%d anos" % int(dias / 365.25);
        if dias >= 60:
            return "%d meses" % int(dias / 30.44);
        return "%d dias" % dias;

    def cor(self):
        return COR_ORIGEM.get( self.origem, QColor(80, 80, 80) );

    def editavel(self):
        """Projecao nao se edita na timeline: a data mora no vinculo/classificacao/referencia
        e e la que se muda. So o evento marcado a mao tem linha propria para alterar."""
        return self.origem == ORIGEM_EVENTO and self.obj != None;

    def rotulo(self):
        """Texto de uma linha, usado tanto para desenhar quanto para medir a largura que o
        evento ocupa no nivel (o rotulo costuma ser mais largo que a propria barra)."""
        return self.titulo + " · " + self.periodo_texto();

    def tooltip(self):
        linhas = [ self.titulo ];
        if self.subtitulo != "":
            linhas.append( self.subtitulo );
        periodo = self.periodo_texto();
        if self.duracao_texto() != "":
            periodo = periodo + "  (" + self.duracao_texto() + ")";
        linhas.append( periodo );
        linhas.append( "Origem: " + ROTULO_ORIGEM.get(self.origem, self.origem) );
        # Evento marcado e referencia carregam descricao; ela e o que explica o acontecimento.
        descricao = str( getattr(self.obj, "description", "") or "" ).strip();
        if descricao != "":
            if len(descricao) > 300:
                descricao = descricao[:300] + "…";
            linhas.append( "" );
            linhas.append( descricao );
        return "\n".join( linhas );

    def __str__(self):
        return self.rotulo();
