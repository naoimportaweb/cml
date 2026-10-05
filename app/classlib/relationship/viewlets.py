# Viewlets: cor e tamanho da caixa a partir de uma PROPRIEDADE do mapa (SPEC.md §3.3).
#
# A ideia e do Maltego, que traz sete de fabrica e sempre faz a mesma coisa -- decidir o
# tamanho e a cor da bola por uma propriedade. Aqui vale mais como MECANISMO do que como lista:
# com ele, "tamanho por grau", "por rank" e "por referencias" sao tres configuracoes da mesma
# coisa, em vez de tres regras escritas no meio do codigo de desenho.
#
# Cada viewlet devolve, por caixa, (escala, cor):
#   escala -- 1.0 e o tamanho normal; o canvas amplia a caixa em volta do centro dela;
#   cor    -- None nao pinta nada; com cor, o canvas desenha uma MOLDURA atras da caixa
#             (o draw de cada tipo ja preenche o proprio retangulo de branco ou amarelo,
#             entao pintar por tras e o jeito de colorir sem mexer no desenho do modelo).
#
# O vinculo nao participa: viewlet fala de entidade.

from PySide6.QtGui import QColor;

ESCALA_MIN = 1.0;
ESCALA_MAX = 2.2;

COR_TIPO = {"person": QColor(70, 130, 220), "organization": QColor(60, 160, 110),
            "other": QColor(200, 150, 40)};
COR_ALERTA = QColor(215, 60, 60);
COR_OK = QColor(150, 150, 150);

VIEWLETS = [("nenhum",      "Nenhum (normal)"),
            ("grau",        "Tamanho por vínculos"),
            ("rank",        "Tamanho por rank (vínculos + dos vizinhos)"),
            ("referencias", "Tamanho por referências"),
            ("tipo",        "Cor por tipo"),
            ("sem_fonte",   "Cor: sem fonte (destaca quem não tem referência)")];


def rotulo(nome):
    for chave, texto in VIEWLETS:
        if chave == nome:
            return texto;
    return nome;


def __caixas__(mapa):
    return [e for e in mapa.elements if e.entity.etype != "link"];


def __vinculos__(mapa):
    return [e for e in mapa.elements if e.entity.etype == "link"];


def __graus__(mapa):
    grau = {c: 0 for c in __caixas__(mapa)};
    for vinculo in __vinculos__(mapa):
        for ponta in list(vinculo.to_entity) + list(vinculo.from_entity):
            if ponta.entity in grau:
                grau[ponta.entity] = grau[ponta.entity] + 1;
    return grau;


def __vizinhos__(mapa):
    vizinhos = {c: set() for c in __caixas__(mapa)};
    for vinculo in __vinculos__(mapa):
        de = [p.entity for p in vinculo.from_entity if p.entity in vizinhos];
        para = [p.entity for p in vinculo.to_entity if p.entity in vizinhos];
        for a in de:
            for b in para:
                if a is not b:
                    vizinhos[a].add(b);
                    vizinhos[b].add(a);
    return vizinhos;


def __escalar__(valores):
    """Mapeia os valores para [ESCALA_MIN, ESCALA_MAX]. Todos iguais (inclusive todos zero)
    devolve tudo no tamanho normal -- ampliar tudo por igual nao diz nada a ninguem."""
    if len(valores) == 0:
        return {};
    menor = min(valores.values());
    maior = max(valores.values());
    if maior == menor:
        return {chave: ESCALA_MIN for chave in valores};
    faixa = float(maior - menor);
    return {chave: ESCALA_MIN + (valor - menor) / faixa * (ESCALA_MAX - ESCALA_MIN)
            for chave, valor in valores.items()};


def calcular(mapa, nome):
    """Devolve {caixa: (escala, cor)}. Viewlet desconhecido ou 'nenhum' devolve vazio, que o
    canvas entende como 'desenhe do jeito normal'."""
    caixas = __caixas__(mapa);
    if nome in (None, "", "nenhum") or len(caixas) == 0:
        return {};

    if nome == "tipo":
        return {c: (ESCALA_MIN, COR_TIPO.get(c.entity.etype)) for c in caixas};

    if nome == "sem_fonte":
        # Regra editorial do projeto: informacao sem fonte e problema. Aqui ela vira cor.
        saida = {};
        for caixa in caixas:
            tem = len(caixa.entity.references or []) > 0;
            saida[caixa] = (ESCALA_MIN, COR_OK if tem else COR_ALERTA);
        return saida;

    if nome == "grau":
        valores = __graus__(mapa);
    elif nome == "rank":
        # O "entity rank" do Maltego: os proprios vinculos mais a soma dos vinculos dos
        # vizinhos. Acha o hub que o grau simples nao acha -- quem liga poucos, mas importantes.
        grau = __graus__(mapa);
        vizinhos = __vizinhos__(mapa);
        valores = {c: grau[c] + sum(grau.get(v, 0) for v in vizinhos.get(c, ())) for c in caixas};
    elif nome == "referencias":
        valores = {c: len(c.entity.references or []) for c in caixas};
    else:
        return {};

    escalas = __escalar__(valores);
    return {c: (escalas.get(c, ESCALA_MIN), None) for c in caixas};
