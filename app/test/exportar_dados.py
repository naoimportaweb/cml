#!/usr/bin/env python3
# Teste do export de DADO (CSV e GraphML) -- SPEC.md §6. Mapa EM MEMORIA, sem servidor.
#
# O que importa:
#   - duas tabelas separadas, porque as colunas de entidade nao sao as de vinculo;
#   - hiper-aresta vira UMA LINHA POR PAR (planilha e GraphML não sabem o que e isso);
#   - data suja nao vai para o arquivo;
#   - o GraphML e XML bem formado, com as datas e a contagem de referencias como atributo;
#   - nome com ";" , aspas e "<" nao quebra nem o CSV nem o XML.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/exportar_dados.py

import os, sys, inspect, tempfile, csv;
from xml.etree import ElementTree;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
TEMP = tempfile.mkdtemp(prefix="cml_dados_");
os.environ["HOME"] = TEMP;

from PySide6.QtWidgets import QApplication;

from classlib.relationship.maprelationship import MapRelationship;
from classlib import exportar_dados as ed;

FALHAS = [];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def montar():
    mapa = MapRelationship();
    mapa.name = "Operação Teste";
    # Nome hostil: ponto-e-virgula quebra CSV mal feito, "<" quebra XML mal feito.
    zeca = mapa.addEntity("person", 100, 100, text='Zeca "O Chefe"; Silva <chefe>');
    zeca.start_date = "2019-01-01"; zeca.end_date = "0000-00-00";   # fim sujo
    ana = mapa.addEntity("person", 300, 100, text="Ana Souza");
    org = mapa.addEntity("organization", 500, 300, text="Construtora X");
    org.entity.small_label = "CX";
    org.entity.references = [object(), object()];
    v = mapa.addEntity("link", 250, 200, text="dirige");
    v.addFrom(zeca, start_date="2020-01-01", end_date=None);
    v.addTo(org);
    # hiper-aresta: duas pontas de um lado
    v2 = mapa.addEntity("link", 350, 250, text="assina");
    v2.addFrom(zeca); v2.addFrom(ana); v2.addTo(org);
    return mapa, zeca, ana, org, v, v2;


def main():
    QApplication(sys.argv);
    mapa, zeca, ana, org, v, v2 = montar();

    print("CSV: dois arquivos");
    gravados = ed.exportar(mapa, os.path.join(TEMP, "mapa"), formato="csv");
    confere(len(gravados) == 2, "gravou dois arquivos");
    confere(all(os.path.exists(g) for g in gravados), "os dois existem no disco");

    with open(gravados[0], encoding="utf-8-sig") as arquivo:
        entidades = list(csv.reader(arquivo, delimiter=";"));
    with open(gravados[1], encoding="utf-8-sig") as arquivo:
        vinculos = list(csv.reader(arquivo, delimiter=";"));

    confere(entidades[0] == ed.COLUNAS_ENTIDADE, "cabecalho de entidades");
    confere(len(entidades) == 4, "3 entidades + cabecalho (%d)" % len(entidades));
    linha_org = [l for l in entidades[1:] if l[3] == "Construtora X"][0];
    confere(linha_org[4] == "CX", "apelido na coluna certa");
    confere(linha_org[5] == "3", "grau conta as 3 ARESTAS que tocam a organizacao (hiper-aresta expandida)");
    confere(linha_org[6] == "2", "contagem de referencias");

    linha_zeca = [l for l in entidades[1:] if l[3].startswith("Zeca")][0];
    confere(";" in linha_zeca[3], "nome com ponto-e-virgula sobreviveu intacto ao CSV");
    confere(linha_zeca[8] == "2019-01-01", "data boa foi");
    confere(linha_zeca[9] == "", "data suja (0000-00-00) NAO foi");

    print("\nhiper-aresta vira uma linha por par");
    confere(len(vinculos) == 4, "3 pares + cabecalho (%d)" % len(vinculos));
    assina = [l for l in vinculos[1:] if l[1] == "assina"];
    confere(len(assina) == 2, "o vinculo de duas pontas virou 2 linhas");
    confere(len(set(l[0] for l in assina)) == 2, "e cada linha tem id proprio (sufixo)");
    dirige = [l for l in vinculos[1:] if l[1] == "dirige"][0];
    confere(dirige[6] == "2020-01-01", "periodo da ponta DE foi junto");
    confere(dirige[4] == zeca.id and dirige[5] == org.id, "os ids das pontas batem com o modelo");

    print("\nGraphML");
    gravados = ed.exportar(mapa, os.path.join(TEMP, "mapa"), formato="graphml");
    arvore = ElementTree.parse(gravados[0]);   # so parseia se for XML bem formado
    raiz = arvore.getroot();
    ns = "{http://graphml.graphdrawing.org/xmlns}";
    nos = raiz.findall(".//%snode" % ns);
    arestas = raiz.findall(".//%sedge" % ns);
    confere(len(nos) == 3, "3 nos (%d)" % len(nos));
    confere(len(arestas) == 3, "3 arestas, uma por par (%d)" % len(arestas));

    ids = [n.get("id") for n in nos];
    confere(all(a.get("source") in ids and a.get("target") in ids for a in arestas),
            "toda aresta liga nos que existem (nenhuma ponta solta)");

    def dado(elemento, chave):
        for d in elemento.findall("%sdata" % ns):
            if d.get("key") == "d_" + chave:
                return d.text or "";
        return None;

    no_zeca = [n for n in nos if (dado(n, "nome") or "").startswith("Zeca")][0];
    confere("<chefe>" in dado(no_zeca, "nome"), "'<' no nome foi escapado e voltou intacto");
    confere(dado(no_zeca, "fim") == "", "data suja nao virou atributo");
    no_org = [n for n in nos if dado(n, "nome") == "Construtora X"][0];
    confere(dado(no_org, "vinculos") == "3", "grau virou atributo do no");
    confere(dado(no_org, "referencias") == "2", "referencias viraram atributo do no");
    confere(dado(arestas[0], "verbo") != None, "a aresta carrega o verbo");

    print("\nSTIX 2.1");
    import json, re as _re;
    mapa2 = MapRelationship();
    mapa2.name = "CTI";
    # id em formato UUID = origem MISP (convencao do projeto); o export tem de REAPROVEITA-lo
    ator = mapa2.addEntity("other", 10, 10, text="APT-Exemplo");
    ator.entity.id = "9f1c6f58-6c4e-4c2a-9a1e-1b2c3d4e5f60";
    ator.entity.sub_etype_name = "threat actor";
    ator.start_date = "2018-04-02";
    praga = mapa2.addEntity("other", 200, 10, text="MalwareX");
    praga.entity.sub_etype_name = "ransomware";
    pessoa = mapa2.addEntity("person", 10, 200, text="Fulano");
    elo = mapa2.addEntity("link", 100, 100, text="usa o");
    elo.addFrom(ator, start_date="2020-01-01", end_date="2021-06-30"); elo.addTo(praga);

    caminho = ed.exportar(mapa2, os.path.join(TEMP, "cti"), formato="stix")[0];
    bundle = json.load(open(caminho, encoding="utf-8"));
    confere(bundle["type"] == "bundle" and bundle["id"].startswith("bundle--"), "é um bundle STIX");
    por_tipo = {};
    for o in bundle["objects"]:
        por_tipo.setdefault(o["type"], []).append(o);
    confere("threat-actor" in por_tipo, "sub-tipo 'threat actor' virou threat-actor");
    confere("malware" in por_tipo, "'ransomware' virou malware");
    confere(por_tipo["malware"][0].get("is_family") is True, "malware tem is_family (obrigatório no 2.1)");
    confere("identity" in por_tipo, "pessoa virou identity");
    confere(por_tipo["identity"][0]["identity_class"] == "individual", "com identity_class individual");

    objeto_ator = por_tipo["threat-actor"][0];
    confere(objeto_ator["id"] == "threat-actor--9f1c6f58-6c4e-4c2a-9a1e-1b2c3d4e5f60",
            "o UUID do MISP foi REAPROVEITADO no id STIX");
    confere(objeto_ator.get("first_seen") == "2018-04-02T00:00:00.000Z", "data virou first_seen");
    confere(all(o.get("spec_version") == "2.1" for o in bundle["objects"]), "todos marcam spec_version 2.1");

    relacoes = por_tipo.get("relationship", []);
    confere(len(relacoes) == 1, "um relationship (%d)" % len(relacoes));
    confere(relacoes[0]["relationship_type"] == "usa-o", "verbo virou relationship_type válido: %s"
            % relacoes[0]["relationship_type"]);
    confere(relacoes[0]["start_time"] == "2020-01-01T00:00:00.000Z", "start_time da ponta");
    confere(relacoes[0]["stop_time"] == "2021-06-30T00:00:00.000Z", "stop_time da ponta");
    ids = set(o["id"] for o in bundle["objects"]);
    confere(relacoes[0]["source_ref"] in ids and relacoes[0]["target_ref"] in ids,
            "as duas pontas apontam para objetos do próprio bundle");
    confere(all(_re.match(r"^[a-z0-9-]+--[0-9a-f-]{36}$", o["id"]) for o in bundle["objects"]),
            "todo id no formato tipo--uuid");

    print("\nSTIX é determinístico");
    outro = ed.exportar(mapa2, os.path.join(TEMP, "cti2"), formato="stix")[0];
    b2 = json.load(open(outro, encoding="utf-8"));
    ids2 = set(o["id"] for o in b2["objects"]);
    confere(ids == ids2, "exportar duas vezes dá os mesmos ids de objeto");

    print("\nrecusas");
    try:
        ed.exportar(mapa, os.path.join(TEMP, "x.xlsx"));
        confere(False, "deveria recusar formato desconhecido");
    except ed.ErroExportacao as erro:
        confere("xlsx" in str(erro), "recusou formato: %s" % erro);
    try:
        ed.exportar(MapRelationship(), os.path.join(TEMP, "vazio.csv"));
        confere(False, "deveria recusar mapa vazio");
    except ed.ErroExportacao as erro:
        confere(True, "recusou mapa vazio: %s" % erro);

    print("\nvinculo sem ponta nao vira linha torta");
    solto = MapRelationship();
    solto.addEntity("person", 0, 0, text="Sozinho");
    solto.addEntity("link", 10, 10, text="orfao");
    gravados = ed.exportar(solto, os.path.join(TEMP, "solto"), formato="graphml");
    raiz = ElementTree.parse(gravados[0]).getroot();
    confere(len(raiz.findall(".//%sedge" % ns)) == 0, "vinculo sem ponta foi ignorado, nao exportado quebrado");

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    print("arquivos em %s" % TEMP);
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
