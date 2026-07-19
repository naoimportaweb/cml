import os, sys, inspect;

from PySide6.QtCore import Qt, QByteArray, QBuffer;
from PySide6.QtGui import QImage, QPixmap, QPainter;
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QFileDialog, QMessageBox, QListWidget, QFrame);

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(os.path.dirname( CURRENTDIR ));
sys.path.append( ROOT );

from classlib.configuration import Configuration;

# Reduz TODA imagem antes de gravar (o usuario autorizou perder qualidade): o base64 vai no
# banco e viaja no envelope RPC, entao imagens grandes (fotos/screenshots de varios MB)
# estouravam tamanho. Limita o maior lado e salva como JPEG com qualidade reduzida.
MAX_LADO = 800;
QUALIDADE = 72;   # qualidade JPEG (0-100); menor = arquivo menor

# Formatos que o QFileDialog oferece para abrir. O Qt le todos e o cliente converte para PNG.
FILTRO = "Imagens (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff);;Todos os arquivos (*)";


def png_base64_from_file(path, max_lado=MAX_LADO):
    """Le uma imagem de QUALQUER formato suportado pelo Qt e devolve base64 (str) reduzida.

    Devolve None se o arquivo nao for uma imagem valida. Reduz o tamanho (maior lado <=
    max_lado) e salva como JPEG com qualidade reduzida — bem menor que PNG para fotos. O nome
    e legado ('png_'); a saida hoje e JPEG, mas os decodificadores auto-detectam o formato,
    entao os PNGs ja gravados continuam funcionando.
    """
    img = QImage(path);
    if img.isNull():
        return None;
    if max_lado and (img.width() > max_lado or img.height() > max_lado):
        img = img.scaled(max_lado, max_lado, Qt.KeepAspectRatio, Qt.SmoothTransformation);
    # JPEG nao tem canal alpha: achata sobre branco para nao virar fundo preto.
    if img.hasAlphaChannel():
        fundo = QImage(img.size(), QImage.Format_RGB32);
        fundo.fill(Qt.white);
        p = QPainter(fundo); p.drawImage(0, 0, img); p.end();
        img = fundo;
    ba = QByteArray();
    buf = QBuffer(ba);
    buf.open(QBuffer.WriteOnly);
    img.save(buf, "JPEG", QUALIDADE);
    buf.close();
    return bytes(ba.toBase64()).decode("ascii");


def pixmap_from_base64(b64):
    """QPixmap a partir de base64 (para os previews). Sem dica de formato: auto-detecta, entao
    le tanto o JPEG novo quanto os PNG ja gravados."""
    ba = QByteArray.fromBase64( QByteArray(b64.encode("ascii")) );
    pix = QPixmap();
    pix.loadFromData(ba);
    return pix;


class QImages(QWidget):
    """Painel de imagens de uma entidade, embutivel numa aba (estilo QBot).

    with_face controla a secao de rosto (vinculo -> etype 'link' nao tem rosto). Carrega do
    servidor no __init__ e grava na hora a cada alteracao (Entity.save_images), desacoplado
    do save do mapa.
    """
    def __init__(self, parent, entity, with_face=True):
        super().__init__(parent);
        self.entity = entity;
        self.with_face = with_face;
        try:
            self.entity.load_images();
        except Exception as e:
            # Sem servidor/tabela a lista fica vazia; o dialogo nao deve quebrar por isso.
            print("QImages: falha ao carregar imagens:", e);

        layout = QVBoxLayout();

        # --- lista de imagens + preview ---
        btn_add = QPushButton("Add image");
        btn_del = QPushButton("Remove image");
        btn_add.setFont( Configuration.instancia().getFont() );
        btn_del.setFont( Configuration.instancia().getFont() );
        btn_add.clicked.connect( self.btn_add_click );
        btn_del.clicked.connect( self.btn_del_click );
        linha_btn = QHBoxLayout();
        linha_btn.addWidget( btn_add );
        linha_btn.addWidget( btn_del );
        linha_btn.addStretch();
        layout.addLayout( linha_btn );

        corpo = QHBoxLayout();
        self.lista = QListWidget();
        self.lista.setMaximumWidth( 220 );
        self.lista.currentRowChanged.connect( self.__preview__ );
        corpo.addWidget( self.lista );
        self.lbl_preview = QLabel("Sem imagem selecionada.");
        self.lbl_preview.setAlignment( Qt.AlignCenter );
        self.lbl_preview.setMinimumSize( 260, 260 );
        self.lbl_preview.setFrameShape( QFrame.StyledPanel );
        corpo.addWidget( self.lbl_preview, 1 );
        layout.addLayout( corpo );

        # --- rosto ---
        if self.with_face:
            layout.addWidget( self.__separador__() );
            lbl_titulo = QLabel("<b>Rosto</b> (imagem principal, 1 por objeto)");
            layout.addWidget( lbl_titulo );
            face_corpo = QHBoxLayout();
            self.lbl_face = QLabel();
            self.lbl_face.setAlignment( Qt.AlignCenter );
            self.lbl_face.setMinimumSize( 140, 140 );
            self.lbl_face.setMaximumWidth( 200 );
            self.lbl_face.setFrameShape( QFrame.StyledPanel );
            face_corpo.addWidget( self.lbl_face );
            face_botoes = QVBoxLayout();
            btn_face_file = QPushButton("Definir rosto…");
            btn_face_sel  = QPushButton("Usar imagem selecionada");
            btn_face_del  = QPushButton("Remover rosto");
            for b in (btn_face_file, btn_face_sel, btn_face_del):
                b.setFont( Configuration.instancia().getFont() );
                face_botoes.addWidget( b );
            face_botoes.addStretch();
            btn_face_file.clicked.connect( self.btn_face_file_click );
            btn_face_sel.clicked.connect( self.btn_face_sel_click );
            btn_face_del.clicked.connect( self.btn_face_del_click );
            face_corpo.addLayout( face_botoes );
            face_corpo.addStretch();
            layout.addLayout( face_corpo );

        self.setLayout( layout );
        self.__lista_load__();
        if self.with_face:
            self.__face_load__();

    def __separador__(self):
        linha = QFrame();
        linha.setFrameShape( QFrame.HLine );
        linha.setFrameShadow( QFrame.Sunken );
        return linha;

    # ---- lista ----
    def __lista_load__(self):
        self.lista.clear();
        for i in range(len( self.entity.images )):
            self.lista.addItem( "Imagem %d" % (i + 1) );
        self.lbl_preview.clear();
        self.lbl_preview.setText("Sem imagem selecionada.");

    def __preview__(self, row):
        if row < 0 or row >= len( self.entity.images ):
            self.lbl_preview.setText("Sem imagem selecionada.");
            return;
        pix = pixmap_from_base64( self.entity.images[row]["png_base64"] );
        self.lbl_preview.setPixmap( pix.scaled( self.lbl_preview.width(), self.lbl_preview.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation ) );

    def btn_add_click(self):
        path, _ = QFileDialog.getOpenFileName(self, "Escolher imagem", "", FILTRO);
        if path == "":
            return;
        b64 = png_base64_from_file( path );
        if b64 == None:
            QMessageBox.warning(self, "Imagem inválida", "Não foi possível ler esse arquivo como imagem.");
            return;
        self.entity.add_image( b64 );
        self.__salvar__();
        self.__lista_load__();
        self.lista.setCurrentRow( len( self.entity.images ) - 1 );

    def btn_del_click(self):
        row = self.lista.currentRow();
        if row < 0:
            return;
        self.entity.remove_image( row );
        self.__salvar__();
        self.__lista_load__();

    # ---- rosto ----
    def __face_load__(self):
        if self.entity.face:
            pix = pixmap_from_base64( self.entity.face );
            self.lbl_face.setPixmap( pix.scaled( self.lbl_face.width(), self.lbl_face.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation ) );
        else:
            self.lbl_face.clear();
            self.lbl_face.setText("Sem rosto.");

    def btn_face_file_click(self):
        path, _ = QFileDialog.getOpenFileName(self, "Escolher rosto", "", FILTRO);
        if path == "":
            return;
        b64 = png_base64_from_file( path );
        if b64 == None:
            QMessageBox.warning(self, "Imagem inválida", "Não foi possível ler esse arquivo como imagem.");
            return;
        self.entity.set_face( b64 );
        self.__salvar__();
        self.__face_load__();

    def btn_face_sel_click(self):
        row = self.lista.currentRow();
        if row < 0 or row >= len( self.entity.images ):
            QMessageBox.information(self, "Rosto", "Selecione uma imagem da lista primeiro.");
            return;
        self.entity.set_face( self.entity.images[row]["png_base64"] );
        self.__salvar__();
        self.__face_load__();

    def btn_face_del_click(self):
        self.entity.clear_face();
        self.__salvar__();
        self.__face_load__();

    # ---- persistencia ----
    def __salvar__(self):
        # NAO falhar em silencio: __execute__ nao lanca em erro de servidor — devolve
        # {status: False} (ou envelope de erro em resposta vazia/500). Sem checar isso, a
        # imagem "some" (nunca foi gravada) sem o usuario saber. Aqui o erro vira aviso.
        try:
            js = self.entity.save_images();
        except Exception as e:
            QMessageBox.warning(self, "Falha ao salvar", "Não foi possível salvar as imagens no servidor:\n" + str(e));
            return False;
        if not js or not js.get("status"):
            erro = (js or {}).get("error");
            if erro == None or str(erro).strip() == "":
                erro = ("resposta vazia/erro do servidor. Provavelmente o Entity/001.php novo "
                        "e a migração (entity_image/entity_face) ainda não foram publicados.");
            QMessageBox.warning(self, "Falha ao salvar imagem", "O servidor não confirmou o salvamento:\n" + str(erro));
            return False;
        return True;
