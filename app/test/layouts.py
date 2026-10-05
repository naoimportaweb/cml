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

from PySide6.QtGui import QPainter, QPixmap;

from classlib.relationship.maprelationship import MapRelationship;
from classlib.relationship import layouts;
from classlib.exportar_diagrama import fonte_do_diagrama;


def recalcular(mapa):
    """Define w/h de cada caixa pela metrica da fonte, como o canvas faz antes de desenhar.
    Sem isto todas ficam com a largura PADRAO e o teste de colisao mente -- foi o que me
    escondeu o defeito dos rotulos empilhados."""
    rascunho = QPixmap(1, 1);
    painter = QPainter();
    painter.begin(rascunho);
    painter.setFont(fonte_do_diagrama());
    for elemento in mapa.elements:
        elemento.recalc(painter);
    painter.end();

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

    print("\nespalhar: as promessas dele");

    def retangulos(mapa):
        return [(e, (e.x, e.y, e.w or 1, e.h or 1)) for e in mapa.elements];

    def colisoes(mapa, folga=0):
        pares = 0;
        itens = retangulos(mapa);
        for i in range(len(itens)):
            for j in range(i + 1, len(itens)):
                a1, b1 = itens[i][1], itens[j][1];
                if not (a1[0] + a1[2] + folga <= b1[0] or b1[0] + b1[2] + folga <= a1[0] or
                        a1[1] + a1[3] + folga <= b1[1] or b1[1] + b1[3] + folga <= a1[1]):
                    pares = pares + 1;
        return pares;

    def arvore():
        # DAG de verdade: raiz -> dois -> quatro. Aqui a regra "de cima aponta para baixo"
        # tem de valer para TODA aresta.
        mapa = MapRelationship();
        mapa.name = "Árvore";
        raiz = mapa.addEntity("organization", 0, 0, text="Holding"); raiz.w = 110; raiz.h = 20;
        nivel1 = [];
        for nome in ("Alfa", "Beta"):
            caixa = mapa.addEntity("organization", 0, 0, text=nome); caixa.w = 90; caixa.h = 20;
            elo = mapa.addEntity("link", 0, 0, text="controla"); elo.w = 70; elo.h = 20;
            elo.addFrom(raiz); elo.addTo(caixa);
            nivel1.append(caixa);
        for i in range(4):
            caixa = mapa.addEntity("person", 0, 0, text="Sócio %d" % i); caixa.w = 90; caixa.h = 20;
            elo = mapa.addEntity("link", 0, 0, text="dirige"); elo.w = 60; elo.h = 20;
            elo.addFrom(nivel1[i % 2]); elo.addTo(caixa);
        mapa.desfazer.clear();
        return mapa, raiz;

    mapa, raiz = arvore();
    recalcular(mapa);
    layouts.aplicar(mapa, "espalhar");
    confere(colisoes(mapa) == 0, "ZERO colisões, contando as caixinhas de verbo (%d)" % colisoes(mapa));

    para_baixo = 0; total_arestas = 0;
    for de, para in layouts.arestas(mapa):
        total_arestas = total_arestas + 1;
        if para.y > de.y:
            para_baixo = para_baixo + 1;
    confere(para_baixo == total_arestas, "num DAG, TODA aresta aponta para baixo (%d/%d)"
            % (para_baixo, total_arestas));
    confere(raiz.y == min(c.y for c in layouts.caixas(mapa)), "a raiz ficou na primeira camada");

    print("\nespalhar respeita a folga, sem sobrar nem faltar");
    # O espalhar NAO busca a menor area -- ele busca ser legivel, e para caber na tela existem
    # zoom, ajustar-a-janela e minimapa. O que ele promete e disciplina de folga: ninguem mais
    # perto que ESPACO_RAMO (seria colisao) e, em algum lugar, alguem exatamente na folga
    # minima (senao nao estaria "o mais proximo possivel", estaria so espalhado a esmo).
    mapa_e, _ = arvore();
    recalcular(mapa_e);
    layouts.aplicar(mapa_e, "espalhar");
    folgas = [];
    por_linha = {};
    for caixa in layouts.caixas(mapa_e):
        por_linha.setdefault(caixa.y, []).append(caixa);
    for linha in por_linha.values():
        linha.sort(key=lambda c: c.x);
        for k in range(1, len(linha)):
            folgas.append(linha[k].x - (linha[k - 1].x + linha[k - 1].w));
    confere(len(folgas) > 0 and min(folgas) >= layouts.ESPACO_RAMO,
            "ninguém mais perto que a folga mínima (menor folga: %d >= %d)"
            % (min(folgas), layouts.ESPACO_RAMO));
    confere(min(folgas) == layouts.ESPACO_RAMO,
            "e alguém está exatamente nela, então não é espalhamento a esmo");

    print("\nespalhar: o TEXTO DO VÍNCULO também entra na briga");
    # Vários vínculos entre AS MESMAS duas caixas: todos têm o mesmo ponto médio, então os
    # rótulos nascem empilhados. É o pior caso, e é o que aparece em mapa denso de verdade.
    for quantos in (6, 12):
        paralelo = MapRelationship();
        paralelo.name = "Paralelas";
        alvo = paralelo.addEntity("organization", 0, 0, text="Empresa Alvo");
        quem = paralelo.addEntity("person", 0, 0, text="Investigado Principal");
        rotulos = ["Suspeito de receber de", "Apreendeu carros de", "Planejou com",
                   "Sócio de", "Controlaram", "Deflagrou contra"];
        for i in range(quantos):
            elo = paralelo.addEntity("link", 0, 0, text="%s %d" % (rotulos[i % len(rotulos)], i));
            elo.addFrom(alvo); elo.addTo(quem);
        recalcular(paralelo);   # larguras REAIS do texto
        layouts.aplicar(paralelo, "espalhar");
        confere(colisoes(paralelo) == 0, "%d vínculos paralelos, nenhum rótulo por cima de outro (%d)"
                % (quantos, colisoes(paralelo)));

    print("\nespalhar com ciclo (nem sempre dá para apontar para baixo)");
    ciclo = MapRelationship();
    ciclo.name = "Ciclo";
    a1 = ciclo.addEntity("person", 0, 0, text="A"); a1.w = 60; a1.h = 20;
    b1 = ciclo.addEntity("person", 0, 0, text="B"); b1.w = 60; b1.h = 20;
    c1 = ciclo.addEntity("person", 0, 0, text="C"); c1.w = 60; c1.h = 20;
    for de, para, verbo in ((a1, b1, "paga"), (b1, c1, "paga"), (c1, a1, "paga")):
        elo = ciclo.addEntity("link", 0, 0, text=verbo); elo.w = 50; elo.h = 20;
        elo.addFrom(de); elo.addTo(para);
    ciclo.desfazer.clear();
    layouts.aplicar(ciclo, "espalhar");
    confere(colisoes(ciclo) == 0, "ciclo também sai sem colisão");
    descendo = len([1 for de, para in layouts.arestas(ciclo) if para.y > de.y]);
    confere(descendo == 2, "2 das 3 arestas descem; a que fecha o ciclo sobe (%d)" % descendo);

    print("\nespalhar é repetível");
    m1, _ = arvore(); layouts.aplicar(m1, "espalhar");
    m2, _ = arvore(); layouts.aplicar(m2, "espalhar");
    confere(all((a.x, a.y) == (b.x, b.y) for a, b in zip(m1.elements, m2.elements)),
            "mesmo mapa, mesmo desenho");

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
