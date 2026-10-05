# Exporta o mapa de vinculos como DADO: CSV e GraphML (SPEC.md §6).
#
# O exportar_diagrama.py tira uma figura; este tira a informacao. Era a lacuna que sobrava
# contra Maltego e Siren: dava para entregar o desenho, nao dava para levar o mapa a outra
# ferramenta (Gephi, yEd, Cytoscape, planilha).
#
# Duas decisoes:
#   - CSV sao DOIS arquivos (entidades e vinculos), porque as colunas de um nao sao as do outro
#     -- a mesma razao das duas abas da List View. Juntar numa planilha so daria metade das
#     colunas vazias em cada linha.
#   - GraphML carrega as datas e a contagem de referencias como atributo, nao so o nome: mapa
#     sem data e sem fonte, aberto no Gephi, perde justamente o que o CML tem de diferente.
#
# Formatos que ainda faltam: STIX 2.1 (casa com a origem MISP) e JSON proprio.

import csv, os, sys, inspect, re;
from xml.sax.saxutils import escape, quoteattr;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append(os.path.dirname(CURRENTDIR));

FORMATOS = ("csv", "graphml");
SUJO = ("", "0000-00-00", "none", "null");

COLUNAS_ENTIDADE = ["id", "tipo", "sub_tipo", "nome", "apelido", "vinculos", "referencias",
                    "classificacoes", "inicio", "fim", "wikipedia", "url", "descricao"];
COLUNAS_VINCULO = ["id", "verbo", "de", "para", "de_id", "para_id",
                   "inicio_de", "fim_de", "inicio_para", "fim_para", "referencias"];


class ErroExportacao(Exception):
    pass;


def data_limpa(valor):
    texto = str(valor or "").strip();
    return "" if texto.lower() in SUJO else texto;


def __texto__(valor):
    return " ".join(str(valor or "").split());


def caixas(mapa):
    return [e for e in mapa.elements if e.entity.etype != "link"];


def vinculos(mapa):
    return [e for e in mapa.elements if e.entity.etype == "link"];


def __pares__(vinculo):
    """Um vinculo com varias pontas de cada lado vira uma LINHA POR PAR: planilha e GraphML
    nao sabem o que e hiper-aresta, e inventar uma linha com 'A, B' no campo nao e dado, e
    texto."""
    de = [p for p in vinculo.from_entity if p.entity != None];
    para = [p for p in vinculo.to_entity if p.entity != None];
    if len(de) == 0 or len(para) == 0:
        return [];
    saida = [];
    for a in de:
        for b in para:
            saida.append((a, b));
    return saida;


def grau(mapa, caixa):
    """Quantas ARESTAS do arquivo exportado tocam esta caixa.

    Conta os PARES, nao os vinculos: um vinculo com duas pontas de um lado vira duas arestas
    no GraphML, e o no dizendo "1" com o grafo tendo 2 arestas e o tipo de desencontro que faz
    o Gephi discordar do proprio arquivo. A coluna "Vínculos" da List View conta outra coisa
    -- quantos vinculos tocam a caixa, que e o que vale no mapa, onde o vinculo e UM objeto."""
    total = 0;
    for vinculo in vinculos(mapa):
        for a, b in __pares__(vinculo):
            if a.entity is caixa:
                total = total + 1;
            if b.entity is caixa:
                total = total + 1;
    return total;


def __linha_entidade__(mapa, caixa):
    entidade = caixa.entity;
    return [caixa.id, entidade.etype or "", entidade.sub_etype_name or "",
            __texto__(entidade.text), __texto__(entidade.small_label),
            grau(mapa, caixa), len(entidade.references or []), len(entidade.classification or []),
            data_limpa(caixa.start_date), data_limpa(caixa.end_date),
            entidade.wikipedia or "", entidade.default_url or "",
            __texto__(entidade.full_description)];


def __linhas_vinculo__(vinculo):
    linhas = [];
    pares = __pares__(vinculo);
    for i in range(len(pares)):
        a, b = pares[i];
        # Varios pares no mesmo vinculo: o id ganha sufixo, para a chave continuar unica.
        identificador = vinculo.id if len(pares) == 1 else "%s#%d" % (vinculo.id, i + 1);
        linhas.append([identificador, __texto__(vinculo.entity.text),
                       __texto__(a.entity.entity.text), __texto__(b.entity.entity.text),
                       a.entity.id, b.entity.id,
                       data_limpa(a.start_date), data_limpa(a.end_date),
                       data_limpa(b.start_date), data_limpa(b.end_date),
                       len(vinculo.entity.references or [])]);
    return linhas;


def para_csv(mapa, caminho):
    """Grava dois arquivos: <caminho>_entidades.csv e <caminho>_vinculos.csv. Devolve a lista
    dos caminhos gravados."""
    base = re.sub(r"\.csv$", "", caminho, flags=re.I);
    alvo_entidades = base + "_entidades.csv";
    alvo_vinculos = base + "_vinculos.csv";
    try:
        # utf-8-sig: sem o BOM o Excel abre acentuacao errada, e planilha e o destino numero um.
        with open(alvo_entidades, "w", newline="", encoding="utf-8-sig") as arquivo:
            escritor = csv.writer(arquivo, delimiter=";");
            escritor.writerow(COLUNAS_ENTIDADE);
            for caixa in caixas(mapa):
                escritor.writerow(__linha_entidade__(mapa, caixa));
        with open(alvo_vinculos, "w", newline="", encoding="utf-8-sig") as arquivo:
            escritor = csv.writer(arquivo, delimiter=";");
            escritor.writerow(COLUNAS_VINCULO);
            for vinculo in vinculos(mapa):
                for linha in __linhas_vinculo__(vinculo):
                    escritor.writerow(linha);
    except OSError as erro:
        raise ErroExportacao("Não foi possível gravar o CSV: %s" % erro);
    return [alvo_entidades, alvo_vinculos];


CHAVES_NO = [("nome", "string"), ("tipo", "string"), ("sub_tipo", "string"), ("apelido", "string"),
             ("vinculos", "int"), ("referencias", "int"), ("inicio", "string"), ("fim", "string"),
             ("url", "string")];
CHAVES_ARESTA = [("verbo", "string"), ("inicio_de", "string"), ("fim_de", "string"),
                 ("inicio_para", "string"), ("fim_para", "string"), ("referencias", "int")];


def __dado__(chave, valor):
    return '      <data key=%s>%s</data>' % (quoteattr("d_" + chave), escape(str(valor)));


def para_graphml(mapa, caminho):
    """GraphML dirigido, com as datas e a contagem de referencias como atributo -- e o que o
    Gephi/yEd/Cytoscape leem direto."""
    if not caminho.lower().endswith(".graphml"):
        caminho = caminho + ".graphml";
    partes = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">'];
    for chave, tipo in CHAVES_NO:
        partes.append('  <key id="d_%s" for="node" attr.name="%s" attr.type="%s"/>' % (chave, chave, tipo));
    for chave, tipo in CHAVES_ARESTA:
        partes.append('  <key id="d_%s" for="edge" attr.name="%s" attr.type="%s"/>' % (chave, chave, tipo));
    partes.append('  <graph id=%s edgedefault="directed">' % quoteattr(__texto__(mapa.getName()) or "mapa"));

    for caixa in caixas(mapa):
        entidade = caixa.entity;
        partes.append('    <node id=%s>' % quoteattr(caixa.id));
        for chave, valor in [("nome", __texto__(entidade.text)), ("tipo", entidade.etype or ""),
                             ("sub_tipo", entidade.sub_etype_name or ""),
                             ("apelido", __texto__(entidade.small_label)),
                             ("vinculos", grau(mapa, caixa)),
                             ("referencias", len(entidade.references or [])),
                             ("inicio", data_limpa(caixa.start_date)),
                             ("fim", data_limpa(caixa.end_date)),
                             ("url", entidade.default_url or "")]:
            partes.append(__dado__(chave, valor));
        partes.append('    </node>');

    for vinculo in vinculos(mapa):
        linhas = __linhas_vinculo__(vinculo);
        for linha in linhas:
            partes.append('    <edge id=%s source=%s target=%s>'
                          % (quoteattr(linha[0]), quoteattr(linha[4]), quoteattr(linha[5])));
            for chave, valor in [("verbo", linha[1]), ("inicio_de", linha[6]), ("fim_de", linha[7]),
                                 ("inicio_para", linha[8]), ("fim_para", linha[9]),
                                 ("referencias", linha[10])]:
                partes.append(__dado__(chave, valor));
            partes.append('    </edge>');

    partes.append('  </graph>');
    partes.append('</graphml>');
    try:
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write("\n".join(partes) + "\n");
    except OSError as erro:
        raise ErroExportacao("Não foi possível gravar o GraphML: %s" % erro);
    return [caminho];


def exportar(mapa, caminho, formato=None):
    if mapa == None:
        raise ErroExportacao("Nenhum mapa aberto.");
    if len(mapa.elements) == 0:
        raise ErroExportacao("O mapa não tem nada para exportar.");
    if formato == None:
        formato = os.path.splitext(caminho)[1].lstrip(".").lower();
    formato = (formato or "").lower();
    if formato not in FORMATOS:
        raise ErroExportacao("Formato não suportado: %s (use csv ou graphml)." % (formato or "?"));
    return para_csv(mapa, caminho) if formato == "csv" else para_graphml(mapa, caminho);
