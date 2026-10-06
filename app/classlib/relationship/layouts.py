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

LAYOUTS = [("estrela",     "Estrela (um no centro, os demais em anéis)"),
           ("espalhar",    "Espalhar (sem colisão, de cima para baixo)"),
           ("organico",    "Orgânico"),
           ("hierarquico", "Hierárquico"),
           ("circular",    "Circular"),
           ("bloco",       "Bloco"),
           ("ortogonal",   "Ortogonal")];

MARGEM = 60;        # distancia da borda depois de normalizar
ESPACO_X = 60;      # respiro horizontal entre caixas
ESPACO_Y = 110;     # altura de uma camada
GRADE = 20;         # passo da grade do layout ortogonal
ANEIS_VERBO = 8;    # quantos aneis o afastar_vinculos procura antes de desistir
NIVEIS_ESTRELA = 3; # aneis do layout estrela, quando ninguem diz quantos
RAIO_ESTRELA = 260; # distancia do centro ate o primeiro anel
# Folgas do espalhar. Sao generosas de proposito: o objetivo dele nao e caber na tela, e ser
# LIDO por uma pessoa -- e para caber na tela existem o zoom, o ajustar-a-janela e o minimapa.
# Com folga pequena as diagonais entre camadas passam rente as caixas e os rotulos se espremem,
# que foi o que o dono viu no mapa real.
ESPACO_RAMO = 180;  # folga horizontal entre caixas vizinhas da mesma camada
ESPACO_VERBO = 170;  # folga entre camadas no "espalhar": tem de caber a caixinha do verbo
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
    """Coloca x e y no estilo CACHOEIRA: cada ramo desce no seu proprio curso.

    A primeira versao centralizava CADA camada em zero, independentemente. O resultado era uma
    piramide com tudo amontoado no meio: aceitavel num mapa de brinquedo, ilegivel num real.
    Agora o x nasce da familia -- filho sob a media dos pais, pai sobre a media dos filhos -- e
    as passadas alternam de cima para baixo e de baixo para cima ate assentar. Ramos diferentes
    ficam em correntes separadas, que e o que da a cara de cachoeira.

    A colisao continua impossivel por construcao: depois de cada ajuste, a camada e varrida da
    esquerda para a direita empurrando quem encostou."""
    indices = sorted(camadas.keys());
    pais, filhos = {}, {};
    for a, b in boas:
        filhos.setdefault(a, []).append(b);
        pais.setdefault(b, []).append(a);

    y = 0;
    for i in indices:
        linha = camadas[i];
        for caixa in linha:
            caixa.setY(int(y));
        y = y + max((c.h or 20) for c in linha) + ESPACO_VERBO;

    def largura(caixa):
        return (caixa.w or 100) + ESPACO_RAMO;

    def acomodar(linha):
        # Empurra para a direita quem encostou no vizinho. E isto que garante o "sem colisao"
        # depois de qualquer puxao -- a ordem da camada nunca muda aqui, so o espacamento.
        for k in range(1, len(linha)):
            minimo = linha[k - 1].x + largura(linha[k - 1]);
            if linha[k].x < minimo:
                linha[k].setX(int(minimo));

    def centro(caixa):
        return caixa.x + (caixa.w or 0) / 2.0;

    # Posicao inicial: a primeira camada em fila, as demais sob a familia.
    x = 0;
    for caixa in camadas[indices[0]]:
        caixa.setX(int(x));
        x = x + largura(caixa);
    for i in indices[1:]:
        linha = camadas[i];
        posicao = 0;
        for caixa in linha:
            familia = [p for p in pais.get(caixa, ()) if p not in linha];
            alvo = (sum(centro(p) for p in familia) / len(familia) - (caixa.w or 0) / 2.0) \
                   if len(familia) > 0 else posicao;
            caixa.setX(int(alvo));
            posicao = max(posicao, caixa.x + largura(caixa));
        linha.sort(key=lambda c: c.x);
        acomodar(linha);

    # Assenta: desce puxando filho para debaixo dos pais, sobe puxando pai para cima dos filhos.
    # O numero de passadas e PAR de proposito, para a ultima ser de SUBIDA: terminando na
    # descida, o pai fica onde estava e os filhos se amontoam embaixo dele -- a raiz aparecia
    # na ponta esquerda com a arvore inteira pendurada a direita.
    for passada in range(6):
        descendo = passada % 2 == 0;
        ordem = indices[1:] if descendo else list(reversed(indices[:-1]));
        for i in ordem:
            linha = camadas[i];
            vizinhanca = pais if descendo else filhos;
            for caixa in linha:
                familia = [v for v in vizinhanca.get(caixa, ()) if v not in linha];
                if len(familia) == 0:
                    continue;
                alvo = sum(centro(v) for v in familia) / len(familia) - (caixa.w or 0) / 2.0;
                caixa.setX(int(alvo));
            linha.sort(key=lambda c: c.x);
            acomodar(linha);


def __colide__(a, b, folga=6):
    return not (a[0] + a[2] + folga <= b[0] or b[0] + b[2] + folga <= a[0] or
                a[1] + a[3] + folga <= b[1] or b[1] + b[3] + folga <= a[1]);


def afastar_vinculos(mapa):
    """Tira a caixinha do verbo de cima de quem ja esta la.

    O TEXTO DO VINCULO entra na briga da colisao igual a qualquer caixa -- e so olhando um mapa
    denso para ver que e ele quem mais se sobrepoe: varios vinculos entre as mesmas duas caixas
    tem o MESMO ponto medio, entao os rotulos nascem todos empilhados no mesmo lugar.

    SO a caixa do verbo se mexe: as caixas de entidade ficam onde o layout as pos, senao o 'sem
    colisao' de uma vira a colisao da outra. A procura e em aneis a partir do ponto certo, com
    passo do tamanho do proprio rotulo, preferindo subir/descer (que e onde existe folga entre
    camadas) antes de ir para os lados."""
    ocupadas = [(c.x, c.y, c.w or 1, c.h or 1) for c in caixas(mapa)];
    # Mais largo primeiro: quem e dificil de encaixar escolhe enquanto ha espaco.
    for vinculo in sorted(vinculos(mapa), key=lambda v: -(v.w or 0)):
        largura = vinculo.w or 60;
        altura = vinculo.h or 20;
        atual = (vinculo.x, vinculo.y, largura, altura);
        if not any(__colide__(atual, outra) for outra in ocupadas):
            ocupadas.append(atual);
            continue;
        passo_x = largura + 14;
        passo_y = altura + 8;
        candidatos = [];
        for anel in range(1, ANEIS_VERBO + 1):
            for dy in range(-anel, anel + 1):
                for dx in range(-anel, anel + 1):
                    if max(abs(dx), abs(dy)) != anel:
                        continue;   # so a borda do anel; o miolo ja foi tentado antes
                    candidatos.append((abs(dy), abs(dx), anel, dx, dy));
        candidatos.sort();   # perto antes de longe, e vertical antes de horizontal
        for _, _, _, dx, dy in candidatos:
            tentativa = (vinculo.x + dx * passo_x, vinculo.y + dy * passo_y, largura, altura);
            if not any(__colide__(tentativa, outra) for outra in ocupadas):
                vinculo.setX(int(tentativa[0]));
                vinculo.setY(int(tentativa[1]));
                ocupadas.append(tentativa);
                break;
        else:
            # Nao deveria acontecer com ANEIS_VERBO aneis; fica registrado em vez de silencioso.
            ocupadas.append(atual);


def escolher_centro(mapa, lista):
    """Quem fica no meio da estrela quando ninguem escolheu: a caixa de maior grau.

    Nao e capricho -- a estrela existe para responder "o que gira em volta DISTO", e o no mais
    ligado e a resposta mais provavel. O chamador passa a caixa selecionada quando ha uma."""
    if len(lista) == 0:
        return None;
    return sorted(lista, key=lambda c: (-grau(mapa, c), (c.entity.text or "").lower()))[0];


def __niveis_a_partir_de__(mapa, lista, centro):
    """Distancia em saltos de cada caixa ate o centro (busca em largura). Quem nao se liga ao
    centro fica como None: vai para a prateleira, nao para um anel -- pendurar desconectado num
    anel diria que ha ligacao onde nao ha."""
    vizinhos = {c: set() for c in lista};
    for a, b in arestas(mapa):
        if a in vizinhos and b in vizinhos:
            vizinhos[a].add(b);
            vizinhos[b].add(a);
    nivel = {centro: 0};
    fila = [centro];
    while len(fila) > 0:
        atual = fila.pop(0);
        for vizinho in vizinhos.get(atual, ()):
            if vizinho not in nivel:
                nivel[vizinho] = nivel[atual] + 1;
                fila.append(vizinho);
    return nivel;


def __estrela__(mapa, lista, centro=None, niveis=None):
    """Um no no centro e os demais em aneis ao redor, por distancia em saltos.

    O raio de cada anel NAO e um multiplo fixo: ele cresce ate caber o perimetro de quem esta
    nele. Com raio fixo, o anel 2 de um mapa grande vira uma fileira de caixas encavaladas --
    a circunferencia nao acompanha a quantidade de vizinhos sozinha.

    Quem esta alem do ultimo anel pedido vai para o anel de fora, em vez de sumir: o layout
    arruma o mapa, nao decide o que o analista pode ver."""
    if centro == None:
        centro = escolher_centro(mapa, lista);
    if centro == None:
        return;
    if centro not in lista:
        centro = escolher_centro(mapa, lista);
    limite = int(niveis or NIVEIS_ESTRELA);
    if limite < 1:
        limite = 1;

    nivel = __niveis_a_partir_de__(mapa, lista, centro);
    soltas = [c for c in lista if c not in nivel];
    por_anel = {};
    for caixa in lista:
        if caixa not in nivel or caixa is centro:
            continue;
        # Alem do limite, todo mundo no ultimo anel: some-los seria esconder dado.
        por_anel.setdefault(min(nivel[caixa], limite), []).append(caixa);

    # O centro da CAIXA no centro do anel, nao o canto dela: com setX(0)/setY(0) o meio da
    # caixa fica em (w/2, h/2) e todo o anel sai deslocado em relacao a ela.
    centro.setX(int(-(centro.w or 0) / 2));
    centro.setY(int(-(centro.h or 0) / 2));

    # De quem cada caixa desce: serve para o anel de fora nascer PERTO do seu pai. Sem isso o
    # filho cai num angulo qualquer e a linha ate o pai atravessa o desenho inteiro -- a
    # estrela fica certa na geometria e ilegivel no papel.
    vizinhos = {c: set() for c in lista};
    for a, b in arestas(mapa):
        if a in vizinhos and b in vizinhos:
            vizinhos[a].add(b);
            vizinhos[b].add(a);
    angulo_de = {centro: -math.pi / 2};

    raio_anterior = 0;
    for anel in sorted(por_anel.keys()):
        def __angulo_do_pai__(caixa):
            pais = [v for v in vizinhos.get(caixa, ()) if v in angulo_de];
            if len(pais) == 0:
                return 999.0;   # sem pai colocado ainda: vai para o fim, sem atrapalhar
            return min(angulo_de[p] for p in pais);
        no_anel = sorted(por_anel[anel],
                         key=lambda c: (__angulo_do_pai__(c), -grau(mapa, c), (c.entity.text or "").lower()));
        # Perimetro necessario: a soma das larguras mais a folga entre vizinhos. O raio sai
        # dai, e nunca encolhe em relacao ao anel de dentro.
        perimetro = sum((c.w or 100) + ESPACO_RAMO for c in no_anel);
        raio = max(RAIO_ESTRELA * anel, perimetro / (2 * math.pi), raio_anterior + ESPACO_VERBO + 60);

        desejados = [__angulo_do_pai__(c) for c in no_anel];
        iguais = len(set(round(d, 4) for d in desejados if d < 900)) <= 1;
        if iguais:
            # Todos filhos do mesmo no (e o caso do primeiro anel, que desce do centro):
            # distribuir por igual. Comeca em -90 graus para o desenho nascer com um no "em
            # cima", que le melhor do que comecar pela direita.
            angulos = [-math.pi / 2 + (2 * math.pi * i) / len(no_anel) for i in range(len(no_anel))];
        else:
            # Cada filho POUSA perto do pai, e nao num angulo qualquer da volta: o que
            # importa num anel de fora e a linha ate o pai ser curta. Ordenar por angulo do
            # pai deixa a ordem certa mas a posicao ainda errada -- e preciso partir do
            # angulo dele e so afastar o necessario para nao encostar no vizinho.
            angulos = [];
            anterior = None;
            for i in range(len(no_anel)):
                largura = (no_anel[i].w or 100) + ESPACO_RAMO;
                separacao = largura / max(1.0, raio);     # arco -> angulo
                alvo = desejados[i] if desejados[i] < 900 else (anterior or -math.pi / 2) + separacao;
                if anterior != None and alvo < anterior + separacao:
                    alvo = anterior + separacao;
                angulos.append(alvo);
                anterior = alvo;
            # Se a soma passou da volta inteira, o anel esta cheio: distribuir por igual, que
            # e o melhor possivel, em vez de deixar o ultimo girar por cima do primeiro.
            if angulos[-1] - angulos[0] > 2 * math.pi:
                angulos = [angulos[0] + (2 * math.pi * i) / len(no_anel) for i in range(len(no_anel))];

        for i in range(len(no_anel)):
            caixa = no_anel[i];
            angulo_de[caixa] = angulos[i];
            caixa.setX(int(math.cos(angulos[i]) * raio - (caixa.w or 0) / 2.0));
            caixa.setY(int(math.sin(angulos[i]) * raio - (caixa.h or 0) / 2.0));
        raio_anterior = raio;

    # As soltas vao para a prateleira, como no espalhar, e nao para um anel.
    if len(soltas) > 0:
        ligadas = [c for c in lista if c not in soltas];
        __prateleira__(ligadas, soltas);


def __espalhar__(mapa, lista):
    pares = arestas(mapa);
    ligadas = set();
    for a, b in pares:
        ligadas.add(a); ligadas.add(b);
    correnteza = [c for c in lista if c in ligadas];
    soltas = [c for c in lista if c not in ligadas];

    if len(correnteza) > 0:
        boas = __sem_ciclos__(correnteza, pares);
        camadas = __camadas_dirigidas__(correnteza, boas);
        camadas = __ordenar_camadas__(camadas, boas);
        __empacotar__(camadas, boas);
    __prateleira__(correnteza, soltas);


def __prateleira__(correnteza, soltas):
    """Caixa sem vinculo nenhum nao participa da cachoeira -- ela nao desce de lugar nenhum.

    Deixa-las na primeira camada abria um vao enorme no desenho: elas ficavam na origem e o
    resto da arvore se afastava para a direita durante o assentamento. Vao para uma prateleira
    embaixo, empacotadas, que e tambem como o analista as le: material solto, ainda sem lugar."""
    if len(soltas) == 0:
        return;
    if len(correnteza) == 0:
        base_x, base_y, limite = 0, 0, 6;
    else:
        base_x = min(c.x for c in correnteza);
        base_y = max(c.y + (c.h or 20) for c in correnteza) + ESPACO_VERBO;
        largura_total = max(c.x + (c.w or 0) for c in correnteza) - base_x;
        limite = max(1, int(largura_total / (160 + ESPACO_RAMO)));
    x, y, na_linha = base_x, base_y, 0;
    altura_linha = 0;
    for caixa in soltas:
        caixa.setX(int(x));
        caixa.setY(int(y));
        x = x + (caixa.w or 100) + ESPACO_RAMO;
        altura_linha = max(altura_linha, caixa.h or 20);
        na_linha = na_linha + 1;
        if na_linha >= limite:
            x = base_x; y = y + altura_linha + 30; na_linha = 0; altura_linha = 0;


ALGORITMOS = {"estrela": __estrela__, "espalhar": __espalhar__, "organico": __organico__, "hierarquico": __hierarquico__, "circular": __circular__,
              "bloco": __bloco__, "ortogonal": __ortogonal__};


def rotulo(nome):
    for chave, texto in LAYOUTS:
        if chave == nome:
            return texto;
    return nome;


def aplicar(mapa, nome, centro=None, niveis=None):
    """Posiciona as caixas do mapa e devolve quantas foram movidas. Entra como UM passo de
    desfazer. Mapa travado nao e mexido.

    `centro` e `niveis` so valem para o layout estrela; os outros os ignoram, em vez de
    recusarem -- quem chama nao deveria precisar saber qual layout aceita o que."""
    if nome not in ALGORITMOS:
        raise ValueError("Layout desconhecido: %s" % nome);
    if mapa.getLocked():
        raise Exception("O mapa está travado (somente leitura).");
    lista = caixas(mapa);
    if len(lista) == 0:
        return 0;
    with Operacao(mapa, "Layout " + rotulo(nome)):
        if nome == "estrela":
            __estrela__(mapa, lista, centro=centro, niveis=niveis);
        else:
            ALGORITMOS[nome](mapa, lista);
        __normalizar__(lista);
        __centralizar_vinculos__(mapa);
        if nome in ("espalhar", "estrela"):
            # Os dois prometem ausencia de colisao. Faz sentido justamente neles porque nenhum
            # dos dois DECIDE onde o verbo fica -- o espalhar posiciona por camada e a estrela
            # por anel, e a caixa do verbo e consequencia. Nos outros layouts, mexer no verbo
            # depois mudaria um desenho que ja esta como o algoritmo quis.
            afastar_vinculos(mapa);
            __normalizar__(mapa.elements);
    return len(lista);
