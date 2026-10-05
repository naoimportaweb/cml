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

LAYOUTS = [("espalhar",    "Espalhar (sem colisão, de cima para baixo)"),
           ("organico",    "Orgânico"),
           ("hierarquico", "Hierárquico"),
           ("circular",    "Circular"),
           ("bloco",       "Bloco"),
           ("ortogonal",   "Ortogonal")];

MARGEM = 60;        # distancia da borda depois de normalizar
ESPACO_X = 60;      # respiro horizontal entre caixas
ESPACO_Y = 110;     # altura de uma camada
GRADE = 20;         # passo da grade do layout ortogonal
ESPACO_VERBO = 70;  # folga entre camadas no "espalhar": tem de caber a caixinha do verbo
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


def __sem_ciclos__(lista, pares):
    """Arestas que podem ser usadas para empilhar as camadas, sem ciclo.

    A regra do dono e "quem esta em cima aponta para quem esta embaixo". Nem sempre da: o mapa
    e um GRAFO, e grafo tem ciclo (A dirige B, B financia A). Uma busca em profundidade marca as
    arestas de retorno -- as que fecham o ciclo -- e elas ficam de fora da conta das camadas.
    O desenho sai com essas poucas apontando para cima, e isso e honesto: a alternativa seria
    inventar uma hierarquia que o caso nao tem."""
    saida = {c: [] for c in lista};
    for a, b in pares:
        if a in saida and b in saida and a is not b:
            saida[a].append(b);
    cor = {c: 0 for c in lista};   # 0 = nao visitado, 1 = na pilha, 2 = fechado
    boas = [];
    def visitar(no):
        cor[no] = 1;
        for vizinho in saida[no]:
            if cor[vizinho] == 1:
                continue;          # aresta de retorno: fecha ciclo, nao conta para a camada
            boas.append((no, vizinho));
            if cor[vizinho] == 0:
                visitar(vizinho);
        cor[no] = 2;
    # Comeca pelos que ninguem aponta: sao as raizes naturais ("de cima").
    entrada = {c: 0 for c in lista};
    for a, b in pares:
        if b in entrada and a is not b:
            entrada[b] = entrada[b] + 1;
    for no in sorted(lista, key=lambda c: (entrada[c], -grau_dirigido(saida, c))):
        if cor[no] == 0:
            visitar(no);
    return boas;


def grau_dirigido(saida, no):
    return len(saida.get(no, ()));


def __camadas_dirigidas__(lista, boas):
    """Nivel de cada caixa: uma a mais que o maior nivel de quem aponta para ela."""
    entrada = {c: [] for c in lista};
    for a, b in boas:
        entrada[b].append(a);
    nivel = {};
    def calcular(no, visitando):
        if no in nivel:
            return nivel[no];
        if no in visitando:
            return 0;
        visitando.add(no);
        if len(entrada[no]) == 0:
            nivel[no] = 0;
        else:
            nivel[no] = max(calcular(pai, visitando) for pai in entrada[no]) + 1;
        visitando.discard(no);
        return nivel[no];
    for no in lista:
        calcular(no, set());
    camadas = {};
    for no in lista:
        camadas.setdefault(nivel[no], []).append(no);
    return camadas;


def __ordenar_camadas__(camadas, boas, passadas=4):
    """Reduz cruzamento pelo metodo do baricentro: cada caixa tende para a media das posicoes
    de quem ela liga na camada vizinha. Varre para baixo e para cima algumas vezes."""
    vizinhos_acima = {};
    vizinhos_abaixo = {};
    for a, b in boas:
        vizinhos_acima.setdefault(b, []).append(a);
        vizinhos_abaixo.setdefault(a, []).append(b);
    indices = sorted(camadas.keys());
    for passada in range(passadas):
        ordem = indices if passada % 2 == 0 else list(reversed(indices));
        for i in ordem:
            vizinhos = vizinhos_acima if passada % 2 == 0 else vizinhos_abaixo;
            posicao = {};
            for j in indices:
                for k in range(len(camadas[j])):
                    posicao[camadas[j][k]] = k;
            def baricentro(no):
                ligados = [posicao[v] for v in vizinhos.get(no, ()) if v in posicao];
                return sum(ligados) / float(len(ligados)) if len(ligados) > 0 else posicao.get(no, 0);
            camadas[i] = sorted(camadas[i], key=baricentro);
    return camadas;


def __empacotar__(camadas, boas):
    """Coloca x e y. Dentro da camada, encosta uma na outra com folga -- e o 'mais proximo
    possivel' sem colisao, usando a largura REAL de cada caixa. Depois algumas passadas puxando
    cada uma para perto de quem ela liga, sem deixar encostar."""
    indices = sorted(camadas.keys());
    y = 0;
    for i in indices:
        linha = camadas[i];
        x = 0;
        for caixa in linha:
            caixa.setX(int(x));
            caixa.setY(int(y));
            x = x + __largura__(caixa);
        # Centraliza a camada em zero, para o desenho crescer dos dois lados.
        largura = x - ESPACO_X;
        for caixa in linha:
            caixa.setX(int(caixa.x - largura / 2));
        altura = max((c.h or 20) for c in linha);
        # A folga vertical tem de caber a CAIXA DO VERBO, que vai para o meio das pontas.
        y = y + altura + ESPACO_VERBO;

    vizinhos = {};
    for a, b in boas:
        vizinhos.setdefault(a, []).append(b);
        vizinhos.setdefault(b, []).append(a);
    for _ in range(6):
        for i in indices:
            linha = camadas[i];
            for k in range(len(linha)):
                caixa = linha[k];
                ligados = [v for v in vizinhos.get(caixa, ()) if v not in linha];
                if len(ligados) == 0:
                    continue;
                alvo = sum(v.x + (v.w or 0) / 2.0 for v in ligados) / len(ligados) - (caixa.w or 0) / 2.0;
                # Os limites sao os vizinhos de camada: e isto que garante que puxar para perto
                # NUNCA encosta uma caixa na outra.
                menor = linha[k - 1].x + __largura__(linha[k - 1]) if k > 0 else alvo;
                maior = linha[k + 1].x - __largura__(caixa) if k + 1 < len(linha) else alvo;
                caixa.setX(int(max(menor, min(maior, alvo))));


def __colide__(a, b, folga=6):
    return not (a[0] + a[2] + folga <= b[0] or b[0] + b[2] + folga <= a[0] or
                a[1] + a[3] + folga <= b[1] or b[1] + b[3] + folga <= a[1]);


def afastar_vinculos(mapa):
    """Tira a caixinha do verbo de cima de quem ja esta la.

    O meio das pontas e o lugar certo, mas duas arestas vizinhas caem no mesmo ponto e os dois
    verbos se escrevem um por cima do outro. Aqui SO a caixa do verbo se mexe -- as caixas de
    entidade ficam onde o layout as pos, senao o 'sem colisao' de um vira a colisao do outro."""
    ocupadas = [(c.x, c.y, c.w or 1, c.h or 1) for c in caixas(mapa)];
    for vinculo in vinculos(mapa):
        atual = (vinculo.x, vinculo.y, vinculo.w or 1, vinculo.h or 1);
        if not any(__colide__(atual, outra) for outra in ocupadas):
            ocupadas.append(atual);
            continue;
        achou = False;
        # Em espiral curta a partir do ponto certo: primeiro de lado (onde ha gap entre
        # camadas), depois para cima e para baixo.
        for raio in (18, 36, 54, 72):
            for dx, dy in ((raio, 0), (-raio, 0), (0, raio), (0, -raio),
                           (raio, raio), (-raio, raio), (raio, -raio), (-raio, -raio)):
                tentativa = (vinculo.x + dx, vinculo.y + dy, atual[2], atual[3]);
                if not any(__colide__(tentativa, outra) for outra in ocupadas):
                    vinculo.setX(int(tentativa[0]));
                    vinculo.setY(int(tentativa[1]));
                    ocupadas.append(tentativa);
                    achou = True;
                    break;
            if achou:
                break;
        if not achou:
            ocupadas.append(atual);   # desistiu: melhor sobrepor do que jogar longe da aresta


def __espalhar__(mapa, lista):
    pares = arestas(mapa);
    boas = __sem_ciclos__(lista, pares);
    camadas = __camadas_dirigidas__(lista, boas);
    camadas = __ordenar_camadas__(camadas, boas);
    __empacotar__(camadas, boas);


ALGORITMOS = {"espalhar": __espalhar__, "organico": __organico__, "hierarquico": __hierarquico__, "circular": __circular__,
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
        if nome == "espalhar":
            # So o "espalhar" promete ausencia de colisao; nos outros, mexer no verbo depois
            # mudaria um desenho que ja esta como o algoritmo quis.
            afastar_vinculos(mapa);
            __normalizar__(mapa.elements);
    return len(lista);
