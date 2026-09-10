import os, sys, inspect;

from PySide6.QtCore import (QDate, Qt)
from PySide6.QtWidgets import (QWidget, QComboBox, QDateEdit, QGridLayout, QLabel, QPushButton)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( os.path.dirname( CURRENTDIR ) );
sys.path.append( ROOT );

from classlib.configuration import Configuration;


class QPeriodo(QWidget):
    """Par de datas (inicio/fim) + formato de exibicao, no padrao que o DialogLinkEdit criou:
    cada data tem um botao Enable/Disable, porque "sem data" e um valor legitimo e diferente
    de "data de hoje".

    Existe para a referencia e o evento da timeline nao copiarem pela terceira vez as ~40
    linhas do link. Grava com aplicar(obj): o objeto so precisa ter start_date/end_date/
    format_date, que e a forma de TODO periodo neste modelo."""

    FORMATOS = ["yyyy-MM-dd", "dd/MM/yyyy", "MM/yyyy", "yyyy"];

    def __init__(self, parent=None, start_date=None, end_date=None, format_date=None,
                 rotulo_inicio="Data / início:", rotulo_fim="Fim (opcional):"):
        super().__init__(parent);
        formato = format_date or "yyyy-MM-dd";
        fonte = Configuration.instancia().getFont();

        self.start_date_flag = ( start_date != None and str(start_date).strip() != "" );
        self.end_date_flag   = ( end_date   != None and str(end_date).strip()   != "" );

        self.start_date = QDateEdit(self);
        self.end_date   = QDateEdit(self);
        self.start_date.setCalendarPopup(True);
        self.end_date.setCalendarPopup(True);
        self.__set_data__( self.start_date, start_date );
        self.__set_data__( self.end_date,   end_date );
        self.start_date.setDisplayFormat( formato );
        self.end_date.setDisplayFormat( formato );

        self.btn_start = QPushButton("Disable" if self.start_date_flag else "Enable");
        self.btn_end   = QPushButton("Disable" if self.end_date_flag   else "Enable");
        self.btn_start.setFocusPolicy(Qt.NoFocus);
        self.btn_end.setFocusPolicy(Qt.NoFocus);
        self.btn_start.clicked.connect( self.btn_start_click );
        self.btn_end.clicked.connect( self.btn_end_click );
        self.start_date.setVisible( self.start_date_flag );
        self.end_date.setVisible( self.end_date_flag );

        self.combo_format = QComboBox();
        for f in self.FORMATOS:
            self.combo_format.addItem(f);
        indice = self.combo_format.findText( formato, Qt.MatchFixedString );
        if indice >= 0:
            self.combo_format.setCurrentIndex( indice );
        self.combo_format.currentTextChanged.connect( self.combo_format_changed );

        lbl_inicio = QLabel(rotulo_inicio); lbl_inicio.setFont(fonte);
        lbl_fim    = QLabel(rotulo_fim);    lbl_fim.setFont(fonte);
        lbl_form   = QLabel("Formato:");    lbl_form.setFont(fonte);

        layout = QGridLayout();
        layout.setContentsMargins(0, 0, 0, 0);
        layout.addWidget(lbl_inicio,        0, 0); layout.addWidget(self.start_date,  0, 1); layout.addWidget(self.btn_start, 0, 2);
        layout.addWidget(lbl_fim,           1, 0); layout.addWidget(self.end_date,    1, 1); layout.addWidget(self.btn_end,   1, 2);
        layout.addWidget(lbl_form,          2, 0); layout.addWidget(self.combo_format, 2, 1);
        self.setLayout( layout );

    def __set_data__(self, campo, valor):
        # Aceita o que vem do banco ("1998-06-01" ou "1998-06-01 00:00:00") e cai em hoje
        # quando nao ha data — o campo esta escondido nesse caso, entao e so o ponto de
        # partida de quem clicar em Enable.
        texto = str(valor or "").strip().split(" ")[0];
        data = QDate.fromString( texto, "yyyy-MM-dd" );
        if not data.isValid():
            data = QDate.currentDate();
        campo.setDate( data );

    def btn_start_click(self):
        self.start_date_flag = not self.start_date_flag;
        self.start_date.setVisible( self.start_date_flag );
        self.btn_start.setText( "Disable" if self.start_date_flag else "Enable" );

    def btn_end_click(self):
        self.end_date_flag = not self.end_date_flag;
        self.end_date.setVisible( self.end_date_flag );
        self.btn_end.setText( "Disable" if self.end_date_flag else "Enable" );

    def combo_format_changed(self):
        self.start_date.setDisplayFormat( self.combo_format.currentText() );
        self.end_date.setDisplayFormat( self.combo_format.currentText() );

    def valores(self):
        """(start_date, end_date, format_date) — sempre "yyyy-MM-dd" no valor gravado; o
        formato escolhido e so exibicao, como no resto do sistema."""
        inicio = self.start_date.date().toString("yyyy-MM-dd") if self.start_date_flag else None;
        fim    = self.end_date.date().toString("yyyy-MM-dd")   if self.end_date_flag   else None;
        return ( inicio, fim, self.combo_format.currentText() );

    def aplicar(self, obj):
        inicio, fim, formato = self.valores();
        obj.start_date  = inicio;
        obj.end_date    = fim;
        obj.format_date = formato;
        return obj;
