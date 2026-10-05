import os, sys, inspect, json;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QKeySequence, QLinearGradient, QPainter
from PySide6.QtWidgets import (QMessageBox, QApplication, QFileDialog, QMainWindow, QComboBox, QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton, QWidget, QFrame)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );

sys.path.append( ROOT );
sys.path.append("/opt/cml/app/");

from view.ui.customvlayout import CustomVLayout;
from view.ui import estilo;
from classlib.server import Server;
from classlib.user import User;
from classlib.configuration import Configuration;
from classlib.domain import Domain;
from classlib.entity import Entity;

class PainelMarca(QFrame):
    """A coluna da esquerda: emblema, nome e uma linha do que o programa faz.

    O emblema e desenhado (estilo.emblema), nao carregado de arquivo: e a propria coisa que o
    CML faz -- entidades e os vinculos entre elas -- e assim nasce na resolucao da tela, segue
    a cor do tema e nao ha binario de enfeite para alguem trocar por engano."""

    LARGURA = 300;

    def __init__(self):
        super().__init__();
        self.setFixedWidth(self.LARGURA);
        self.setAutoFillBackground(True);
        self.emblema = estilo.emblema(200, 190);

        layout = QVBoxLayout(self);
        layout.setContentsMargins(28, 30, 28, 24);
        layout.addStretch(2);

        self.desenho = QLabel();
        self.desenho.setPixmap(self.emblema);
        self.desenho.setAlignment(Qt.AlignHCenter);
        self.desenho.setStyleSheet("background: transparent;");
        layout.addWidget(self.desenho);
        layout.addSpacing(18);

        titulo = QLabel("CML");
        fonte = QFont("monospace");
        fonte.setStyleHint(QFont.Monospace);
        fonte.setPointSize(30);
        fonte.setBold(True);
        titulo.setFont(fonte);
        titulo.setAlignment(Qt.AlignHCenter);
        titulo.setStyleSheet("color: %s; background: transparent;" % estilo.COR_TEXTO);
        layout.addWidget(titulo);

        linha = QLabel("análise de vínculos");
        fonte_linha = QFont("monospace");
        fonte_linha.setStyleHint(QFont.Monospace);
        fonte_linha.setPointSize(10);
        linha.setFont(fonte_linha);
        linha.setAlignment(Qt.AlignHCenter);
        linha.setStyleSheet("color: %s; background: transparent;" % estilo.COR_REALCE);
        layout.addWidget(linha);
        layout.addStretch(3);

        # Duas linhas de proposito: numa so, o Qt quebrava "linha do tempo" no meio.
        rodape = QLabel("mapas · organogramas\nlinha do tempo");
        fonte_rodape = QFont("monospace");
        fonte_rodape.setStyleHint(QFont.Monospace);
        fonte_rodape.setPointSize(8);
        rodape.setFont(fonte_rodape);
        rodape.setAlignment(Qt.AlignHCenter);
        rodape.setWordWrap(True);
        rodape.setStyleSheet("color: %s; background: transparent;" % estilo.COR_APAGADO);
        layout.addWidget(rodape);

    def paintEvent(self, evento):
        # Gradiente no proprio painel, de cima claro para baixo escuro: separa a coluna da
        # marca do formulario sem precisar de uma borda desenhada.
        painter = QPainter(self);
        gradiente = QLinearGradient(0, 0, 0, self.height());
        gradiente.setColorAt(0.0, QColor(estilo.COR_ALTERNADA));
        gradiente.setColorAt(1.0, QColor(estilo.COR_FUNDO));
        painter.fillRect(self.rect(), gradiente);
        painter.setPen(QColor(estilo.COR_BORDA));
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height());
        painter.end();
        super().paintEvent(evento);


class DialogConnect(QDialog):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(780, 460);
        config = Configuration.instancia();
        self.list_domains = [];
        self.setWindowTitle("CML — entrar")

        # Duas colunas: marca a esquerda, formulario a direita.
        fora = QHBoxLayout(self);
        fora.setContentsMargins(0, 0, 0, 0);
        fora.setSpacing(0);
        fora.addWidget(PainelMarca());

        direita = QWidget();
        coluna = QVBoxLayout(direita);
        coluna.setContentsMargins(34, 30, 34, 26);
        coluna.setSpacing(0);

        self.cabecalho = QLabel("Entrar");
        fonte_cabecalho = QFont();
        fonte_cabecalho.setPointSize(16);
        fonte_cabecalho.setBold(True);
        self.cabecalho.setFont(fonte_cabecalho);
        coluna.addWidget(self.cabecalho);
        self.subtitulo = QLabel("Informe o servidor, escolha o domain e entre com a sua conta.");
        self.subtitulo.setWordWrap(True);
        self.subtitulo.setStyleSheet("color: %s;" % estilo.COR_APAGADO);
        coluna.addWidget(self.subtitulo);
        coluna.addSpacing(18);

        self.layout_principal = CustomVLayout();
        coluna.addLayout( self.layout_principal );
        coluna.addStretch(1);
        fora.addWidget(direita, 1);

        self.ui_server  ();
        self.ui_register();
        self.ui_login   ();
        self.layout_principal.disable("register");
        if self.txt_login_username.text().strip() == "":
            self.txt_login_username.setFocus()
        elif self.txt_login_password.text().strip() == "":
            self.txt_login_password.setFocus();

    def buffer_text(self):
        print("testado.....");

    def __rotulo__(self, texto):
        etiqueta = QLabel(texto);
        etiqueta.setProperty("class", "normal");
        etiqueta.setStyleSheet("color: %s;" % estilo.COR_APAGADO);
        return etiqueta;

    def ui_server(self):
        # Margem zero: quem da respiro e a coluna de fora. Com margem nos dois, o formulario
        # ficava deslocado para a direita e desalinhado do cabecalho.
        layout_server = QGridLayout()
        layout_server.setContentsMargins(0, 0, 0, 0)
        layout_server.setSpacing(8)
        layout_server.setColumnStretch(0, 1);
        layout_server.addWidget(self.__rotulo__("Servidor"), 0, 0, 1, 2);
        self.txt_server = QLineEdit();
        self.txt_server.setPlaceholderText("https://exemplo.com.br");
        self.txt_server.setClearButtonEnabled(True);
        btn_domains = QPushButton("Domains")
        btn_domains.setAutoDefault(False);
        btn_domains.setToolTip("Buscar no servidor a lista de domains disponíveis");
        btn_domains.clicked.connect(self.btn_domains_click)
        layout_server.addWidget(self.txt_server, 1, 0);
        layout_server.addWidget(btn_domains, 1, 1);
        layout_server.addWidget(self.__rotulo__("Domain"), 2, 0, 1, 2);
        self.combo_domains = QComboBox();
        self.combo_domains.setPlaceholderText("clique em Domains para listar");
        self.combo_domains.currentIndexChanged.connect(self.combo_domains_changed)
        layout_server.addWidget(self.combo_domains, 3, 0, 1, 2);
        self.layout_principal.addLayout( "server", layout_server );
        self.txt_server.setText( Configuration.instancia().login_server );

    def ui_login(self):
        layout_login = QGridLayout()
        layout_login.setContentsMargins(0, 14, 0, 0)
        layout_login.setSpacing(8)
        layout_login.setColumnStretch(0, 1);
        layout_login.addWidget(self.__rotulo__("Usuário"), 0, 0, 1, 2);
        self.txt_login_username = QLineEdit()
        self.txt_login_username.setText( Configuration.instancia().login_username );
        layout_login.addWidget(self.txt_login_username, 1, 0, 1, 2)
        layout_login.addWidget(self.__rotulo__("Senha"), 2, 0, 1, 2);
        self.txt_login_password = QLineEdit();
        self.txt_login_password.setEchoMode(QLineEdit.EchoMode.Password)
        # Enter no campo de senha entra, que e o que todo mundo tenta primeiro.
        self.txt_login_password.returnPressed.connect(self.btn_click_login_entrar);
        layout_login.addWidget(self.txt_login_password, 3, 0, 1, 2)
        btn_register_navegar = QPushButton("Criar conta")
        # Num QDialog todo botao nasce autoDefault, e o seletor QPushButton:default pintava os
        # dois de azul -- a tela ficava com duas acoes principais e nenhuma.
        btn_register_navegar.setAutoDefault(False);
        btn_register_navegar.clicked.connect(self.btn_click_register_navegar)
        btn_login_entrar = QPushButton("Entrar")
        btn_login_entrar.setProperty("destaque", "sim");   # a acao principal da tela
        btn_login_entrar.setDefault(True);
        btn_login_entrar.clicked.connect(self.btn_click_login_entrar)
        linha = QHBoxLayout();
        linha.setContentsMargins(0, 10, 0, 0);
        linha.addWidget(btn_register_navegar);
        linha.addStretch(1);
        linha.addWidget(btn_login_entrar);
        layout_login.addLayout(linha, 4, 0, 1, 2);
        self.layout_principal.addLayout( "login", layout_login );

    def ui_register(self):
        layout_register = QGridLayout()
        layout_register.setContentsMargins(0, 14, 0, 0)
        layout_register.setSpacing(8)
        layout_register.setColumnStretch(0, 1);
        layout_register.addWidget(self.__rotulo__("Usuário"), 0, 0, 1, 2);
        self.txt_register_username = QLineEdit()
        layout_register.addWidget(self.txt_register_username, 1, 0, 1, 2)
        layout_register.addWidget(self.__rotulo__("Token de convite"), 2, 0, 1, 2);
        # So faz sentido em domain restrito; o combo_domains_changed liga e desliga.
        self.txt_register_token = QLineEdit()
        self.txt_register_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_register_token.setPlaceholderText("exigido apenas em domain restrito");
        layout_register.addWidget(self.txt_register_token, 3, 0, 1, 2)
        layout_register.addWidget(self.__rotulo__("Senha"), 4, 0, 1, 2);
        self.txt_register_password = QLineEdit()
        self.txt_register_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout_register.addWidget(self.txt_register_password, 5, 0, 1, 2)
        layout_register.addWidget(self.__rotulo__("Repita a senha"), 6, 0, 1, 2);
        self.txt_register_password_2 = QLineEdit()
        self.txt_register_password_2.setEchoMode(QLineEdit.EchoMode.Password)
        layout_register.addWidget(self.txt_register_password_2, 7, 0, 1, 2)
        layout_register.addWidget(self.__rotulo__("E-mail"), 8, 0, 1, 2);
        self.txt_register_mail = QLineEdit()
        layout_register.addWidget(self.txt_register_mail, 9, 0, 1, 2)
        btn_login_navegar = QPushButton("Voltar")
        btn_login_navegar.setAutoDefault(False);
        btn_login_navegar.clicked.connect(self.btn_click_login_navegar)
        btn_register_entrar = QPushButton("Criar conta")
        btn_register_entrar.setProperty("destaque", "sim");
        btn_register_entrar.clicked.connect(self.btn_click_register_entrar)
        linha = QHBoxLayout();
        linha.setContentsMargins(0, 10, 0, 0);
        linha.addWidget(btn_login_navegar);
        linha.addStretch(1);
        linha.addWidget(btn_register_entrar);
        layout_register.addLayout(linha, 10, 0, 1, 2);
        self.layout_principal.addLayout( "register", layout_register );

    def combo_domains_changed(self):
        self.txt_register_token.setEnabled( self.list_domains[ self.combo_domains.currentIndex() ]["restricted"] );

    def btn_domains_click(self):
        server = Server.instancia();
        server.ip = self.txt_server.text();
        domain = Domain();
        buffer_domains = domain.list();
        if not buffer_domains:
            msgBox = QMessageBox();
            msgBox.setText( "Não foi possível obter a lista de domains de " + server.ip + ".\nVerifique a URL do servidor (o esquema http/https precisa ser o final, sem redirecionamento) e a conexão." );
            msgBox.exec();
            return;
        self.list_domains = buffer_domains;
        self.combo_domains.clear(); # sem isto cada clique reempilha os domains no combo
        for buffer in self.list_domains:
            self.combo_domains.addItem( buffer["name"] );
        return;

    def btn_click_register_navegar(self):
        self.layout_principal.disable("login");
        self.layout_principal.enable("register");
        self.cabecalho.setText("Criar conta");
        self.subtitulo.setText("Domain restrito exige um token de convite, entregue pelo administrador.");

    def btn_click_login_navegar(self):
        self.layout_principal.enable("login");
        self.layout_principal.disable("register");
        self.cabecalho.setText("Entrar");
        self.subtitulo.setText("Informe o servidor, escolha o domain e entre com a sua conta.");
    
    def __domain_selecionado__(self):
        # O combo só é populado pelo botão Domains. Sem clicar nele antes, list_domains
        # fica vazio e indexar aqui estoura IndexError sem nada aparecer na tela.
        indice = self.combo_domains.currentIndex();
        if indice < 0 or indice >= len( self.list_domains ):
            msgBox = QMessageBox();
            msgBox.setText( "Informe o servidor e clique em Domains antes de continuar." );
            msgBox.exec();
            return None;
        return self.list_domains[ indice ];

    def btn_click_register_entrar(self):
        server = Server.instancia();
        server.ip = self.txt_server.text();
        domain_selecionado = self.__domain_selecionado__();
        if domain_selecionado == None:
            return;
        server.domain = domain_selecionado["name"];
        user = User(self.txt_register_username.text());
        try:
            if self.txt_register_password.text() != self.txt_register_password_2.text():
                raise Exception("O password informado não é igual ao teste.");

            if domain_selecionado["restricted"]:
                if self.txt_register_token.text().strip() == "" or self.txt_register_password.text().strip() == "" or self.txt_register_username.text().strip() == "" or self.txt_register_mail.text().strip() == "":
                    raise Exception("Informe todos os dados.");  

            if user.register( self.txt_register_username.text(), self.txt_register_password.text(), self.txt_register_mail.text(), self.txt_register_token.text() ) == True:
                self.layout_principal.disable("register");
                self.layout_principal.enable("login");
                msgBox = QMessageBox();
                msgBox.setText( "Cadastro criado com sucesso, realize o procedimento de login." );
                msgBox.exec();
        except Exception as error:
            print(repr(error))
            msgBox = QMessageBox();
            msgBox.setText( str(repr(error)) );
            msgBox.exec();
    
    def btn_click_login_entrar(self):
        server = Server.instancia();
        server.ip = self.txt_server.text();
        domain_selecionado = self.__domain_selecionado__();
        if domain_selecionado == None:
            return;
        server.domain = domain_selecionado["name"];
        user = User(self.txt_login_username.text());
        buffer_public_pem = user.publickey() ;
        if buffer_public_pem == None:
            msgBox = QMessageBox();
            msgBox.setText( "Não foi possível obter a chave pública de " + server.ip + ".\nVerifique a URL do servidor e o domain selecionado." );
            msgBox.exec();
            return;
        server.public_key = buffer_public_pem;
        if user.login( self.txt_login_password.text() ):
            Configuration.instancia().login_username = self.txt_login_username.text();
            # server.ip e nao txt_server.text(): o Server ja normalizou a barra final, e
            # assim ela nao volta do ~/.cml.json na proxima sessao.
            Configuration.instancia().login_server = server.ip;
            Configuration.instancia().save();
            server.status = True;
            self.close();
        else:
            msgBox = QMessageBox();
            msgBox.setText( "Usuário ou senha inválidos." );
            msgBox.exec();
