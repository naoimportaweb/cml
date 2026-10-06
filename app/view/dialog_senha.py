import os, sys, inspect;

from PySide6.QtCore import Qt;
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QVBoxLayout);

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from classlib.user import User;
from classlib.configuration import Configuration;
from view.ui import estilo;

MINIMO = 8;


class DialogSenha(QDialog):
    """Trocar a propria senha.

    Antes isto nao existia em lugar nenhum -- nem no cliente, nem no servidor -- e a unica
    forma de girar uma senha era UPDATE direto no banco. Com a senha semeada do create.sql
    publicada em repositorio, nao ter como trocar era parte do problema.
    """

    def __init__(self, parent):
        super().__init__(parent);
        self.setWindowTitle("Alterar senha");
        self.setMinimumWidth(420);

        layout = QVBoxLayout(self);
        layout.setContentsMargins(22, 20, 22, 18);
        layout.setSpacing(6);

        titulo = QLabel("Alterar senha");
        fonte = titulo.font(); fonte.setPointSize(14); fonte.setBold(True); titulo.setFont(fonte);
        layout.addWidget(titulo);
        aviso = QLabel("As outras sessões desta conta serão encerradas.");
        aviso.setWordWrap(True);
        aviso.setStyleSheet("color: %s;" % estilo.COR_APAGADO);
        layout.addWidget(aviso);
        layout.addSpacing(12);

        self.txt_atual = self.__campo__(layout, "Senha atual");
        self.txt_nova = self.__campo__(layout, "Senha nova (mínimo de %d caracteres)" % MINIMO);
        self.txt_repete = self.__campo__(layout, "Repita a senha nova");

        self.mensagem = QLabel("");
        self.mensagem.setWordWrap(True);
        layout.addSpacing(6);
        layout.addWidget(self.mensagem);

        botoes = QDialogButtonBox(QDialogButtonBox.Cancel);
        self.btn_ok = QPushButton("Alterar");
        self.btn_ok.setProperty("destaque", "sim");
        self.btn_ok.setDefault(True);
        self.btn_ok.clicked.connect(self.alterar);
        botoes.addButton(self.btn_ok, QDialogButtonBox.AcceptRole);
        botoes.rejected.connect(self.reject);
        layout.addWidget(botoes);

        self.txt_atual.setFocus();

    def __campo__(self, layout, rotulo):
        etiqueta = QLabel(rotulo);
        etiqueta.setStyleSheet("color: %s;" % estilo.COR_APAGADO);
        layout.addWidget(etiqueta);
        campo = QLineEdit();
        campo.setEchoMode(QLineEdit.Password);
        campo.returnPressed.connect(self.alterar);
        layout.addWidget(campo);
        layout.addSpacing(8);
        return campo;

    def __erro__(self, texto):
        self.mensagem.setText(texto);
        self.mensagem.setStyleSheet("color: #e06c6c;");

    def alterar(self):
        atual = self.txt_atual.text();
        nova = self.txt_nova.text();
        if atual.strip() == "":
            return self.__erro__("Informe a senha atual.");
        if len(nova) < MINIMO:
            return self.__erro__("A senha nova precisa de pelo menos %d caracteres." % MINIMO);
        if nova != self.txt_repete.text():
            return self.__erro__("A repetição não confere com a senha nova.");
        if nova == atual:
            return self.__erro__("A senha nova é igual à atual.");

        self.btn_ok.setEnabled(False);
        self.mensagem.setText("Falando com o servidor...");
        self.mensagem.setStyleSheet("color: %s;" % estilo.COR_APAGADO);
        try:
            ok, texto = User( Configuration.instancia().login_username ).change_password(atual, nova);
        except Exception as erro:
            self.btn_ok.setEnabled(True);
            return self.__erro__("Não foi possível alterar: %s" % erro);
        self.btn_ok.setEnabled(True);
        if not ok:
            return self.__erro__(texto);
        QMessageBox.information(self, "Alterar senha", texto);
        self.accept();
