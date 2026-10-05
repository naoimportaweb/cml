#!/usr/bin/env python3
# Teste do exportador de diagrama (SPEC.md §3.2). Monta um mapa de vinculos EM MEMORIA -- sem
# servidor, sem login -- e exporta nos tres formatos, conferindo o que importa:
#
#   - o arquivo existe e tem a assinatura do formato (bytes magicos, nao extensao);
#   - o SVG nao carrega script nem foreignObject, e rotulo com "<script>" sai ESCAPADO.
#     Isso e a lei do projeto: o SVG que a gente gera e seguro, o de fora e que nao entra.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/exportar_diagrama.py

import os, sys, inspect, tempfile;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
TEMP = tempfile.mkdtemp(prefix="cml_export_");
os.environ["HOME"] = TEMP;   # Configuration grava ~/.cml.json: isola do config real

from PySide6.QtWidgets import QApplication;

from classlib.relationship.maprelationship import MapRelationship;
from classlib import exportar_diagrama as ex;

FALHAS = [];


def confere(condicao, descricao):
    if condicao:
        print("  ok   %s" % descricao);
    else:
        print("  ERRO %s" % descricao);
        FALHAS.append(descricao);


def montar_mapa():
    mapa = MapRelationship();
    mapa.name = "Teste de exportação";
    # Nome hostil de proposito: tem que sair escapado no SVG, nunca como marcacao.
    pessoa = mapa.addEntity("person", 120, 120, text="<script>alert(1)</script>");
    org = mapa.addEntity("organization", 460, 260, text="Empresa X");
    vinculo = mapa.addEntity("link", 280, 190, text="dirige");
    vinculo.addFrom(pessoa);
    vinculo.addTo(org);
    return mapa;


def main():
    QApplication(sys.argv);
    mapa = montar_mapa();
    print("mapa em memoria: %d elements" % len(mapa.elements));

    print("\nPNG");
    caminho = ex.exportar(mapa, os.path.join(TEMP, "mapa"), formato="png");
    dados = open(caminho, "rb").read();
    confere(dados[:8] == b"\x89PNG\r\n\x1a\n", "assinatura PNG");
    confere(len(dados) > 2000, "tem conteudo (%d bytes)" % len(dados));

    print("\nPDF");
    caminho = ex.exportar(mapa, os.path.join(TEMP, "mapa"), formato="pdf");
    dados = open(caminho, "rb").read();
    confere(dados[:5] == b"%PDF-", "assinatura %PDF-");
    confere(len(dados) > 1000, "tem conteudo (%d bytes)" % len(dados));

    print("\nSVG");
    caminho = ex.exportar(mapa, os.path.join(TEMP, "mapa"), formato="svg");
    texto = open(caminho, encoding="utf-8").read();
    confere("<svg" in texto, "tem raiz <svg");
    confere("<text" in texto, "texto saiu como <text> (vetor, nao bitmap)");
    confere("&lt;script&gt;" in texto, "rotulo hostil veio ESCAPADO (&lt;script&gt;)");
    confere("<script" not in texto.lower(), "nenhum <script> real no arquivo");
    confere("foreignobject" not in texto.lower(), "nenhum <foreignObject>");
    confere("xlink:href=\"http" not in texto.lower(), "nenhuma referencia externa http");

    print("\nformato invalido");
    try:
        ex.exportar(mapa, os.path.join(TEMP, "mapa.bmp"));
        confere(False, "deveria recusar .bmp");
    except ex.ErroExportacao as erro:
        confere("bmp" in str(erro), "recusou .bmp com mensagem clara: %s" % erro);

    print("\nmapa vazio");
    try:
        ex.exportar(MapRelationship(), os.path.join(TEMP, "vazio.png"));
        confere(False, "deveria recusar mapa sem caixa");
    except ex.ErroExportacao as erro:
        confere(True, "recusou mapa vazio: %s" % erro);

    print("\nextensao ausente ganha a do formato");
    caminho = ex.exportar(mapa, os.path.join(TEMP, "sem_extensao"), formato="png");
    confere(caminho.endswith(".png") and os.path.exists(caminho), "virou %s" % os.path.basename(caminho));

    print("\nnome de arquivo sugerido");
    confere(ex.nome_de_arquivo(mapa) == "Teste_de_exportação", "nome limpo: %s" % ex.nome_de_arquivo(mapa));

    print("\n%s" % ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    print("arquivos em %s" % TEMP);
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
