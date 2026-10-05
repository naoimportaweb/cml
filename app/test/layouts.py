#!/usr/bin/env python3
# Teste dos layouts automaticos (SPEC.md §3.3). Mapa EM MEMORIA, sem servidor.
#
# O que todo layout tem de cumprir, seja qual for o algoritmo:
#   - mexe em TODAS as caixas e em nenhum vinculo diretamente;
#   - deixa tudo em coordenada positiva (o modelo e o banco nunca tiveram x/y negativo);
#   - nao empilha duas caixas no mesmo ponto;
#   - poe a caixa do verbo ENTRE as pontas que ela liga;
#   - entra como UM passo de desfazer, e desfazer devolve a posicao manual intacta;
#   - recusa mapa travado.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/layouts.py

import os, sys, inspect, tempfile;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
os.environ["HOME"] = tempfile.mkdtemp(prefix="cml_layout_");

from PySide6.QtWidgets import QApplication;

from classlib.relationship.maprelationship import MapRelationship;
from classlib.relationship import layouts;

FALHAS = [];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def montar(n=9):
    mapa = MapRelationship();
    mapa.name = "Layouts";
    centro = mapa.addEntity("organization", 500, 500, text="Construtora X");
    centro.w = 110; centro.h = 20;
    folhas = [];
    for i in range(n):
        caixa = mapa.addEntity("person" if i % 2 == 0 else "other", 100 + i, 100 + i,
                               text="Pessoa %d" % i);
        caixa.w = 90; caixa.h = 20;
        folhas.append(caixa);
        elo = mapa.addEntity("link", 300, 300, text="liga");
        elo.w = 50; elo.h = 20;
        elo.addFrom(caixa); elo.addTo(centro);
    # uma caixa solta, sem vinculo nenhum: layout nao pode esquecer dela
    solta = mapa.addEntity("other", 700, 700, text="Avulsa");
    solta.w = 80; solta.h = 20;
    mapa.desfazer.clear();
    return mapa, centro, folhas, solta;


def sobrepostas(lista):
    pares = 0;
    for i in range(len(lista)):
        for j in range(i + 1, len(lista)):
            a, b = lista[i], lista[j];
            if abs(a.x - b.x) < 5 and abs(a.y - b.y) < 5:
                pares = pares + 1;
    return pares;


def main():
    QApplication(sys.argv);

    for nome, rotulo in layouts.LAYOUTS:
        print("\n%s" % rotulo);
        mapa, centro, folhas, solta = montar();
        caixas = layouts.caixas(mapa);
        antes = {c: (c.x, c.y) for c in caixas};

        quantas = layouts.aplicar(mapa, nome);
        confere(quantas == len(caixas), "mexeu nas %d caixas" % len(caixas));
        confere(all(c.x >= 0 and c.y >= 0 for c in mapa.elements),
                "nenhuma coordenada negativa (min x=%d, y=%d)"
                % (min(c.x for c in mapa.elements), min(c.y for c in mapa.elements)));
        confere(sobrepostas(caixas) == 0, "nenhuma caixa empilhada em cima de outra");
        confere(any((c.x, c.y) != antes[c] for c in caixas), "as posicoes realmente mudaram");
        confere(solta.x >= 0 and solta.y >= 0, "a caixa sem vinculo tambem foi posicionada");

        # o verbo tem de cair entre as pontas que ele liga
        fora = 0;
        for vinculo in layouts.vinculos(mapa):
            pontas = [p.entity for p in list(vinculo.to_entity) + list(vinculo.from_entity)];
            menor_x = min(p.x for p in pontas); maior_x = max(p.x + (p.w or 0) for p in pontas);
            menor_y = min(p.y for p in pontas); maior_y = max(p.y + (p.h or 0) for p in pontas);
            meio_x = vinculo.x + (vinculo.w or 0) / 2.0;
            meio_y = vinculo.y + (vinculo.h or 0) / 2.0;
            if not (menor_x - 1 <= meio_x <= maior_x + 1 and menor_y - 1 <= meio_y <= maior_y + 1):
                fora = fora + 1;
        confere(fora == 0, "todo verbo caiu entre as suas pontas (%d fora)" % fora);

        confere(mapa.desfazer.count() == 1, "empilhou UM passo (%d)" % mapa.desfazer.count());
        mapa.desfazer.undo();
        confere(all((c.x, c.y) == antes[c] for c in caixas),
                "desfazer devolveu a posicao manual de todas as caixas");

    print("\nortogonal cai na grade");
    mapa, centro, folhas, solta = montar();
    layouts.aplicar(mapa, "ortogonal");
    fora_da_grade = [c for c in layouts.caixas(mapa) if c.x % layouts.GRADE != 0 or c.y % layouts.GRADE != 0];
    confere(len(fora_da_grade) == 0, "todas as caixas em multiplos de %d" % layouts.GRADE);

    print("\norganico e repetivel");
    m1, _, _, _ = montar(); layouts.aplicar(m1, "organico");
    m2, _, _, _ = montar(); layouts.aplicar(m2, "organico");
    iguais = all((a.x, a.y) == (b.x, b.y) for a, b in zip(layouts.caixas(m1), layouts.caixas(m2)));
    confere(iguais, "mesma semente, mesmo desenho (nao sorteia diferente a cada clique)");

    print("\nmapa travado");
    mapa, centro, folhas, solta = montar();
    mapa.locked = True;
    posicoes = {c: (c.x, c.y) for c in layouts.caixas(mapa)};
    try:
        layouts.aplicar(mapa, "circular");
        confere(False, "deveria recusar mapa travado");
    except Exception as erro:
        confere("travado" in str(erro), "recusou com mensagem clara: %s" % erro);
    confere(all((c.x, c.y) == posicoes[c] for c in layouts.caixas(mapa)), "e nao mexeu em nada");

    print("\nmapa vazio e layout desconhecido");
    confere(layouts.aplicar(MapRelationship(), "circular") == 0, "mapa vazio devolve 0, sem quebrar");
    try:
        layouts.aplicar(montar()[0], "espiral");
        confere(False, "deveria recusar layout desconhecido");
    except ValueError as erro:
        confere("espiral" in str(erro), "recusou layout desconhecido: %s" % erro);

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
