#!/usr/bin/env python3
# Teste de copiar/colar entre mapas (SPEC.md §3.3). Mapa EM MEMORIA, sem servidor.
#
# A regra que importa: ENTIDADE E GLOBAL. Colar cria CAIXA nova apontando para a MESMA
# entidade -- se duplicasse a entidade, o merge_to teria de juntar os gemeos depois.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/transferencia.py

import os, sys, inspect, tempfile, json;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
os.environ["HOME"] = tempfile.mkdtemp(prefix="cml_transf_");

from PySide6.QtWidgets import QApplication;

from classlib.relationship.maprelationship import MapRelationship;
from classlib.relationship import transferencia as tr;
from classlib.relationship.comandos import Operacao;

FALHAS = [];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def montar():
    mapa = MapRelationship();
    mapa.name = "Origem";
    zeca = mapa.addEntity("person", 100, 100, text="Zeca");
    zeca.entity.small_label = "ZS";
    zeca.entity.full_description = "Sócio desde 2019";
    zeca.start_date = "2019-01-01";
    org = mapa.addEntity("organization", 400, 200, text="Construtora X");
    fora = mapa.addEntity("other", 700, 400, text="Fora da seleção");
    v = mapa.addEntity("link", 250, 150, text="dirige");
    v.addFrom(zeca, start_date="2020-03-01", end_date=None);
    v.addTo(org);
    solto = mapa.addEntity("link", 600, 300, text="meia aresta");
    solto.addFrom(org); solto.addTo(fora);
    mapa.desfazer.clear();
    return mapa, zeca, org, fora, v, solto;


def main():
    QApplication(sys.argv);
    origem, zeca, org, fora, v, solto = montar();

    print("copiar");
    texto = tr.copiar([zeca, org, v, solto]);
    dados = json.loads(texto);
    confere(dados["cabecalho"] == tr.CABECALHO, "tem o cabeçalho próprio");
    confere(len(dados["caixas"]) == 2, "2 caixas (%d)" % len(dados["caixas"]));
    confere(len(dados["vinculos"]) == 1, "só o vínculo com AS DUAS pontas na seleção (%d)"
            % len(dados["vinculos"]));

    print("\ncolar em outro mapa");
    destino = MapRelationship();
    destino.name = "Destino";
    with Operacao(destino, "Colar"):
        caixas, vinculos, novos = tr.colar(destino, texto);
    confere((caixas, vinculos) == (2, 1), "coladas 2 caixas e 1 vínculo");
    confere(len(destino.elements) == 3, "3 elements no destino");
    confere(len(novos) == 3, "devolveu os novos para quem quiser selecionar");

    print("\nentidade é a MESMA, a caixa é nova");
    colado_zeca = [e for e in destino.elements if e.entity.text == "Zeca"][0];
    confere(colado_zeca.entity.id == zeca.entity.id, "mesmo entity_id (entidade é global)");
    confere(colado_zeca.id != zeca.id, "mas a caixa tem id próprio");
    confere(colado_zeca is not zeca, "e é outro objeto");

    print("\nos campos vieram junto");
    confere(colado_zeca.entity.small_label == "ZS", "apelido");
    confere(colado_zeca.entity.full_description == "Sócio desde 2019", "descrição");
    confere(colado_zeca.start_date == "2019-01-01", "data da caixa");
    colado_v = [e for e in destino.elements if e.entity.etype == "link"][0];
    confere(colado_v.from_entity[0].start_date == "2020-03-01", "data da PONTA do vínculo");
    confere(colado_v.from_entity[0].entity is colado_zeca, "a ponta aponta para a caixa COLADA");
    confere(colado_v.to_entity[0].entity.entity.text == "Construtora X", "a outra ponta também");

    print("\ndeslocamento");
    confere(colado_zeca.x == zeca.x + tr.DESLOCAMENTO, "colou deslocado, não por cima (%d)" % colado_zeca.x);

    print("\num Ctrl+Z desfaz a colagem inteira");
    confere(destino.desfazer.count() == 1, "um passo só");
    destino.desfazer.undo();
    confere(len(destino.elements) == 0, "desfazer limpou os 3 de uma vez");

    print("\nrecusas");
    confere(not tr.pode_colar("qualquer texto"), "texto solto não é pedaço de mapa");
    confere(not tr.pode_colar('{"cabecalho": "OUTRA-COISA"}'), "JSON de outro programa também não");
    confere(tr.pode_colar(texto), "o nosso é reconhecido");
    try:
        tr.colar(destino, "lixo");
        confere(False, "deveria recusar");
    except tr.ErroTransferencia as erro:
        confere("transferência" in str(erro), "recusou com mensagem clara");
    try:
        tr.copiar([v]);
        confere(False, "deveria recusar copiar só vínculo");
    except tr.ErroTransferencia as erro:
        confere("caixa" in str(erro), "copiar só vínculo é recusado: %s" % erro);

    print("\nmapa travado não recebe");
    travado = MapRelationship();
    travado.locked = True;
    try:
        tr.colar(travado, texto);
        confere(False, "deveria recusar");
    except tr.ErroTransferencia as erro:
        confere("travado" in str(erro), "recusou mapa travado");

    print("\ncolar no MESMO mapa");
    with Operacao(origem, "Colar"):
        caixas, vinculos, novos = tr.colar(origem, texto);
    confere(caixas == 2, "colou no próprio mapa de origem");
    gemeas = [e for e in origem.elements if e.entity.id == zeca.entity.id];
    confere(len(gemeas) == 2, "duas CAIXAS para a mesma entidade, o que é legítimo");
    confere(len(set(e.id for e in gemeas)) == 2, "com ids de caixa diferentes");

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
