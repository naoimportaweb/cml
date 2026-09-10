import os, sys, inspect;

from PySide6.QtCore import (QDate, Qt)
from PySide6.QtWidgets import (QDialog, QGridLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
                               QTextEdit, QVBoxLayout, QWidget)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from classlib.configuration import Configuration;
from classlib.timeline.map_event import MapEvent;
from view.ui.customvlayout import CustomVLayout;
from view.ui.qperiodo import QPeriodo;
from view.dialogentityload import DialogEntityLoad;


class DialogTimelineEvent(QDialog):
    """Marcar (ou editar) um acontecimento na timeline do mapa.

    Grava na hora, direto pelo MapEvent (TimelineEvent.save no servidor), em vez de esperar o
    save do documento. A entidade associada e opcional e vem do mesmo buscador que o resto do
    app usa (DialogEntityLoad, que devolve pelo callback entity_selected)."""

    def __init__(self, form, diagram_timeline_id, evento=None):
        super().__init__(form);
        self.form = form;
        self.gravou = False;
        self.removeu = False;
        # evento None = novo. O dono e a TIMELINE: a mesma investigacao pode ter varias
        # linhas do tempo, e o evento de uma nao deve aparecer na outra.
        self.evento = evento if evento != None else MapEvent( diagram_timeline_id );
        if evento == None:
            self.evento.start_date = QDate.currentDate().toString("yyyy-MM-dd");

        # O tamanho que o usuario deixou da ultima vez. Marcar evento e um trabalho de
        # digitar descricao: quem alargou a janela uma vez quer ela assim sempre.
        self.resize( *Configuration.instancia().getTamanhoJanela("timeline_event", 620, 480) );
        self.setWindowTitle("Evento da timeline");
        fonte = Configuration.instancia().getFont();

        layout_principal = QVBoxLayout();
        self.setLayout( layout_principal );
        layout = QGridLayout();

        lbl_titulo = QLabel("Título:"); lbl_titulo.setFont(fonte);
        self.txt_titulo = QLineEdit(); self.txt_titulo.setFont(fonte);
        self.txt_titulo.setText( self.evento.text_label );
        layout.addWidget(lbl_titulo, 0, 0); layout.addWidget(self.txt_titulo, 0, 1);

        lbl_entidade = QLabel("Entidade:"); lbl_entidade.setFont(fonte);
        self.txt_entidade = QLineEdit(); self.txt_entidade.setFont(fonte);
        self.txt_entidade.setReadOnly(True);
        self.txt_entidade.setText( self.evento.entity_text_label or "" );
        btn_entidade = QPushButton("Buscar…");
        btn_limpar   = QPushButton("Limpar");
        btn_entidade.clicked.connect( self.btn_entidade_click );
        btn_limpar.clicked.connect( self.btn_limpar_click );
        linha_entidade = CustomVLayout.widget_layout(self, [self.txt_entidade, btn_entidade, btn_limpar]);
        layout.addWidget(lbl_entidade, 1, 0); layout.addWidget(linha_entidade, 1, 1);

        self.periodo = QPeriodo(self, start_date=self.evento.start_date, end_date=self.evento.end_date,
                                format_date=self.evento.format_date);
        layout.addWidget(self.periodo, 2, 1);

        lbl_desc = QLabel("Descrição:"); lbl_desc.setFont(fonte);
        self.txt_descricao = QTextEdit(); self.txt_descricao.setFont(fonte);
        self.txt_descricao.setPlainText( self.evento.description or "" );
        layout.addWidget(lbl_desc, 3, 0); layout.addWidget(self.txt_descricao, 3, 1);

        widget = QWidget(); widget.setLayout( layout );
        layout_principal.addWidget( widget );

        btn_salvar = QPushButton("Salvar");
        btn_salvar.clicked.connect( self.btn_salvar_click );
        botoes = [btn_salvar];
        if evento != None:
            btn_remover = QPushButton("Remover");
            btn_remover.clicked.connect( self.btn_remover_click );
            botoes.append( btn_remover );
        btn_cancelar = QPushButton("Cancelar");
        btn_cancelar.clicked.connect( self.close );
        botoes.append( btn_cancelar );
        layout_principal.addWidget( CustomVLayout.widget_layout(self, botoes) );

    def closeEvent(self, event):
        # Grava no fechamento, e nao no resizeEvent: arrastar a borda dispara dezenas de
        # eventos por segundo, e cada um reescreveria o ~/.cml.json inteiro.
        Configuration.instancia().setTamanhoJanela("timeline_event", self.width(), self.height());
        super().closeEvent(event);

    # DialogEntityLoad devolve por callback: e o contrato que ele ja usa no resto do app.
    def btn_entidade_click(self):
        f = DialogEntityLoad(self);
        f.exec();

    def entity_selected(self, entity):
        self.evento.entity_id = entity["id"];
        self.evento.entity_text_label = entity["text_label"];
        self.txt_entidade.setText( entity["text_label"] );

    def btn_limpar_click(self):
        self.evento.entity_id = None;
        self.evento.entity_text_label = "";
        self.txt_entidade.setText("");

    def btn_salvar_click(self):
        titulo = self.txt_titulo.text().strip();
        if titulo == "":
            QMessageBox.information(self, "Evento", "Dê um título ao evento.");
            return;
        inicio, fim, formato = self.periodo.valores();
        if inicio == None and fim == None:
            # Sem data o evento nao teria onde ser desenhado — e o unico campo insubstituivel.
            QMessageBox.information(self, "Evento", "Um evento precisa de pelo menos uma data.");
            return;
        self.evento.text_label = titulo;
        self.evento.description = self.txt_descricao.toPlainText();
        self.periodo.aplicar( self.evento );
        if self.evento.save():
            self.gravou = True;
            self.close();
        else:
            QMessageBox.warning(self, "Evento", "Não foi possível gravar o evento:\n\n"
                + str(getattr(self.evento, "ultimo_erro", "") or "erro desconhecido"));

    def btn_remover_click(self):
        resposta = QMessageBox.question(self, "Remover",
            "Remover o evento \"%s\" desta timeline?" % self.evento.text_label);
        if resposta != QMessageBox.Yes:
            return;
        if self.evento.delete():
            self.removeu = True;
            self.close();
        else:
            QMessageBox.warning(self, "Evento", "Não foi possível remover o evento:\n\n"
                + str(getattr(self.evento, "ultimo_erro", "") or "erro desconhecido"));
