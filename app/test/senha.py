#!/usr/bin/env python3
# Teste da troca de senha e do mascaramento do envelope RPC (SPEC.md §10.1 a §10.3).
# Sem servidor: o __execute__ do User e trocado por um servidor de mentira que imita o
# User.change_password do PHP.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/senha.py

import os, sys, inspect, hashlib, json, tempfile;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
os.environ["HOME"] = tempfile.mkdtemp(prefix="cml_senha_");

from PySide6.QtWidgets import QApplication;

FALHAS = [];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


class ServidorFalso:
    """Imita o User.change_password do PHP: confere a senha atual, recusa igual, troca o salt."""

    def __init__(self, senha="segredo-atual", salt="1111"):
        self.salt = salt;
        self.guardado = hashlib.sha256((senha + salt).encode()).hexdigest();
        self.chamadas = [];

    def __call__(self, classe, metodo, parametros, crypto_v="000"):
        self.chamadas.append((classe, metodo, dict(parametros)));
        if (classe, metodo) == ("Session", "publickey"):
            return {"status": True, "return": {"public": "-", "salt": self.salt}};
        if (classe, metodo) != ("User", "change_password"):
            return {"status": False, "return": None, "error": "método inesperado"};
        atual, nova, salt = parametros["atual"], parametros["nova"], parametros["salt"];
        if atual != self.guardado:
            return {"status": True, "return": {"status": False, "mensage": "A senha atual não confere."}};
        if atual == nova:
            return {"status": True, "return": {"status": False, "mensage": "A senha nova é igual à atual."}};
        self.guardado = nova;
        self.salt = salt;
        return {"status": True, "return": {"status": True, "mensage": "Senha alterada."}};


def main():
    QApplication(sys.argv);
    from classlib.user import User;
    from classlib import connectobject;

    print("troca de senha");
    servidor = ServidorFalso();
    usuario = User("fulano");
    usuario.salt = servidor.salt;
    usuario.__execute__ = servidor;
    ok, mensagem = usuario.change_password("segredo-atual", "senha-nova-longa");
    confere(ok, "aceitou a troca: %s" % mensagem);

    print("\nmanda hash, nunca a senha em claro");
    enviado = servidor.chamadas[-1][2];
    corpo = json.dumps(enviado);
    confere("segredo-atual" not in corpo and "senha-nova-longa" not in corpo,
            "nenhuma senha em claro no que foi enviado");
    confere(len(enviado["atual"]) == 64 and len(enviado["nova"]) == 64, "os dois são sha256");

    print("\no salt gira na troca");
    confere(enviado["salt"] != "1111", "foi mandado um salt novo");
    confere(usuario.salt == enviado["salt"], "e o cliente passou a usar o novo");
    confere(enviado["nova"] == hashlib.sha256(("senha-nova-longa" + enviado["salt"]).encode()).hexdigest(),
            "a nova foi calculada COM o salt novo");

    print("\na senha nova passa a valer, a antiga não");
    ok, _ = usuario.change_password("segredo-atual", "outra-qualquer-xy");
    confere(not ok, "a senha antiga foi recusada");
    ok, _ = usuario.change_password("senha-nova-longa", "outra-qualquer-xy");
    confere(ok, "a nova foi aceita");

    print("\nrecusas do servidor chegam como mensagem, não como exceção");
    ok, mensagem = usuario.change_password("errada-mesmo", "qualquer-coisa-x");
    confere(not ok and "não confere" in mensagem, "senha atual errada: %s" % mensagem);

    print("\nnunca manda username: quem é vem do token da sessão");
    for _classe, _metodo, parametros in servidor.chamadas:
        if _metodo == "change_password":
            confere("username" not in parametros, "o pedido não carrega username");
            break;

    print("\no envelope RPC não sai com segredo");
    envelope = {"class": "Session", "method": "login", "domain": "corrupcao",
                "session": "TOKEN-SECRETO-123",
                "parameters": '00000000{"username": "fulano", "password": "2399bc29", "simetric_key": "f148"}'};
    mascarado = json.dumps(connectobject.__mascarar__(envelope));
    confere("TOKEN-SECRETO-123" not in mascarado, "o token da sessão foi omitido");
    confere("2399bc29" not in mascarado, "a senha DENTRO de parameters foi omitida");
    confere("f148" not in mascarado, "a chave simétrica também");
    confere("fulano" in mascarado and "corrupcao" in mascarado,
            "e o que serve para depurar continua legível");
    confere(connectobject.DEPURAR == False, "sem CML_DEBUG_RPC, nada é impresso");

    print("\nsem backend de LLM, o app recusa com MOTIVO (não com exceção crua)");
    from transform import nucleo;
    for variavel in ("CML_LLM_BACKEND", "CML_OLLAMA_URL"):
        os.environ.pop(variavel, None);
    confere(nucleo.backend_llm() == "nenhum", "sem variável nenhuma, não há backend (%s)" % nucleo.backend_llm());
    motivo = nucleo.motivo_llm();
    confere(motivo != None and "rolhama" in motivo and "CML_OLLAMA_URL" in motivo,
            "e o motivo diz o que houve e o que fazer: %s" % motivo);
    cfg_ia = {"fonte": "ia", "rede": False};
    confere(nucleo.indisponivel(cfg_ia) == motivo, "o menu de transform mostra o MESMO motivo");

    os.environ["CML_OLLAMA_URL"] = "http://127.0.0.1:11434";
    confere(nucleo.backend_llm() == "ollama", "com CML_OLLAMA_URL, o backend é o Ollama local");
    confere(nucleo.motivo_llm() == None, "e aí não há motivo de recusa");
    confere(nucleo.indisponivel(cfg_ia) == None, "o transform de IA volta a ficar disponível");

    os.environ["CML_LLM_BACKEND"] = "rolhama";
    confere("não volta" in (nucleo.motivo_llm() or ""), "pedir rolhama explicitamente é recusado com explicação");
    os.environ.pop("CML_LLM_BACKEND", None);
    os.environ.pop("CML_OLLAMA_URL", None);

    print("\no report recusa antes de subir a thread");
    from view.ui.report_manager import ReportManager;
    class MapaFalso:
        id = "x"; 
        def getName(self): return "M";
    try:
        ReportManager.instancia().iniciar(MapaFalso());
        confere(False, "deveria recusar sem LLM");
    except Exception as erro:
        confere("precisa de um LLM" in str(erro), "recusou com motivo: %s" % str(erro)[:80]);

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
