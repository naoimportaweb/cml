#!/usr/bin/env python3
# Teste do Mapa Regional (SPEC.md §5). Mapa EM MEMORIA, sem servidor.
#
# O que ele promete, e o que o teste cobra:
#   - reconhece pais pelo SUB-TIPO, nao por adivinhacao sobre o nome;
#   - "entidades" conta caixas DISTINTAS que tocam o país, nao vinculos -- duas pessoas ligadas
#     por tres vinculos cada sao duas, nao seis;
#   - ordena do mais tocado ao menos, com desempate estavel;
#   - avisa quando falta bandeira, em vez de desenhar buraco.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/regional.py

import os, sys, inspect, tempfile;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
os.environ["HOME"] = tempfile.mkdtemp(prefix="cml_regional_");

from PySide6.QtWidgets import QApplication;

from classlib.relationship.maprelationship import MapRelationship;
from classlib.relationship import regional;

FALHAS = [];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def pais(mapa, nome, bandeira="iVBORw0KGgo="):
    caixa = mapa.addEntity("other", 0, 0, text=nome);
    caixa.entity.sub_etype_name = "country";
    caixa.entity.face = bandeira;
    return caixa;


def liga(mapa, de, para, verbo="atua em"):
    elo = mapa.addEntity("link", 0, 0, text=verbo);
    elo.addFrom(de); elo.addTo(para);
    return elo;


def main():
    QApplication(sys.argv);
    mapa = MapRelationship();
    mapa.name = "Regional";

    brasil = pais(mapa, "Brasil");
    panama = pais(mapa, "Panamá");
    suica = pais(mapa, "Suíça", bandeira=None);          # sem bandeira de propósito
    nao_pais = mapa.addEntity("other", 0, 0, text="Contrato 44");   # sem sub-tipo

    zeca = mapa.addEntity("person", 0, 0, text="Zeca");
    ana = mapa.addEntity("person", 0, 0, text="Ana");
    org = mapa.addEntity("organization", 0, 0, text="Construtora X");

    # Zeca toca o Brasil por TRÊS vínculos: tem de contar como UMA entidade.
    liga(mapa, zeca, brasil); liga(mapa, zeca, brasil, "nasceu em"); liga(mapa, zeca, brasil, "votou em");
    liga(mapa, ana, brasil);
    liga(mapa, org, brasil);
    liga(mapa, org, panama);
    liga(mapa, zeca, nao_pais);   # não é país: não entra em lugar nenhum do resumo

    resumo = regional.agregar(mapa);

    print("reconhece país pelo sub-tipo");
    confere(len(resumo) == 3, "3 países (%d)" % len(resumo));
    nomes = [r["nome"] for r in resumo];
    confere("Contrato 44" not in nomes, "entidade sem sub-tipo não virou país");
    confere(not regional.eh_pais(zeca), "pessoa não é país");
    confere(regional.eh_pais(brasil), "entidade com sub-tipo country é país");

    print("\nconta ENTIDADES distintas, não vínculos");
    br = [r for r in resumo if r["nome"] == "Brasil"][0];
    confere(br["entidades"] == 3, "Brasil tocado por 3 entidades, apesar dos 5 vínculos (%d)" % br["entidades"]);
    confere(br["vinculos"] == 5, "e os 5 vínculos também são contados, em coluna própria (%d)" % br["vinculos"]);

    print("\nordem: do mais tocado ao menos");
    confere(nomes[0] == "Brasil", "Brasil primeiro");
    pa = [r for r in resumo if r["nome"] == "Panamá"][0];
    confere(pa["entidades"] == 1, "Panamá com 1");
    su = [r for r in resumo if r["nome"] == "Suíça"][0];
    confere(su["entidades"] == 0, "Suíça sem ninguém ligado, e mesmo assim aparece");
    confere(nomes.index("Panamá") < nomes.index("Suíça"), "e vem antes da Suíça");

    print("\nbandeira que falta é avisada, não escondida");
    confere(regional.sem_bandeira(resumo) == 1, "1 país sem bandeira (%d)" % regional.sem_bandeira(resumo));

    print("\ndesempate é estável");
    a = [r["nome"] for r in regional.agregar(mapa)];
    b = [r["nome"] for r in regional.agregar(mapa)];
    confere(a == b, "a mesma ordem em duas chamadas");

    print("\nmapa sem país nenhum");
    vazio = MapRelationship();
    vazio.addEntity("person", 0, 0, text="Alguém");
    confere(regional.agregar(vazio) == [], "devolve vazio, sem quebrar");
    confere(regional.agregar(MapRelationship()) == [], "mapa vazio idem");

    print("\na vista monta sem servidor");
    from view.ui.mapa_regional import MapaRegional;
    vista = MapaRegional(None, mapa);
    vista.atualizar();
    confere(vista.tabela.rowCount() == 3, "3 linhas na tabela");
    confere(vista.tabela.item(0, 1).text() == "Brasil", "a primeira é o Brasil");
    confere("sem bandeira" in vista.explicacao.text(), "o aviso de bandeira aparece na tela");
    vazia = MapaRegional(None, MapRelationship());
    vazia.atualizar();
    confere("Nenhum país" in vazia.explicacao.text(), "mapa sem país explica o que é um país");

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
