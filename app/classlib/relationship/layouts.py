# Layouts automaticos do mapa de vinculos (SPEC.md §3.3). Os cinco do Maltego: organico,
# hierarquico, circular, bloco e ortogonal.
#
# Tres regras que valem para todos:
#   1. Layout e ACAO, nao modo: roda uma vez, escreve x/y no modelo e sai. Depois o analista
#      arrasta a vontade -- a posicao manual e dado, nao enfeite.
#   2. Por isso tudo entra como UM passo de desfazer. Sem isso o botao seria destrutivo: joga
#      fora um posicionamento que pode ter levado horas.
#   3. O vinculo NAO participa do layout. Ele e hiper-aresta: a caixa do verbo vai para o meio
#      das pontas depois que as caixas acharam lugar, senao ele seria tratado como no solto e
#      iria parar longe das linhas que desenha.
#
# Sem biblioteca externa de grafo: sao algoritmos curtos e o projeto nao tem build system.

import math, random;

from classlib.relationship.comandos import Operacao;

LAYOUTS = [("organico",    "Orgânico"),
           ("hierarquico", "Hierárquico"),
           ("circular",    "Circular"),
           ("bloco",       "Bloco"),
           ("ortogonal",   "Ortogonal")];

MARGEM = 60;        # distancia da borda depois de normalizar
ESPACO_X = 60;      # respiro horizontal entre caixas
ESPACO_Y = 110;     # altura de uma camada
GRADE = 20;         # passo da grade do layout ortogonal
SEMENTE = 20261005; # posicao inicial do organico e sorteada: semente fixa = resultado repetivel
GRAVIDADE = 6.0;    # divisor da gravidade do organico (ver comentario em __organico__)


def caixas(mapa):
    return [e for e in mapa.elements if e.entity.etype != "link"];


def vinculos(mapa):
    return [e for e in mapa.elements if e.entity.etype == "link"];


def arestas(mapa):
    """Pares (caixa_de, caixa_para) extraidos dos vinculos. Um vinculo com duas pontas de cada
    lado vira quatro arestas -- e e isso mesmo: todas elas sao desenhadas."""
    saida = [];
    for vinculo in vinculos(mapa):
        de = [p.entity for p in vinculo.from_entity if p.entity != None];
        para = [p.entity for p in vinculo.to_entity if p.entity != None];
        for a in de:
            for b in para:
                if a is not b:
                    saida.append((a, b));
    return saida;


def __vizinhanca__(lista, pares):
    vizinhos = {c: set() for c in lista};
    for a, b in pares:
        if a in vizinhos and b in vizinhos:
            vizinhos[a].add(b);
            vizinhos[b].add(a);
    return vizinhos;


def grau(mapa, caixa):
    total = 0;
    for vinculo in vinculos(mapa):
        for ponta in list(vinculo.to_entity) + list(vinculo.from_entity):
            if ponta.entity is caixa:
                total = total + 1;
    return total;


def __largura__(caixa):
    return (caixa.w or 100) + ESPACO_X;


def __normalizar__(lista):
    # Traz tudo para coordenada positiva: o modelo e o banco sempre trabalharam com x/y >= 0.
    if len(lista) == 0:
        return;
    menor_x = min(c.x for c in lista);
    menor_y = min(c.y for c in lista);
    for caixa in lista:
        caixa.setX(int(caixa.x - menor_x + MARGEM));
        caixa.setY(int(caixa.y - menor_y + MARGEM));


def __centralizar_vinculos__(mapa):
    # A caixa do verbo vai para o meio das pontas que ela liga.
    for vinculo in vinculos(mapa):
        pontas = [p.entity for p in list(vinculo.to_entity) + list(vinculo.from_entity) if p.entity != None];
        if len(pontas) == 0:
            continue;
        meio_x = sum((p.x + (p.w or 100) / 2.0) for p in pontas) / len(pontas);
        meio_y = sum((p.y + (p.h or 20) / 2.0) for p in pontas) / len(pontas);
        vinculo.setX(int(meio_x - (vinculo.w or 60) / 2.0));
        vinculo.setY(int(meio_y - (vinculo.h or 20) / 2.0));


# ---------------------------------------------------------------- os cinco

def __organico__(mapa, lista):
    # Fruchterman-Reingold: molas nas arestas, repulsao entre todos, temperatura caindo.
    n = len(lista);
    area = max(1, n) * 40000.0;
    k = math.sqrt(area / max(1, n));
    sorteio = random.Random(SEMENTE);
    pos = {};
    for caixa in lista:
        # Comeca em circulo com ruido: tudo no mesmo ponto faz a repulsao explodir (divisao
        # por distancia zero) e o desenho sair em leque.
        angulo = sorteio.random() * 2 * math.pi;
        raio = sorteio.random() * k * math.sqrt(n);
        pos[caixa] = [math.cos(angulo) * raio, math.sin(angulo) * raio];

    pares = arestas(mapa);
    temperatura = k * 2.0;
    passos = 200;
    for passo in range(passos):
        desloc = {c: [0.0, 0.0] for c in lista};
        for i in range(n):
            for j in range(i + 1, n):
                a, b = lista[i], lista[j];
                dx = pos[a][0] - pos[b][0];
                dy = pos[a][1] - pos[b][1];
                dist = math.sqrt(dx * dx + dy * dy) or 0.01;
                forca = (k * k) / dist;
                ux, uy = dx / dist, dy / dist;
                desloc[a][0] += ux * forca; desloc[a][1] += uy * forca;
                desloc[b][0] -= ux * forca; desloc[b][1] -= uy * forca;
        for a, b in pares:
            if a not in pos or b not in pos:
                continue;
            dx = pos[a][0] - pos[b][0];
            dy = pos[a][1] - pos[b][1];
            dist = math.sqrt(dx * dx + dy * dy) or 0.01;
            forca = (dist * dist) / k;
            ux, uy = dx / dist, dy / dist;
            desloc[a][0] -= ux * forca; desloc[a][1] -= uy * forca;
            desloc[b][0] += ux * forca; desloc[b][1] += uy * forca;
        # Gravidade: mola fraca puxando tudo para o centro. Sem ela, caixa SEM VINCULO so
        # sente repulsao e voa para fora -- um mapa com meia duzia de soltas vira um aglomerado
        # no meio e lixo nas bordas, e o "ajustar a janela" deixa tudo ilegivel. A constante
        # cresce com o numero de nos porque a repulsao sobre a caixa solta tambem cresce: no
        # equilibrio, (n-1)k²/d = g·d, entao g ~ n deixa a distancia final proporcional a k em
        # vez de explodir com o tamanho do mapa.
        gravidade = max(0.3, n / GRAVIDADE);
        for caixa in lista:
            desloc[caixa][0] -= pos[caixa][0] * gravidade;
            desloc[caixa][1] -= pos[caixa][1] * gravidade;
            dx, dy = desloc[caixa];
            tamanho = math.sqrt(dx * dx + dy * dy) or 0.01;
            # O passo nunca passa da temperatura: e o que faz o desenho assentar em vez de
            # ficar oscilando para sempre.
            pos[caixa][0] += (dx / tamanho) * min(tamanho, temperatura);
            pos[caixa][1] += (dy / tamanho) * min(tamanho, temperatura);
        temperatura = temperatura * (1.0 - (passo + 1.0) / passos) if passo < passos - 1 else 0;
        temperatura = max(temperatura, k * 0.01);

    for caixa in lista:
        caixa.setX(int(pos[caixa][0]));
        caixa.setY(int(pos[caixa][1]));


def __camadas__(mapa, lista):
    """Reparte as caixas em camadas por distancia (busca em largura). Comeca pelas de maior
    grau, que e o que poe o centro da investigacao no topo."""
    vizinhos = __vizinhanca__(lista, arestas(mapa));
    faltando = sorted(lista, key=lambda c: -grau(mapa, c));
    nivel = {};
    for semente in faltando:
        if semente in nivel:
            continue;
        nivel[semente] = 0;
        fila = [semente];
        while len(fila) > 0:
            atual = fila.pop(0);
            for vizinho in vizinhos.get(atual, ()):
                if vizinho not in nivel:
                    nivel[vizinho] = nivel[atual] + 1;
                    fila.append(vizinho);
    camadas = {};
    for caixa in lista:
        camadas.setdefault(nivel.get(caixa, 0), []).append(caixa);
    return camadas;


def __hierarquico__(mapa, lista):
    camadas = __camadas__(mapa, lista);
    for indice in sorted(camadas.keys()):
        linha = camadas[indice];
        largura = sum(__largura__(c) for c in linha);
        x = -largura / 2.0;
        for caixa in linha:
            caixa.setX(int(x));
            caixa.setY(int(indice * ESPACO_Y));
            x = x + __largura__(caixa);


def __circular__(mapa, lista):
    # Mais ligados por ultimo no circulo nao ajuda: o util e a ordem por grau, para vizinho de
    # grau parecido ficar junto e as linhas cruzarem menos.
    ordenadas = sorted(lista, key=lambda c: -grau(mapa, c));
    n = max(1, len(ordenadas));
    perimetro = sum(__largura__(c) for c in ordenadas);
    raio = max(220.0, perimetro / (2 * math.pi));
    for i in range(len(ordenadas)):
        angulo = (2 * math.pi * i) / n;
        ordenadas[i].setX(int(math.cos(angulo) * raio));
        ordenadas[i].setY(int(math.sin(angulo) * raio));


def __bloco__(mapa, lista):
    # Um bloco por tipo, e dentro do bloco os mais ligados primeiro -- e a leitura "quem e quem"
    # que o Maltego faz no layout de mesmo nome.
    ordem_tipo = ["person", "organization", "other"];
    def chave(caixa):
        etype = caixa.entity.etype;
        return (ordem_tipo.index(etype) if etype in ordem_tipo else len(ordem_tipo),
                -grau(mapa, caixa), (caixa.entity.text or "").lower());
    ordenadas = sorted(lista, key=chave);
    por_linha = max(1, int(math.ceil(math.sqrt(len(ordenadas) or 1))));
    y = 0;
    i = 0;
    while i < len(ordenadas):
        linha = ordenadas[i:i + por_linha];
        x = 0;
        for caixa in linha:
            caixa.setX(int(x));
            caixa.setY(int(y));
            x = x + __largura__(caixa);
        y = y + ESPACO_Y;
        i = i + por_linha;


def __ortogonal__(mapa, lista):
    # Hierarquico e depois tudo encaixado na grade: linhas retas, bom para mapa impresso. E o
    # que o Graph Browser novo do Maltego pos no lugar do layout de bloco.
    __hierarquico__(mapa, lista);
    for caixa in lista:
        caixa.setX(int(round(caixa.x / float(GRADE)) * GRADE));
        caixa.setY(int(round(caixa.y / float(GRADE)) * GRADE));


ALGORITMOS = {"organico": __organico__, "hierarquico": __hierarquico__, "circular": __circular__,
              "bloco": __bloco__, "ortogonal": __ortogonal__};


def rotulo(nome):
    for chave, texto in LAYOUTS:
        if chave == nome:
            return texto;
    return nome;


def aplicar(mapa, nome):
    """Posiciona as caixas do mapa e devolve quantas foram movidas. Entra como UM passo de
    desfazer. Mapa travado nao e mexido."""
    if nome not in ALGORITMOS:
        raise ValueError("Layout desconhecido: %s" % nome);
    if mapa.getLocked():
        raise Exception("O mapa está travado (somente leitura).");
    lista = caixas(mapa);
    if len(lista) == 0:
        return 0;
    with Operacao(mapa, "Layout " + rotulo(nome)):
        ALGORITMOS[nome](mapa, lista);
        __normalizar__(lista);
        __centralizar_vinculos__(mapa);
    return len(lista);
