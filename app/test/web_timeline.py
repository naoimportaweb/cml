#!/usr/bin/env python3
# Compara a projecao de datas da timeline do DESKTOP (Python) com a da WEB (PHP).
#
# Mesma razao do web_organograma.py: o dono escolheu reimplementar os diagramas na web
# (SPEC.md §11), entao o mesmo algoritmo vive em dois lugares e precisa de algo que vigie.
#
# O que se compara NAO e o desenho -- a metrica de fonte do Qt e a do canvas nunca vao bater
# ao pixel, e exigir isso seria um teste que falha por motivo errado. Compara-se o que mais
# dói quando diverge: QUAIS EVENTOS EXISTEM. Ou seja, a limpeza de data suja, a inversao de
# periodo invertido, o dedup por prioridade de origem e a ordem de leitura.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/web_timeline.py
#
# Precisa de `php` no PATH; sem ele o teste avisa e nao falha.

import os, sys, inspect, json, shutil, subprocess, tempfile;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
REPO = os.path.dirname(ROOT);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
os.environ["HOME"] = tempfile.mkdtemp(prefix="cml_webtl_");

MODELO_PHP = os.path.join(REPO, "server", "webpage", "model", "timeline", "timeline.php");

FALHAS = [];

# (origem, titulo, detalhe, inicio, fim) -- com os casos tortos de propósito.
BRUTOS = [
    ("elemento",      "Zeca Silva",   "no mapa", "2019-01-01", "2022-12-31"),
    ("entidade",      "Zeca Silva",   "",        "2019-01-01", "2022-12-31"),  # mesma coisa: dedup
    ("evento",        "Busca e apreensão", "PF", "2021-05-10", None),
    ("referencia",    "Reportagem X", "Zeca",    "2020-03-02", None),
    ("vinculo",       "dirige",       "A → B",   "2003-01-01", "1998-01-01"),  # periodo invertido
    ("classificacao", "Zeca — Cargo: Diretor", "Zeca", "0000-00-00", "2010-01-01"),  # data suja
    ("entidade",      "Sem data",     "",        None,         None),           # nao vira evento
    ("elemento",      "Só fim",       "no mapa", "",           "2015-07-07"),   # so o fim
    ("referencia",    "Reportagem X", "Zeca",    "2020-03-02", None),           # repetida
];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def normalizar_python(origem, titulo, detalhe, inicio, fim):
    """Aplica as MESMAS regras do TimelineEvent.novo do desktop, usando o parse_data dele."""
    from classlib.timeline.timeline_event import parse_data;
    ini, f = parse_data(inicio), parse_data(fim);
    if ini == None and f == None:
        return None;
    if ini == None:
        ini, f = f, None;
    if f != None and f < ini:
        ini, f = f, ini;
    return {"origem": origem, "titulo": titulo.strip(), "detalhe": (detalhe or "").strip(),
            "inicio": ini.isoformat(), "fim": f.isoformat() if f != None else None};


def consolidar_python(brutos):
    from classlib.timeline.timeline_event import PRIORIDADE_ORIGEM;
    def prioridade(e):
        return PRIORIDADE_ORIGEM.index(e["origem"]) if e["origem"] in PRIORIDADE_ORIGEM else len(PRIORIDADE_ORIGEM);
    escolhidos = {};
    for e in brutos:
        if e == None:
            continue;
        chave = "%s|%s|%s" % (e["titulo"], e["inicio"], e["fim"] if e["fim"] != None else "");
        atual = escolhidos.get(chave);
        if atual == None or prioridade(e) < prioridade(atual):
            escolhidos[chave] = e;
    saida = list(escolhidos.values());
    saida.sort(key=lambda e: (e["inicio"], e["fim"] or e["inicio"], e["titulo"]));
    return saida;


def rodar_php():
    if shutil.which("php") == None:
        return None;
    programa = """<?php
require_once %s;
$brutos = [];
foreach( json_decode(%s, true) as $r ){
    array_push( $brutos, Timeline::normalizar($r[0], $r[1], $r[2], $r[3], $r[4]) );
}
echo json_encode( Timeline::consolidar( $brutos ) );
""" % (json.dumps(MODELO_PHP), json.dumps(json.dumps(BRUTOS)));
    with tempfile.NamedTemporaryFile("w", suffix=".php", delete=False, encoding="utf-8") as arquivo:
        arquivo.write(programa);
        caminho = arquivo.name;
    try:
        saida = subprocess.run(["php", caminho], capture_output=True, text=True, timeout=60);
        if saida.returncode != 0:
            raise Exception((saida.stderr or saida.stdout).strip()[:400]);
        return json.loads(saida.stdout.strip());
    finally:
        os.unlink(caminho);


def main():
    from PySide6.QtWidgets import QApplication;
    QApplication.instance() or QApplication(sys.argv);

    print("desktop (Python)");
    py = consolidar_python([normalizar_python(*b) for b in BRUTOS]);
    confere(len(py) > 0, "%d eventos depois do dedup" % len(py));

    print("\nweb (PHP, lido do model/timeline/timeline.php)");
    try:
        php = rodar_php();
    except Exception as erro:
        confere(False, "o PHP do modelo não rodou: %s" % erro);
        php = None;
    if php == None and shutil.which("php") == None:
        print("  --   php não encontrado: comparação pulada");
        print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
        return 1 if len(FALHAS) > 0 else 0;

    if php != None:
        confere(len(php) == len(py), "mesma quantidade de eventos (web %d, desktop %d)" % (len(php), len(py)));

        print("\nos dois concordam, evento a evento");
        def simples(lista):
            return [(e["origem"], e["titulo"], e["inicio"], e["fim"]) for e in lista];
        a, b = simples(py), simples(php);
        divergentes = [str(x) + " != " + str(y) for x, y in zip(a, b) if x != y];
        confere(a == b, "nenhuma divergência" if a == b else "DIVERGIRAM: " + "; ".join(divergentes[:3]));

        print("\ne as regras que importam valem nos dois");
        titulos = [e["titulo"] for e in php];
        confere("Sem data" not in titulos, "evento sem data nenhuma não entra");
        confere(titulos.count("Reportagem X") == 1, "repetida entrou uma vez só");
        zeca = [e for e in php if e["titulo"] == "Zeca Silva"];
        confere(len(zeca) == 1 and zeca[0]["origem"] == "entidade",
                "entre 'elemento' e 'entidade' idênticos fica o de maior prioridade (%s)"
                % (zeca[0]["origem"] if zeca else "—"));
        vinculo = [e for e in php if e["titulo"] == "dirige"][0];
        confere(vinculo["inicio"] == "1998-01-01" and vinculo["fim"] == "2003-01-01",
                "período invertido foi normalizado (%s → %s)" % (vinculo["inicio"], vinculo["fim"]));
        classif = [e for e in php if e["titulo"].startswith("Zeca — Cargo")][0];
        confere(classif["inicio"] == "2010-01-01" and classif["fim"] == None,
                "data suja virou evento pontual na data boa");
        so_fim = [e for e in php if e["titulo"] == "Só fim"][0];
        confere(so_fim["inicio"] == "2015-07-07" and so_fim["fim"] == None,
                "só o fim preenchido vira marco naquela data");
        inicios = [e["inicio"] for e in php];
        confere(inicios == sorted(inicios), "ordenados por início: %s" % inicios);

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
