import os, sys, inspect, datetime;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from PySide6.QtCore import Qt, QRectF, QDate;
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QFontMetrics;

from classlib.connectobject import ConnectObject;
from classlib.configuration import Configuration;
from classlib.timeline.map_event import MapEvent;
from classlib.timeline.timeline_event import (TimelineEvent, PRIORIDADE_ORIGEM, ROTULO_ORIGEM,
    COR_ORIGEM, ORIGEM_EVENTO, ORIGEM_REFERENCIA, ORIGEM_VINCULO, ORIGEM_CLASSIFICACAO,
    ORIGEM_ENTIDADE, ORIGEM_ELEMENTO);


class Timeline(ConnectObject):
    """Terceiro tipo de diagrama: a linha do tempo.

    E um DOCUMENTO como o mapa e o organograma — tem nome, e criado, salvo e aparece na
    lista de abrir (Map.search devolve os tres tipos). O que ele nao guarda e geometria: a
    posicao de um evento e a data dele, entao nao ha x/y para persistir.

    O mapa de origem e OPCIONAL e define os dois modos:
      com mapa  -> PROJETA as datas que ja existem nele (vinculo, classificacao, entidade,
                   caixa e referencia com data) e soma os eventos marcados;
      sem mapa  -> so os eventos marcados.

    O contrato com a casca (MdiMap/application) e o mesmo do OrganizationChart: draw(painter),
    getName(), getLocked() e save(). O layout mora aqui, e nao no engine, como no organograma:
    o engine so cuida de mouse, pixmap e menu."""

    # Geometria. Os "niveis" sao o empilhamento que evita sobreposicao: eventos que disputam
    # o mesmo pedaco do eixo sobem uma faixa em vez de escrever um por cima do outro.
    MARGEM_ESQ   = 80;
    MARGEM_DIR   = 90;
    TOPO         = 78;    # titulo (linha 1) + resumo e legenda (linha 2)
    RODAPE       = 30;
    ALT_BARRA    = 13;
    NIVEL_BARRA  = 31;    # rotulo + barra + folga
    NIVEL_MARCO  = 33;
    FOLGA_NIVEL  = 16;    # respiro horizontal entre dois eventos do mesmo nivel
    BASE_LARGURA = 1500;  # px do eixo com zoom 1
    ALT_MINIMA   = 420;
    # Quantas faixas empilhadas ainda se lê sem esforço. Acima disto a timeline vira uma
    # escada vertical e a noção de ritmo — que é o motivo de existir um eixo real — se perde.
    NIVEIS_CONFORTAVEIS = 12;
    ZOOMS_INICIAIS = [1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0];

    def __init__(self, id_=None):
        super().__init__();
        if id_ != None:
            self.id = id_;
        self.name = "New Timeline";
        self.keyword = "";
        self.diagram_relationship_id = None;   # mapa de origem (opcional)
        self.mapa = None;                      # MapRelationship carregado, quando ha origem
        self.nome_mapa = "";
        self.marcados = [];                    # MapEvent do banco
        self.eventos = [];                     # TimelineEvent desenhaveis (projecao + marcados)
        self.zoom = 1.0;
        self.folga_direita = self.MARGEM_DIR;
        self.selecionado = None;
        self.lock_list = [];      # o update_menus do application le isto
        self.locked = False;
        self.ultimo_erro = "";
        # Dominio temporal, preenchido pelo recalc.
        self.dom_ini = None; self.dom_fim = None;
        self.largura_eixo = self.BASE_LARGURA;
        self.eixo_y = self.TOPO;
        self.altura = self.ALT_MINIMA;
        self.niveis_barra = 0; self.niveis_marco = 0;
        self.ticks = [];

    # ------------------------------------------------------------------ contrato de diagrama
    def getName(self):
        return self.name;

    def getLocked(self):
        # A timeline nao trava: ela nao reescreve o mapa, e dois analistas podem ter a mesma
        # linha do tempo aberta sem se atrapalhar.
        return False;

    def create(self):
        js = self.__execute__("Timeline", "create", {"id" : self.id, "text_label" : self.name,
            "keyword" : self.keyword, "diagram_relationship_id" : self.diagram_relationship_id });
        if js.get("status"):
            return js["return"];
        self.ultimo_erro = js.get("error") or "O servidor recusou a criação.";
        return False;

    def exists(self, nome):
        js = self.__execute__("Timeline", "exists", {"id" : self.id, "text_label" : nome });
        if js.get("status"):
            return js["return"];
        return False;

    def save(self):
        """Salva o DOCUMENTO (nome, keyword, mapa de origem). Os eventos ja gravaram sozinhos
        quando foram marcados, e a projecao nao se salva — ela se recalcula."""
        js = self.__execute__("Timeline", "save", {"id" : self.id, "text_label" : self.name,
            "keyword" : self.keyword, "diagram_relationship_id" : self.diagram_relationship_id });
        if js.get("status"):
            return js["return"];
        self.ultimo_erro = js.get("error") or "O servidor recusou o save.";
        return False;

    def load(self, id):
        js = self.__execute__("Timeline", "load", {"id" : id });
        if not js.get("status") or js.get("return") == None:
            self.ultimo_erro = js.get("error") or "O servidor não devolveu a timeline.";
            return False;
        return self.load_data( js["return"] );

    def load_data(self, data):
        self.id = data["id"];
        self.name = data.get("text_label") or "";
        self.keyword = data.get("keyword") or "";
        self.diagram_relationship_id = data.get("diagram_relationship_id");
        self.marcados = [ MapEvent.from_row(self.id, linha) for linha in (data.get("events") or []) ];
        # O mapa de origem e carregado pelo caminho normal (MapRelationship.load): e la que
        # mora a leitura das datas do mapa, e duplicar isso no servidor criaria uma segunda
        # verdade. Timeline solta (sem mapa) simplesmente pula esta parte.
        self.mapa = None; self.nome_mapa = "";
        if self.diagram_relationship_id != None and str(self.diagram_relationship_id).strip() != "":
            from classlib.relationship.maprelationship import MapRelationship;
            mapa = MapRelationship();
            if mapa.load( self.diagram_relationship_id ):
                self.mapa = mapa;
                self.nome_mapa = mapa.name or "";
            else:
                # Mapa apagado ou servidor fora: a timeline ainda vale pelos eventos marcados.
                self.ultimo_erro = getattr(mapa, "ultimo_erro", "") or "";
        self.coletar();
        self.ajustar_zoom();
        return True;

    def recarregar(self):
        """Refaz tudo lendo do servidor de novo — o "Atualizar" do menu, para quando alguem
        mexeu nas datas em outra janela."""
        if self.id == None:
            return False;
        return self.load( self.id );

    # ------------------------------------------------------------------ coleta
    def coletar(self):
        """Varre o mapa e monta a lista de eventos. Cinco fontes de projecao + os eventos
        marcados. Deduplica no fim: a mesma data costuma aparecer em duas origens (a data da
        entidade repetida na caixa do mapa, tipicamente)."""
        brutos = [];
        if self.mapa != None:
            for element in getattr(self.mapa, "elements", []):
                brutos += self.__do_element__( element );
        brutos += self.__dos_eventos_marcados__();

        # Dedup por (titulo, inicio, fim), ficando a origem de maior prioridade.
        escolhidos = {};
        for evento in brutos:
            if evento == None:
                continue;
            chave = evento.chave();
            atual = escolhidos.get( chave );
            if atual == None or self.__prioridade__(evento) < self.__prioridade__(atual):
                escolhidos[ chave ] = evento;

        self.eventos = list( escolhidos.values() );
        # Ordem de leitura: por inicio, depois pelo mais curto, depois alfabetica.
        self.eventos.sort( key=lambda e: (e.inicio, (e.fim or e.inicio), e.titulo) );
        self.selecionado = None;
        return self.eventos;

    def __prioridade__(self, evento):
        if evento.origem in PRIORIDADE_ORIGEM:
            return PRIORIDADE_ORIGEM.index( evento.origem );
        return len(PRIORIDADE_ORIGEM);

    def __nome_element__(self, element):
        if element == None:
            return "";
        entidade = getattr(element, "entity", None);
        if entidade == None:
            return "";
        texto = entidade.getText() if hasattr(entidade, "getText") else entidade.text;
        return str(texto or "").strip();

    def __do_element__(self, element):
        eventos = [];
        entidade = getattr(element, "entity", None);
        if entidade == None:
            return eventos;
        nome = self.__nome_element__( element );

        if entidade.etype == "link":
            # Um evento por PONTA datada: as duas pontas de um vinculo podem ter periodos
            # diferentes (A entrou em 1998, B saiu em 2003) e achatar isso perderia dado.
            rotulo = self.__rotulo_vinculo__( element );
            for lentity in list(getattr(element, "from_entity", [])) + list(getattr(element, "to_entity", [])):
                eventos.append( TimelineEvent.novo( ORIGEM_VINCULO, nome, rotulo,
                    lentity.start_date, lentity.end_date, lentity.format_date, obj=element ) );
        else:
            eventos.append( TimelineEvent.novo( ORIGEM_ELEMENTO, nome, "no mapa",
                element.start_date, element.end_date, element.format_date, obj=element ) );
            eventos.append( TimelineEvent.novo( ORIGEM_ENTIDADE, nome, "",
                entidade.start_date, entidade.end_date, entidade.format_date, obj=element ) );
            for classificacao in (entidade.classification or []):
                titulo = nome + " — " + str(classificacao.get("text_label") or "") + ": " + str(classificacao.get("text_label_choice") or "");
                eventos.append( TimelineEvent.novo( ORIGEM_CLASSIFICACAO, titulo, nome,
                    classificacao.get("start_date"), classificacao.get("end_date"), classificacao.get("format_date"), obj=element ) );

        # Referencia com data e um ACONTECIMENTO — vale para entidade e para vinculo.
        for referencia in (entidade.references or []):
            eventos.append( TimelineEvent.novo( ORIGEM_REFERENCIA, referencia.title, nome,
                getattr(referencia, "start_date", None), getattr(referencia, "end_date", None),
                getattr(referencia, "format_date", None), obj=referencia ) );
        return eventos;

    def __rotulo_vinculo__(self, element):
        origens = [ self.__nome_element__(l.entity) for l in getattr(element, "from_entity", []) ];
        destinos = [ self.__nome_element__(l.entity) for l in getattr(element, "to_entity", []) ];
        origens  = [o for o in origens  if o != ""];
        destinos = [d for d in destinos if d != ""];
        if len(origens) == 0 and len(destinos) == 0:
            return "";
        return ", ".join(origens) + " → " + ", ".join(destinos);

    def __dos_eventos_marcados__(self):
        eventos = [];
        for marcado in self.marcados:
            eventos.append( TimelineEvent.novo( ORIGEM_EVENTO, marcado.text_label,
                marcado.entity_text_label, marcado.start_date, marcado.end_date,
                marcado.format_date, obj=marcado ) );
        return eventos;

    def add_marcado(self, evento):
        self.marcados.append( evento );
        self.coletar();

    def del_marcado(self, evento):
        self.marcados = [ m for m in self.marcados if m.id != evento.id ];
        self.coletar();

    def eventos_marcados(self):
        return [ e for e in self.eventos if e.origem == ORIGEM_EVENTO ];

    def ajustar_zoom(self):
        """Escolhe o zoom de abertura pelo empilhamento, não por um número fixo.

        Esticar o eixo separa eventos que disputavam a mesma faixa, e a pilha desmancha: nos
        dados reais do briefing EPRS (27 eventos em 3 meses e meio), zoom 1 dava 26 níveis e
        zoom 3 dá 11. Abrir sempre em 1 obrigaria a dar Ctrl+roda toda vez para conseguir ler.
        O usuário continua mandando no zoom depois disto."""
        if len(self.eventos) == 0:
            self.zoom = 1.0;
            return self.zoom;
        for tentativa in self.ZOOMS_INICIAIS:
            self.zoom = tentativa;
            self.recalc();
            if (self.niveis_barra + self.niveis_marco) <= self.NIVEIS_CONFORTAVEIS:
                break;
        return self.zoom;

    # ------------------------------------------------------------------ layout
    def __fonte__(self):
        return QFont( Configuration.instancia().relationshihp_font_family,
                      Configuration.instancia().relationshihp_font_size );

    def __fonte_titulo__(self):
        fonte = self.__fonte__();
        fonte.setPointSize( Configuration.instancia().relationshihp_font_size + 4 );
        fonte.setBold(True);
        return fonte;

    def tamanho(self):
        """(largura, altura) do desenho. O engine chama ANTES de criar o pixmap, por isso o
        recalc mede texto com QFontMetrics em vez de precisar de um QPainter pronto."""
        self.recalc();
        return ( int(self.MARGEM_ESQ + self.largura_eixo + self.folga_direita), int(self.altura) );

    def recalc(self):
        metrica = QFontMetrics( self.__fonte__() );
        self.largura_eixo = max( 400.0, self.BASE_LARGURA * self.zoom );

        if len(self.eventos) == 0:
            self.dom_ini = None; self.dom_fim = None;
            self.niveis_barra = 0; self.niveis_marco = 0;
            self.folga_direita = self.MARGEM_DIR;
            self.eixo_y = self.TOPO + 60;
            self.altura = self.ALT_MINIMA;
            self.ticks = [];
            return;

        self.__dominio__();
        self.ticks = self.__ticks__();

        # Empilhamento: dois "ocupadores", um para as barras (acima do eixo) e outro para os
        # marcos (abaixo). Cada nivel guarda ate onde ja foi escrito; o evento entra no
        # primeiro nivel livre. Como a lista esta ordenada por inicio, um passo basta.
        ocupado_barra = [];
        ocupado_marco = [];
        for evento in self.eventos:
            x_ini = self.x_da_data( evento.inicio );
            largura_texto = metrica.horizontalAdvance( evento.rotulo() );
            if evento.pontual():
                # De que LADO do pino escrever. Sempre à direita (como era) faz duas coisas
                # ruins quando os eventos se concentram no fim do período — que é o caso comum
                # numa investigação: o rótulo de um evento antigo atravessa a área dos
                # recentes, e o dos recentes estoura a borda. Escrevendo à esquerda quando o
                # evento está na parte direita do eixo, o texto cresce para o espaço vazio.
                # Cabe à direita? Cabe à esquerda? A escolha olha as DUAS margens: preferir
                # cegamente um lado joga o texto para fora do desenho quando o rótulo é longo
                # e o pino está perto daquela borda (foi o que aconteceu dos dois lados).
                espaco_direita = (self.MARGEM_ESQ + self.largura_eixo) - x_ini;
                espaco_esquerda = x_ini - self.MARGEM_ESQ;
                precisa = largura_texto + 20;
                if precisa <= espaco_direita and x_ini <= self.MARGEM_ESQ + self.largura_eixo * 0.55:
                    evento.rotulo_esquerda = False;      # metade inicial e cabe: lado natural
                elif precisa <= espaco_esquerda:
                    evento.rotulo_esquerda = True;       # cresce para o vazio à esquerda
                elif precisa <= espaco_direita:
                    evento.rotulo_esquerda = False;
                else:
                    # Não cabe inteiro em nenhum lado: fica no que tem mais espaço.
                    evento.rotulo_esquerda = bool( espaco_esquerda > espaco_direita );
                if evento.rotulo_esquerda:
                    inicio_ocupado = x_ini - largura_texto - 14;
                    fim_ocupado = x_ini + 10 + self.FOLGA_NIVEL;
                else:
                    inicio_ocupado = x_ini - 6;
                    fim_ocupado = x_ini + largura_texto + self.FOLGA_NIVEL + 12;
                nivel = self.__nivel_livre__( ocupado_marco, inicio_ocupado, fim_ocupado );
                evento.nivel = nivel;
                evento.x = inicio_ocupado;
                evento.w = max( 20, fim_ocupado - inicio_ocupado - self.FOLGA_NIVEL );
                evento.h = 24;
            else:
                x_fim = self.x_da_data( evento.fim );
                fim_ocupado = max( x_fim, x_ini + largura_texto ) + self.FOLGA_NIVEL;
                nivel = self.__nivel_livre__( ocupado_barra, x_ini, fim_ocupado );
                evento.nivel = nivel;
                evento.x = x_ini;
                evento.w = max( x_fim - x_ini, largura_texto, 4 );
                evento.h = self.ALT_BARRA + metrica.height() + 2;

        self.niveis_barra = len( ocupado_barra );
        self.niveis_marco = len( ocupado_marco );
        # Evento que comeca perto do fim do eixo escreve o rotulo para a direita e passava da
        # borda; a margem direita cresce ate caber o texto mais longo.
        extremo = 0;
        for lista in (ocupado_barra, ocupado_marco):
            for fim in lista:
                if fim > extremo:
                    extremo = fim;
        self.folga_direita = max( self.MARGEM_DIR, extremo - (self.MARGEM_ESQ + self.largura_eixo) + 20 );
        self.eixo_y = self.TOPO + max(1, self.niveis_barra) * self.NIVEL_BARRA + 10;
        self.altura = max( self.ALT_MINIMA,
            self.eixo_y + 34 + max(1, self.niveis_marco) * self.NIVEL_MARCO + self.RODAPE );

        # Agora que o eixo tem y, cada evento recebe o seu.
        for evento in self.eventos:
            if evento.pontual():
                evento.y = self.__y_marco__( evento.nivel ) - 12;
            else:
                evento.y = self.__y_barra__( evento.nivel ) - metrica.height() - 2;

    def __nivel_livre__(self, ocupado, inicio, fim):
        for i in range(len(ocupado)):
            if ocupado[i] <= inicio:
                ocupado[i] = fim;
                return i;
        ocupado.append( fim );
        return len(ocupado) - 1;

    def __y_barra__(self, nivel):
        # nivel 0 encosta no eixo; os seguintes sobem.
        return self.eixo_y - 12 - (nivel * self.NIVEL_BARRA) - self.ALT_BARRA;

    def __y_marco__(self, nivel):
        return self.eixo_y + 26 + (nivel * self.NIVEL_MARCO);

    def __dominio__(self):
        inicio = min( [e.inicio for e in self.eventos] );
        fim    = max( [ (e.fim or e.inicio) for e in self.eventos ] );
        if fim <= inicio:
            # Tudo no mesmo dia: sem um vao artificial, todos os eventos cairiam no mesmo x.
            inicio = inicio - datetime.timedelta(days=15);
            fim    = fim    + datetime.timedelta(days=15);
        folga = max( 1, int( (fim - inicio).days * 0.03 ) );
        self.dom_ini = inicio - datetime.timedelta(days=folga);
        self.dom_fim = fim    + datetime.timedelta(days=folga);

    def x_da_data(self, data):
        if self.dom_ini == None or data == None:
            return self.MARGEM_ESQ;
        span = (self.dom_fim - self.dom_ini).days;
        if span <= 0:
            return self.MARGEM_ESQ;
        return self.MARGEM_ESQ + ( (data - self.dom_ini).days * self.largura_eixo / float(span) );

    # ------------------------------------------------------------------ eixo
    # Candidatos de passo, do mais fino ao mais grosso. O escolhido e o primeiro que nao gera
    # mais marcas do que cabe — sem isso, um mapa que cobre 40 anos desenharia 14 mil ticks.
    PASSOS = [ ("dia",1), ("dia",2), ("dia",5), ("dia",10), ("dia",15),
               ("mes",1), ("mes",2), ("mes",3), ("mes",6),
               ("ano",1), ("ano",2), ("ano",5), ("ano",10), ("ano",20), ("ano",25),
               ("ano",50), ("ano",100), ("ano",200), ("ano",500), ("ano",1000) ];

    def __ticks__(self):
        span = max( 1, (self.dom_fim - self.dom_ini).days );
        alvo = max( 3, int( self.largura_eixo / 135 ) );
        for unidade, passo in self.PASSOS:
            if unidade == "dia":
                quantos = span / float(passo);
            elif unidade == "mes":
                quantos = (span / 30.44) / float(passo);
            else:
                quantos = (span / 365.25) / float(passo);
            if quantos <= alvo:
                return self.__gerar_ticks__( unidade, passo );
        return self.__gerar_ticks__( "ano", 1000 );

    def __gerar_ticks__(self, unidade, passo):
        ticks = [];
        if unidade == "ano":
            formato = "yyyy";
            ano = self.dom_ini.year - (self.dom_ini.year % passo);
            while ano <= self.dom_fim.year + passo:
                try:
                    data = datetime.date(ano, 1, 1);
                except ValueError:
                    break;
                if data >= self.dom_ini and data <= self.dom_fim:
                    ticks.append( (data, QDate(data.year, 1, 1).toString(formato)) );
                ano += passo;
        elif unidade == "mes":
            formato = "MM/yyyy";
            ano = self.dom_ini.year; mes = 1 + ((self.dom_ini.month - 1) // passo) * passo;
            while datetime.date(ano, mes, 1) <= self.dom_fim:
                data = datetime.date(ano, mes, 1);
                if data >= self.dom_ini:
                    ticks.append( (data, QDate(ano, mes, 1).toString(formato)) );
                mes += passo;
                while mes > 12:
                    mes -= 12; ano += 1;
        else:
            formato = "dd/MM/yyyy";
            data = self.dom_ini;
            while data <= self.dom_fim:
                ticks.append( (data, QDate(data.year, data.month, data.day).toString(formato)) );
                data = data + datetime.timedelta(days=passo);
        return ticks;

    # ------------------------------------------------------------------ desenho
    def draw(self, painter):
        self.recalc();
        largura_total = self.MARGEM_ESQ + self.largura_eixo + self.folga_direita;
        self.__draw_titulo__( painter, largura_total );
        if len(self.eventos) == 0:
            self.__draw_vazio__( painter );
            return;
        self.__draw_eixo__( painter );
        for evento in self.eventos:
            if evento.pontual():
                self.__draw_marco__( painter, evento );
            else:
                self.__draw_barra__( painter, evento );

    def __draw_titulo__(self, painter, largura_total):
        painter.setPen( QPen(Qt.black) );
        painter.setFont( self.__fonte_titulo__() );
        painter.drawText( QRectF(self.MARGEM_ESQ, 8, largura_total, 26), Qt.AlignLeft | Qt.AlignVCenter,
            self.name );

        painter.setFont( self.__fonte__() );
        painter.setPen( QPen(QColor(90, 90, 90)) );
        if len(self.eventos) > 0:
            periodo = str(self.eventos[0].inicio.year) + " – " + str( max([ (e.fim or e.inicio) for e in self.eventos ]).year );
            resumo = "%d eventos · %s" % (len(self.eventos), periodo);
        else:
            resumo = "nenhum evento";
        if self.nome_mapa != "":
            resumo = resumo + "  ·  mapa: " + self.nome_mapa;
        metrica_resumo = QFontMetrics( self.__fonte__() );
        painter.drawText( QRectF(self.MARGEM_ESQ, 42, metrica_resumo.horizontalAdvance(resumo) + 10, 18), Qt.AlignLeft | Qt.AlignVCenter, resumo );
        self.__legenda_x__ = self.MARGEM_ESQ + metrica_resumo.horizontalAdvance(resumo) + 30;
        self.__draw_legenda__( painter, largura_total );

    def __draw_legenda__(self, painter, largura_total):
        # So as origens presentes: legenda com item que nao aparece no desenho confunde.
        presentes = [];
        for origem in PRIORIDADE_ORIGEM:
            if len([e for e in self.eventos if e.origem == origem]) > 0:
                presentes.append( origem );
        metrica = QFontMetrics( self.__fonte__() );
        x = getattr(self, "__legenda_x__", self.MARGEM_ESQ + 320);
        for origem in presentes:
            rotulo = ROTULO_ORIGEM.get(origem, origem);
            painter.setPen( QPen(QColor(70,70,70)) );
            painter.setBrush( QBrush( COR_ORIGEM.get(origem, QColor(80,80,80)) ) );
            painter.drawRect( int(x), 46, 10, 10 );
            painter.setBrush( Qt.NoBrush );
            painter.drawText( QRectF(x + 15, 43, metrica.horizontalAdvance(rotulo) + 6, 16),
                Qt.AlignLeft | Qt.AlignVCenter, rotulo );
            x += 15 + metrica.horizontalAdvance(rotulo) + 18;

    def __draw_vazio__(self, painter):
        painter.setPen( QPen(QColor(120,120,120)) );
        painter.setFont( self.__fonte__() );
        if self.mapa != None:
            texto = ("Nenhuma data no mapa de origem.\n\n"
                     "A timeline projeta o que ja esta cadastrado no mapa: periodo do vinculo,\n"
                     "classificacao datada, datas da entidade e da caixa, e referencia com data\n"
                     "(acontecimento).\n\n"
                     "Voce tambem pode marcar um evento aqui: botao direito → Novo evento.");
        else:
            texto = ("Timeline vazia.\n\n"
                     "Esta timeline nao esta ligada a nenhum mapa, entao ela mostra apenas os\n"
                     "eventos que voce marcar: botao direito → Novo evento.\n\n"
                     "Para projetar as datas de um mapa, ligue um mapa de origem na Property.");
        painter.drawText( QRectF(self.MARGEM_ESQ, self.TOPO + 40, 760, 140), Qt.AlignLeft | Qt.AlignTop, texto );

    def __draw_eixo__(self, painter):
        x0 = self.MARGEM_ESQ;
        x1 = self.MARGEM_ESQ + self.largura_eixo;
        metrica = QFontMetrics( self.__fonte__() );
        painter.setFont( self.__fonte__() );

        # Guias verticais primeiro, bem claras: ficam ATRAS das barras e dos marcos.
        painter.setPen( QPen(QColor(228, 228, 232), 1, Qt.SolidLine) );
        topo_guia = self.TOPO;
        base_guia = self.altura - self.RODAPE;
        for data, _ in self.ticks:
            x = self.x_da_data( data );
            painter.drawLine( int(x), int(topo_guia), int(x), int(base_guia) );

        painter.setPen( QPen(Qt.black, 2) );
        painter.drawLine( int(x0), int(self.eixo_y), int(x1), int(self.eixo_y) );

        painter.setPen( QPen(QColor(60,60,60)) );
        for data, rotulo in self.ticks:
            x = self.x_da_data( data );
            painter.drawLine( int(x), int(self.eixo_y - 4), int(x), int(self.eixo_y + 4) );
            largura = metrica.horizontalAdvance( rotulo );
            painter.drawText( QRectF(x - largura/2 - 4, self.eixo_y + 6, largura + 8, 16),
                Qt.AlignCenter, rotulo );

    def __draw_barra__(self, painter, evento):
        cor = evento.cor();
        y_barra = self.__y_barra__( evento.nivel );
        x_ini = self.x_da_data( evento.inicio );
        x_fim = self.x_da_data( evento.fim );
        largura = max( 4, x_fim - x_ini );

        preenchimento = QColor( cor ); preenchimento.setAlpha( 90 );
        painter.setBrush( QBrush(preenchimento) );
        painter.setPen( QPen(cor, 3 if evento is self.selecionado else 1) );
        painter.drawRect( int(x_ini), int(y_barra), int(largura), self.ALT_BARRA );
        painter.setBrush( Qt.NoBrush );

        painter.setFont( self.__fonte__() );
        painter.setPen( QPen(Qt.black) );
        metrica = QFontMetrics( self.__fonte__() );
        rotulo = evento.rotulo();
        painter.drawText( QRectF(x_ini, y_barra - metrica.height() - 1,
            metrica.horizontalAdvance(rotulo) + 8, metrica.height() + 2),
            Qt.AlignLeft | Qt.AlignVCenter, rotulo );

    def __draw_marco__(self, painter, evento):
        cor = evento.cor();
        x = self.x_da_data( evento.inicio );
        y = self.__y_marco__( evento.nivel );

        # Haste do eixo ate o marco: sem ela, um marco no terceiro nivel parece solto.
        painter.setPen( QPen(QColor(170,170,170), 1, Qt.DotLine) );
        painter.drawLine( int(x), int(self.eixo_y), int(x), int(y) );

        painter.setBrush( QBrush(cor) );
        painter.setPen( QPen(cor.darker(140), 3 if evento is self.selecionado else 1) );
        painter.drawEllipse( int(x - 4), int(y - 4), 8, 8 );
        painter.setBrush( Qt.NoBrush );

        painter.setFont( self.__fonte__() );
        painter.setPen( QPen(Qt.black) );
        metrica = QFontMetrics( self.__fonte__() );
        rotulo = evento.rotulo();
        largura = metrica.horizontalAdvance(rotulo) + 8;
        if getattr(evento, "rotulo_esquerda", False):
            painter.drawText( QRectF(x - 8 - largura, y - metrica.height()/2, largura, metrica.height() + 2),
                Qt.AlignRight | Qt.AlignVCenter, rotulo );
        else:
            painter.drawText( QRectF(x + 8, y - metrica.height()/2, largura, metrica.height() + 2),
                Qt.AlignLeft | Qt.AlignVCenter, rotulo );

    # ------------------------------------------------------------------ mouse
    def findByXY(self, x, y):
        # De tras para frente: o ultimo desenhado e o que esta por cima.
        for evento in reversed( self.eventos ):
            if evento.x <= x and x <= evento.x + evento.w and evento.y <= y and y <= evento.y + evento.h:
                return evento;
        return None;
