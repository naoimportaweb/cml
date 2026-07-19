import os, sys, inspect;

from PySide6.QtCore import Qt;
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QLineEdit, QListWidget, QFileDialog, QMessageBox, QFrame);

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from classlib.configuration import Configuration;
from classlib.entity import Entity;
from view.ui.qimages import png_base64_from_file, pixmap_from_base64, FILTRO;


class DialogSubtypes(QDialog):
    """Tela GLOBAL de sub-tipos (nivel banco): cadastrar/remover sub-tipos validos e definir
    o rosto default de cada um. Nao esta ligada a nenhuma entidade — usa uma Entity() so como
    transporte (os metodos de sub-tipo nao dependem do id da entidade)."""
    def __init__(self, form):
        super().__init__(form);
        self.api = Entity();   # so para chamar os endpoints de sub-tipo
        self.face_por_nome = {};
        nWidth = 640; nHeight = 460;
        if form != None:
            self.setGeometry(form.x() + form.width()//2 - nWidth//2, form.y() + form.height()//2 - nHeight//2, nWidth, nHeight);
        self.setWindowTitle("Sub-tipos (Other)");

        layout = QVBoxLayout();
        layout.addWidget( QLabel("Sub-tipos válidos para entidades <b>Other</b> — valem para todo o servidor.") );

        corpo = QHBoxLayout();
        self.lista = QListWidget();
        self.lista.setMaximumWidth( 240 );
        self.lista.currentRowChanged.connect( self.__preview__ );
        corpo.addWidget( self.lista );

        direita = QVBoxLayout();
        direita.addWidget( QLabel("<b>Rosto default</b> do sub-tipo selecionado") );
        self.lbl_face = QLabel("Selecione um sub-tipo.");
        self.lbl_face.setAlignment( Qt.AlignCenter );
        self.lbl_face.setMinimumSize( 220, 220 );
        self.lbl_face.setFrameShape( QFrame.StyledPanel );
        direita.addWidget( self.lbl_face );
        self.btn_set = QPushButton("Definir rosto default…");
        self.btn_del_face = QPushButton("Remover rosto default");
        for b in (self.btn_set, self.btn_del_face):
            b.setFont( Configuration.instancia().getFont() );
            direita.addWidget( b );
        self.btn_set.clicked.connect( self.__set_face__ );
        self.btn_del_face.clicked.connect( self.__del_face__ );
        direita.addStretch();
        corpo.addLayout( direita, 1 );
        layout.addLayout( corpo );

        layout.addWidget( self.__separador__() );
        linha = QHBoxLayout();
        self.txt_novo = QLineEdit();
        self.txt_novo.setPlaceholderText("novo sub-tipo (ex.: exe, elf, sh, js)");
        self.txt_novo.setFont( Configuration.instancia().getFont() );
        btn_add = QPushButton("Adicionar");
        btn_rem = QPushButton("Remover sub-tipo");
        for b in (btn_add, btn_rem):
            b.setFont( Configuration.instancia().getFont() );
        btn_add.clicked.connect( self.__add__ );
        btn_rem.clicked.connect( self.__remove__ );
        linha.addWidget( self.txt_novo ); linha.addWidget( btn_add ); linha.addStretch(); linha.addWidget( btn_rem );
        layout.addLayout( linha );

        btn_fechar = QPushButton("Fechar");
        btn_fechar.clicked.connect( self.close );
        rodape = QHBoxLayout(); rodape.addStretch(); rodape.addWidget( btn_fechar );
        layout.addLayout( rodape );

        self.setLayout( layout );
        self.__carregar__();

    def __separador__(self):
        l = QFrame(); l.setFrameShape( QFrame.HLine ); l.setFrameShadow( QFrame.Sunken ); return l;

    def __carregar__(self):
        self.face_por_nome = {};
        self.lista.clear();
        try:
            subs = self.api.load_subetypes();
        except Exception as e:
            QMessageBox.warning(self, "Falha", "Não foi possível carregar os sub-tipos:\n" + str(e));
            subs = [];
        for s in subs:
            nome = s.get("name") or "";
            self.face_por_nome[ nome ] = s.get("face_default");
            self.lista.addItem( nome );
        self.lbl_face.clear(); self.lbl_face.setText("Selecione um sub-tipo.");

    def __nome_sel__(self):
        it = self.lista.currentItem();
        return it.text() if it != None else "";

    def __preview__(self, row):
        nome = self.__nome_sel__();
        face = self.face_por_nome.get( nome );
        if face:
            pix = pixmap_from_base64( face );
            self.lbl_face.setPixmap( pix.scaled( self.lbl_face.width(), self.lbl_face.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation ) );
        else:
            self.lbl_face.clear();
            self.lbl_face.setText("Sem rosto default." if nome != "" else "Selecione um sub-tipo.");

    def __ok__(self, js):
        if not js or not js.get("status"):
            QMessageBox.warning(self, "Falha", "O servidor não confirmou a operação.");
            return False;
        return True;

    def __add__(self):
        nome = self.txt_novo.text().strip();
        if nome == "":
            return;
        if nome in self.face_por_nome:
            QMessageBox.information(self, "Sub-tipo", "Esse sub-tipo já existe.");
            return;
        if self.__ok__( self.api.create_subetype( nome ) ):
            self.txt_novo.clear();
            self.__carregar__();

    def __remove__(self):
        nome = self.__nome_sel__();
        if nome == "":
            return;
        if QMessageBox.question(self, "Remover", "Remover o sub-tipo '%s'? As entidades que o usavam ficam sem sub-tipo." % nome) != QMessageBox.Yes:
            return;
        if self.__ok__( self.api.delete_subetype( nome ) ):
            self.__carregar__();

    def __set_face__(self):
        nome = self.__nome_sel__();
        if nome == "":
            QMessageBox.information(self, "Sub-tipo", "Selecione um sub-tipo primeiro.");
            return;
        path, _ = QFileDialog.getOpenFileName(self, "Rosto default de '%s'" % nome, "", FILTRO);
        if path == "":
            return;
        b64 = png_base64_from_file( path );
        if b64 == None:
            QMessageBox.warning(self, "Imagem inválida", "Não foi possível ler esse arquivo como imagem.");
            return;
        if self.__ok__( self.api.set_subetype_face( nome, b64 ) ):
            self.face_por_nome[ nome ] = b64;
            self.__preview__( self.lista.currentRow() );

    def __del_face__(self):
        nome = self.__nome_sel__();
        if nome == "":
            return;
        if self.__ok__( self.api.set_subetype_face( nome, None ) ):
            self.face_por_nome[ nome ] = None;
            self.__preview__( self.lista.currentRow() );
