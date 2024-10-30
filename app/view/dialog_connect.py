import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QMessageBox, QApplication, QFileDialog, QMainWindow, QComboBox,
                               QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );

sys.path.append( ROOT );
sys.path.append("/opt/cml/app/");

from view.ui.customvlayout import CustomVLayout;

from classlib.server import Server;
from classlib.user import User;
from classlib.configuration import Configuration;
from classlib.domain import Domain;


class DialogConnect(QDialog):
    def __init__(self):
        super().__init__()
        self.resize(600, 320);
        config = Configuration.instancia();
        self.list_domains = [];
        self.setWindowTitle("Connect")
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
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

    def ui_server(self):
        layout_server = QGridLayout()
        layout_server.setContentsMargins(20, 20, 20, 20)
        layout_server.setSpacing(10)
        self.setWindowTitle("Login/Register")
        server_url = QLabel("Server URL:")
        server_url.setProperty("class", "normal")
        layout_server.addWidget(server_url, 1, 0)
        self.txt_server = QLineEdit();
        self.txt_server.setMinimumWidth(500);
        btn_domains = QPushButton("Domains")
        btn_domains.clicked.connect(self.btn_domains_click)
        layout_server.addWidget(self.txt_server, 1, 1, 1, 1);
        layout_server.addWidget(btn_domains, 1, 2, 1, 1);
        self.combo_domains = QComboBox();
        self.combo_domains.currentIndexChanged.connect(self.combo_domains_changed)
        layout_server.addWidget(self.combo_domains, 2, 1, 1, 2);
        self.layout_principal.addLayout( "server", layout_server );
        self.txt_server.setText( Configuration.instancia().login_server );
        #self.txt_server_finish();

    def ui_login(self):
        layout_login = QGridLayout()
        layout_login.setContentsMargins(20, 20, 20, 20)
        layout_login.setSpacing(10)
        user_login = QLabel("Username:")
        user_login.setProperty("class", "normal")
        layout_login.addWidget(user_login, 1, 0)
        self.txt_login_username = QLineEdit()
        self.txt_login_username.setText( Configuration.instancia().login_username );
        layout_login.addWidget(self.txt_login_username, 1, 1, 1, 2)
        pwd_login = QLabel("Password")
        pwd_login.setProperty("class", "normal")
        layout_login.addWidget(pwd_login, 2, 0)
        self.txt_login_password = QLineEdit();
        self.txt_login_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout_login.addWidget(self.txt_login_password, 2, 1, 1, 2)
        btn_login_entrar = QPushButton("Login")
        btn_login_entrar.clicked.connect(self.btn_click_login_entrar)
        layout_login.addWidget(btn_login_entrar, 4, 2)
        btn_register_navegar = QPushButton("Register")
        btn_register_navegar.clicked.connect(self.btn_click_register_navegar)
        layout_login.addWidget(btn_register_navegar, 4, 1)
        self.layout_principal.addLayout( "login", layout_login );

    def ui_register(self):
        layout_register = QGridLayout()
        layout_register.setContentsMargins(20, 20, 20, 20)
        layout_register.setSpacing(10)
        user_register = QLabel("Username:")
        user_register.setProperty("class", "normal")
        layout_register.addWidget(user_register, 1, 0)
        self.txt_register_username = QLineEdit()
        layout_register.addWidget(self.txt_register_username, 1, 1, 1, 2)
        token_register = QLabel("Invitation token")
        token_register.setProperty("class", "normal")
        layout_register.addWidget(token_register, 2, 0)
        
        # somente exibir se é obrigatório o token de convite, caso contrário náo inserir.
        self.txt_register_token = QLineEdit()
        self.txt_register_token.setEchoMode(QLineEdit.EchoMode.Password)
        layout_register.addWidget(self.txt_register_token, 2, 1, 1, 2)
        pwd_register = QLabel("Password")
        pwd_register.setProperty("class", "normal")
        layout_register.addWidget(pwd_register, 3, 0)

        self.txt_register_password = QLineEdit()
        self.txt_register_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout_register.addWidget(self.txt_register_password, 3, 1, 1, 2)
        pwd_register_2 = QLabel("Password")
        pwd_register_2.setProperty("class", "normal")
        layout_register.addWidget(pwd_register_2, 4, 0)
        self.txt_register_password_2 = QLineEdit()
        self.txt_register_password_2.setEchoMode(QLineEdit.EchoMode.Password)
        layout_register.addWidget(self.txt_register_password_2, 4, 1, 1, 2)
        mail_register = QLabel("E-mail")
        mail_register.setProperty("class", "normal")
        layout_register.addWidget(mail_register, 5, 0)
        self.txt_register_mail = QLineEdit()
        layout_register.addWidget(self.txt_register_mail, 5, 1, 1, 2)
        btn_login_navegar = QPushButton("Login")
        btn_login_navegar.clicked.connect(self.btn_click_login_navegar)
        layout_register.addWidget(btn_login_navegar, 6, 2)
        btn_register_entrar = QPushButton("Register")
        btn_register_entrar.clicked.connect(self.btn_click_register_entrar)
        layout_register.addWidget(btn_register_entrar, 7, 1)
        self.layout_principal.addLayout( "register", layout_register );

    def combo_domains_changed(self):
        self.txt_register_token.setEnabled( self.list_domains[ self.combo_domains.currentIndex() ]["restricted"] );

    def btn_domains_click(self):
        server = Server.instancia();
        server.ip = self.txt_server.text();
        domain = Domain();
        self.list_domains = domain.list();
        for buffer in self.list_domains:
            self.combo_domains.addItem( buffer["name"] );
        return;

    def btn_click_register_navegar(self):
        self.layout_principal.disable("login");
        self.layout_principal.enable("register");
    
    def btn_click_login_navegar(self):
        self.layout_principal.enable("login");
        self.layout_principal.disable("register");       
    
    def btn_click_register_entrar(self):
        server = Server.instancia();
        server.ip = self.txt_server.text();
        server.domain = self.list_domains[ self.combo_domains.currentIndex() ]["name"];
        user = User(self.txt_register_username.text());
        try:
            if self.txt_register_password.text() != self.txt_register_password_2.text():
                raise Exception("O password informado não é igual ao teste.");

            if self.list_domains[ self.combo_domains.currentIndex() ]["restricted"]:
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
        server.domain = self.list_domains[ self.combo_domains.currentIndex() ]["name"];
        user = User(self.txt_login_username.text());
        buffer_public_pem = user.publickey() ;
        if buffer_public_pem != None:
            server.public_key = buffer_public_pem;
            if user.login( self.txt_login_password.text() ):
                Configuration.instancia().login_username = self.txt_login_username.text();
                Configuration.instancia().login_server = self.txt_server.text();
                Configuration.instancia().save();
                server.status = True;
                self.close();
