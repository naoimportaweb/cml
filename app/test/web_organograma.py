#!/usr/bin/env python3
# Compara o layout do organograma do DESKTOP (Python) com o da WEB (JavaScript).
#
# Por que este teste existe: o dono escolheu reimplementar os diagramas na web em vez de
# reusar o desenho do desktop (SPEC.md §12). A consequencia conhecida e que o mesmo algoritmo
# passa a viver em dois lugares -- organization_chart_item.py e
# server/webpage/view/organizationchart/index.php. Duplicacao sem nada que a vigie diverge
# calada, e quem descobre e o usuario vendo dois desenhos diferentes do mesmo organograma.
#
# Entao aqui os dois rodam sobre a MESMA arvore e as posicoes sao comparadas caixa a caixa.
# A medida de texto difere entre Qt e canvas, entao a largura de cada caixa e INJETADA nos
# dois: o que se compara e o ALGORITMO (quem fica onde), nao a metrica de fonte.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/web_organograma.py
#
# Precisa de `node` no PATH; sem ele o teste avisa e nao falha (nem toda maquina de dev tem).

import os, sys, inspect, json, re, subprocess, tempfile, shutil;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
REPO = os.path.dirname(ROOT);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
os.environ["HOME"] = tempfile.mkdtemp(prefix="cml_weborg_");

VIEW = os.path.join(REPO, "server", "webpage", "view", "organizationchart", "index.php");

FALHAS = [];

# (id, pai, texto, quantas entidades, largura fingida)
ARVORE = [
    ("r",  None, "Presidência",          1, 160),
    ("a",  "r",  "Diretoria Financeira",  2, 220),
    ("b",  "r",  "Diretoria de Obras",    1, 200),
    ("c",  "r",  "Diretoria Jurídica",    3, 200),
    ("a1", "a",  "Contabilidade",         1, 140),
    ("a2", "a",  "Tesouraria",            1, 130),
    ("c1", "c",  "Contencioso",           0, 150),
    ("c2", "c",  "Consultivo",            0, 260),
    ("c3", "c",  "Compliance",            1, 120),
];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def __js_da_view__():
    """Tira do index.php o bloco <script>. Ler o arquivo de verdade (e nao uma copia) e o que
    faz o teste acusar quando alguem mexe na view."""
    with open(VIEW, encoding="utf-8") as arquivo:
        texto = arquivo.read();
    corpo = re.search(r"<script>(.*?)</script>", texto, re.S);
    if corpo == None:
        raise Exception("não achei o <script> em " + VIEW);
    return corpo.group(1);


def layout_python():
    from PySide6.QtWidgets import QApplication;
    from classlib.organization_chart.organization_chart import OrganizationChart;
    QApplication.instance() or QApplication(sys.argv);
    chart = OrganizationChart("org");
    por_id = {};
    for ident, pai, texto, _n, _largura in ARVORE:
        item = chart.addEntityItem(texto, organization_chart_item_parent_id=(por_id[pai].id if pai else None));
        por_id[ident] = item;
    # Injeta a medida, em vez de deixar cada lado medir: o que se compara e o algoritmo.
    for ident, _pai, _texto, n, largura in ARVORE:
        item = por_id[ident];
        item.w = largura;
        item.h = 42 + (0 if n == 0 else 6 + 15 * n);
        item.linhas_titulo = [_texto];
        item.buffer_lines_text = ["x"] * n;
    raiz = por_id["r"];
    raiz.posicionar({raiz.level: 0});
    alturas = {};
    raiz.alturas_por_nivel(alturas);
    topo, corrente = {}, 0;
    from classlib.organization_chart import organization_chart_item as modelo;
    for nivel in sorted(alturas.keys()):
        topo[nivel] = corrente;
        corrente = corrente + alturas[nivel] + modelo.ESPACO_NIVEL;
    raiz.aplicar_y(topo);
    return {ident: (por_id[ident].x, por_id[ident].y) for ident, _p, _t, _n, _l in ARVORE};


def layout_js():
    if shutil.which("node") == None:
        return None;
    programa = __js_da_view__() + """

// --- o arranjo do teste: injeta a medida e roda so o layout ---
var ARVORE = %s;
var porId = {};
ARVORE.forEach(function(r){
  porId[r[0]] = { id:r[0], texto:r[2], entidades:[], filhos:[], nivel:0, x:0, y:0,
                  w:r[4], h:42 + (r[3] === 0 ? 0 : 6 + 15 * r[3]),
                  linhas_titulo:[r[2]], linhas_nomes:new Array(r[3]).fill("x") };
});
ARVORE.forEach(function(r){ if (r[1]) { porId[r[1]].filhos.push(porId[r[0]]); } });
(function nivelar(n, nivel){ n.nivel = nivel; n.filhos.forEach(function(f){ nivelar(f, nivel+1); }); })(porId["r"], 0);

posicionar(porId["r"], {});
var alturas = {}; alturasPorNivel(porId["r"], alturas);
var niveis = Object.keys(alturas).map(Number).sort(function(a,b){ return a-b; });
var topo = {}, corrente = 0;
niveis.forEach(function(n){ topo[n] = corrente; corrente += alturas[n] + ESPACO_NIVEL; });
aplicarY(porId["r"], topo);

var saida = {};
ARVORE.forEach(function(r){ saida[r[0]] = [porId[r[0]].x, porId[r[0]].y]; });
console.log(JSON.stringify(saida));
""" % json.dumps(ARVORE);

    # O JS da view usa document/canvas no topo do arquivo; o teste nao tem DOM. Os pedacos de
    # DOM sao trocados por tocos -- medir() e pintar() nao entram no que se compara.
    tocos = """
var document = { getElementById: function(){ return { getContext: function(){ return { measureText: function(){ return {width: 0}; } }; }, textContent:"" }; },
                 querySelector: function(){ return { clientWidth: 1000, innerHTML:"" }; } };
var window = { location: { search: "" } };
var URLSearchParams = function(){ return { get: function(){ return ""; } }; };
var fetch = function(){ return { then: function(){ return this; }, catch: function(){ return this; } }; };
""";
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as arquivo:
        arquivo.write(tocos + programa);
        caminho = arquivo.name;
    try:
        saida = subprocess.run(["node", caminho], capture_output=True, text=True, timeout=60);
        if saida.returncode != 0:
            raise Exception(saida.stderr.strip()[:400]);
        return json.loads(saida.stdout.strip().splitlines()[-1]);
    finally:
        os.unlink(caminho);


def main():
    print("layout do desktop (Python)");
    py = layout_python();
    confere(len(py) == len(ARVORE), "%d caixas posicionadas" % len(py));

    print("\nlayout da web (JavaScript, lido do index.php)");
    try:
        js = layout_js();
    except Exception as erro:
        confere(False, "o JS da view não rodou: %s" % erro);
        js = None;
    if js == None and shutil.which("node") == None:
        print("  --   node não encontrado: comparação pulada (instale node para valer)");
        print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
        return 1 if len(FALHAS) > 0 else 0;
    if js != None:
        confere(len(js) == len(ARVORE), "%d caixas posicionadas" % len(js));

        print("\nos dois concordam, caixa a caixa");
        divergentes = [];
        for ident in sorted(py.keys()):
            if tuple(js.get(ident, (None, None))) != tuple(py[ident]):
                divergentes.append("%s: desktop=%s web=%s" % (ident, py[ident], js.get(ident)));
        confere(len(divergentes) == 0,
                "nenhuma divergência" if len(divergentes) == 0
                else "DIVERGIRAM: " + "; ".join(divergentes[:4]));

        print("\ne as duas implementações mantêm as mesmas promessas");
        caixas = {ident: (js[ident][0], js[ident][1], largura, 42 + (0 if n == 0 else 6 + 15 * n))
                  for ident, _p, _t, n, largura in ARVORE for _x in [0]};
        colisoes = 0;
        chaves = list(caixas.keys());
        for i in range(len(chaves)):
            for j in range(i + 1, len(chaves)):
                a, b = caixas[chaves[i]], caixas[chaves[j]];
                if not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1]):
                    colisoes = colisoes + 1;
        confere(colisoes == 0, "nenhuma caixa sobreposta no layout da web (%d)" % colisoes);

        from classlib.organization_chart import organization_chart_item as modelo;
        por_nivel = {};
        for ident, pai, _t, n, largura in ARVORE:
            nivel = 0 if pai == None else (1 if pai == "r" else 2);
            por_nivel.setdefault(nivel, []).append((js[ident][0], largura));
        menor = None;
        for nivel in por_nivel:
            linha = sorted(por_nivel[nivel]);
            for k in range(1, len(linha)):
                folga = linha[k][0] - (linha[k - 1][0] + linha[k - 1][1]);
                menor = folga if menor == None else min(menor, folga);
        confere(menor != None and menor >= modelo.ESPACO_IRMAO,
                "folga mínima na web = %s (exigido %d)" % (menor, modelo.ESPACO_IRMAO));

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
