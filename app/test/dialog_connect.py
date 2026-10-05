#!/usr/bin/env python3
# Teste da tela de entrada (SPEC/CLAUDE.md: tema e tela de entrada). Sem servidor: o
# Domain.list e trocado por uma lista fixa.
#
# O que importa aqui e o atalho que o dono pediu -- um domain so e escolhido sozinho e o cursor
# cai no primeiro campo que falta -- e o seu limite: com MAIS DE UM domain nao se escolhe por
# conta propria, porque domain errado e banco errado e a senha ja teria sido enviada quando o
# erro aparecesse.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/dialog_connect.py

import os, sys, inspect, tempfile;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
os.environ["HOME"] = tempfile.mkdtemp(prefix="cml_login_");

from PySide6.QtWidgets import QApplication;

FALHAS = [];
ABERTOS = [];   # segura as janelas: sem isto o Python coleta o dialogo antes da assercao ler


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def montar(lista, usuario="", senha=""):
    import classlib.domain as dominio;
    from view.dialog_connect import DialogConnect;
    janela = DialogConnect();
    ABERTOS.append(janela);
    janela.show();
    janela.txt_login_username.setText(usuario);
    janela.txt_login_password.setText(senha);
    dominio.Domain.list = lambda self: lista;   # no lugar da ida ao servidor
    janela.btn_domains_click();
    return janela;


def main():
    app = QApplication(sys.argv);
    from view.ui import estilo;
    estilo.aplicar(app);

    print("um domain só: escolhe sozinho");
    janela = montar([{"name": "corrupcao", "restricted": True}]);
    confere(janela.combo_domains.currentIndex() == 0, "selecionou o índice 0");
    confere(janela.combo_domains.currentText() == "corrupcao", "e é o domain que veio");

    print("\ne o cursor cai no primeiro campo que falta");
    # focusWidget() do diálogo, não hasFocus(): em offscreen a janela não fica ativa, e o
    # hasFocus() de um widget exige janela ativa -- a asserção falharia por motivo errado.
    confere(janela.focusWidget() is janela.txt_login_username, "usuário vazio -> Usuário");
    janela = montar([{"name": "cyberwar", "restricted": False}], usuario="nao.importa.web");
    confere(janela.focusWidget() is janela.txt_login_password, "usuário preenchido -> Senha");
    janela = montar([{"name": "cyberwar", "restricted": False}], usuario="x", senha="y");
    confere(janela.focusWidget() is janela.btn_login_entrar, "os dois preenchidos -> botão Entrar");

    print("\nmais de um domain: NÃO escolhe sozinho");
    janela = montar([{"name": "corrupcao", "restricted": True},
                     {"name": "cyberwar", "restricted": False}]);
    confere(janela.combo_domains.currentIndex() == -1, "fica sem escolha");
    confere(janela.combo_domains.count() == 2, "mas os dois estão na lista");
    confere(janela.focusWidget() is janela.combo_domains, "cursor vai para o combo, que é o que falta decidir");

    print("\nclicar em Domains de novo não duplica");
    janela.btn_domains_click();
    confere(janela.combo_domains.count() == 2, "continua com 2 (%d)" % janela.combo_domains.count());

    print("\ntoken de convite segue o tipo do domain");
    restrito = montar([{"name": "corrupcao", "restricted": True}]);
    confere(restrito.txt_register_token.isEnabled(), "domain restrito habilita o token");
    aberto = montar([{"name": "cyberwar", "restricted": False}]);
    confere(not aberto.txt_register_token.isEnabled(), "domain aberto desabilita");

    print("\nlimpar o combo não liga o token pelo domain antigo");
    # currentIndex() é -1 enquanto nada está escolhido, e em Python lista[-1] é o ÚLTIMO item:
    # sem guarda, o clear() ligava o token conforme o último domain da lista anterior.
    varios = montar([{"name": "aberto1", "restricted": False}, {"name": "restrito2", "restricted": True}]);
    confere(varios.combo_domains.currentIndex() == -1 and not varios.txt_register_token.isEnabled(),
            "sem domain escolhido, o token fica desligado");
    varios.combo_domains.setCurrentIndex(1);   # o restrito
    confere(varios.txt_register_token.isEnabled(), "e liga ao escolher o domain restrito");

    print("\nalternar entre entrar e criar conta");
    janela = montar([{"name": "corrupcao", "restricted": True}]);
    janela.btn_click_register_navegar();
    confere(janela.cabecalho.text() == "Criar conta", "o cabeçalho acompanha: %s" % janela.cabecalho.text());
    janela.btn_click_login_navegar();
    confere(janela.cabecalho.text() == "Entrar", "e volta");

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
