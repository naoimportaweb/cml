#!/usr/bin/env python3
# Teste da importacao de CSV e GraphML (SPEC.md §6). Sem servidor.
#
# A regra de desenho que o teste cobra: importar devolve um RESULTADO (o mesmo que um transform
# devolve), nunca grava no mapa. Quem grava e o painel Proposta, que faz buscar-antes-de-criar.
#
# E o que o leitor tem de aguentar: ponto-e-virgula ou virgula, cabecalho em varias grafias,
# planilha so de vinculos, GraphML de outra ferramenta, aresta apontando para no inexistente.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/importar_dados.py

import os, sys, inspect, tempfile;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
TEMP = tempfile.mkdtemp(prefix="cml_import_");
os.environ["HOME"] = TEMP;

from PySide6.QtWidgets import QApplication;

from classlib.relationship.maprelationship import MapRelationship;
from classlib import importar_dados as imp;
from classlib import exportar_dados as ed;
from transform.aplicar import aplicar;

FALHAS = [];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def gravar(nome, conteudo):
    caminho = os.path.join(TEMP, nome);
    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write(conteudo);
    return caminho;


def main():
    QApplication(sys.argv);

    print("CSV de entidades, com ponto-e-vírgula");
    caminho = gravar("entidades.csv",
                     "nome;tipo;apelido;descricao\n"
                     "Zeca Silva;pessoa;ZS;Sócio\n"
                     "Construtora X;empresa;CX;\n"
                     "Contrato 44;outro;;Assinado em 2021\n");
    r = imp.importar(caminho);
    confere(len(r.entidades) == 3, "3 entidades (%d)" % len(r.entidades));
    tipos = sorted(e["etype"] for e in r.entidades);
    confere(tipos == ["organization", "other", "person"], "tipos traduzidos do português: %s" % tipos);
    zeca = [e for e in r.entidades if e["text_label"] == "Zeca Silva"][0];
    confere(zeca["small_label"] == "ZS" and zeca["description"] == "Sócio", "apelido e descrição");

    print("\nCSV com vírgula e cabeçalho em inglês");
    caminho = gravar("en.csv", "name,type,alias\nJohn Doe,person,JD\nAcme Inc,organization,ACME\n");
    r = imp.importar(caminho);
    confere(len(r.entidades) == 2, "leu com vírgula e outras grafias de coluna");
    confere(r.entidades[0]["small_label"] == "JD", "'alias' reconhecido como apelido");

    print("\nCSV só de vínculos cria as pontas");
    caminho = gravar("vinculos.csv",
                     "de;para;verbo;inicio\n"
                     "Zeca Silva;Construtora X;dirige;2019-01-01\n"
                     "Ana Souza;Construtora X;assina;\n");
    r = imp.importar(caminho);
    confere(len(r.vinculos) == 2, "2 vínculos (%d)" % len(r.vinculos));
    confere(len(r.entidades) == 3, "3 entidades criadas das pontas, sem repetir a repetida (%d)"
            % len(r.entidades));
    confere(r.vinculos[0]["start_date"] == "2019-01-01", "data do vínculo veio");
    confere(len(r.avisos) > 0, "avisa que o tipo das entidades precisa de conferência");

    print("\nida e volta pelo nosso próprio export");
    mapa = MapRelationship();
    mapa.name = "Ida e volta";
    a = mapa.addEntity("person", 10, 10, text="Pessoa A");
    b = mapa.addEntity("organization", 200, 10, text="Empresa B");
    v = mapa.addEntity("link", 100, 50, text="dirige"); v.addFrom(a); v.addTo(b);
    arquivo = ed.exportar(mapa, os.path.join(TEMP, "volta"), formato="graphml")[0];
    r = imp.importar(arquivo);
    confere(len(r.entidades) == 2 and len(r.vinculos) == 1, "o que saiu voltou inteiro");
    nomes = sorted(e["text_label"] for e in r.entidades);
    confere(nomes == ["Empresa B", "Pessoa A"], "nomes preservados: %s" % nomes);
    confere(r.vinculos[0]["verbo"] == "dirige", "verbo preservado");
    confere(sorted(e["etype"] for e in r.entidades) == ["organization", "person"], "tipos preservados");

    print("\nGraphML de outra ferramenta");
    caminho = gravar("gephi.graphml",
                     '<?xml version="1.0" encoding="UTF-8"?>'
                     '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">'
                     '<key id="d0" for="node" attr.name="label" attr.type="string"/>'
                     '<graph edgedefault="undirected">'
                     '<node id="n0"><data key="d0">Alvo Um</data></node>'
                     '<node id="n1"><data key="d0">Alvo Dois</data></node>'
                     '<edge source="n0" target="n1"/>'
                     '<edge source="n0" target="FANTASMA"/>'
                     '</graph></graphml>');
    r = imp.importar(caminho);
    confere(len(r.entidades) == 2, "leu os nós com 'label' em vez de 'nome'");
    confere(len(r.vinculos) == 1, "aresta para nó inexistente foi ignorada, não importada torta");
    confere(r.vinculos[0]["verbo"] != "", "vínculo sem rótulo ganhou verbo padrão: %s" % r.vinculos[0]["verbo"]);

    print("\naplicar sem caixa de origem (é o caso da importação)");
    destino = MapRelationship();
    destino.name = "Destino";
    r = imp.importar(os.path.join(TEMP, "vinculos.csv"));
    escolhas = {e["chave"]: {"aceitar": True, "etype": e["etype"], "reusar": None} for e in r.entidades};
    rel = aplicar(destino, None, r, escolhas, [True] * len(r.vinculos));
    confere(rel["novas"] == 3, "criou as 3 entidades sem caixa de origem (%d)" % rel["novas"]);
    confere(rel["vinculos"] == 2, "e os 2 vínculos (%d)" % rel["vinculos"]);
    confere(destino.desfazer.count() == 1, "entrou como um passo de desfazer");
    caixas = [e for e in destino.elements if e.entity.etype != "link"];
    confere(all(c.x >= 0 and c.y >= 0 for c in caixas), "posicionou em coordenada positiva");

    print("\nrecusas");
    for nome, conteudo, trecho in [
        ("vazio.csv", "", "vazi"),
        ("so_cabecalho.csv", "nome;tipo\n", "cabeçalho"),
        ("sem_nome.csv", "coluna_estranha;outra\nx;y\n", "coluna de nome"),
    ]:
        try:
            imp.importar(gravar(nome, conteudo));
            confere(False, "deveria recusar " + nome);
        except imp.ErroImportacao as erro:
            confere(trecho.lower() in str(erro).lower(), "%s: %s" % (nome, erro));
    try:
        imp.importar(gravar("quebrado.graphml", "<graphml><nao fechado>"));
        confere(False, "deveria recusar XML quebrado");
    except imp.ErroImportacao as erro:
        confere("GraphML" in str(erro), "XML quebrado: %s" % str(erro)[:60]);
    try:
        imp.importar(os.path.join(TEMP, "nao_existe.csv"));
        confere(False, "deveria recusar arquivo inexistente");
    except imp.ErroImportacao as erro:
        confere("não encontrado" in str(erro), "arquivo inexistente");

    print("\nida e volta pelo CSV preserva as datas do vínculo");
    mapa3 = MapRelationship();
    mapa3.name = "Datas";
    pa = mapa3.addEntity("person", 0, 0, text="Pessoa A");
    pb = mapa3.addEntity("organization", 200, 0, text="Org B");
    elo = mapa3.addEntity("link", 100, 50, text="dirige");
    elo.addFrom(pa, start_date="2020-01-01", end_date="2021-02-03"); elo.addTo(pb);
    arquivos = ed.exportar(mapa3, os.path.join(TEMP, "idavolta"), formato="csv");
    r = imp.importar(arquivos[1]);   # o CSV de vínculos
    confere(len(r.vinculos) == 1, "um vínculo");
    confere(r.vinculos[0]["start_date"] == "2020-01-01",
            "a data de início sobreviveu (%s)" % r.vinculos[0]["start_date"]);
    confere(r.vinculos[0]["end_date"] == "2021-02-03",
            "e a de fim também (%s)" % r.vinculos[0]["end_date"]);

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
