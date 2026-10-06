#!/usr/bin/env python3
# Compara a agregacao do Mapa Regional do DESKTOP (Python) com a da WEB (JavaScript).
#
# Por que existe: o dono escolheu reimplementar os diagramas na web em vez de reusar o desenho
# do desktop (SPEC.md §11), e a aba Regional e o terceiro caso disso. O mesmo conjunto de
# regras passa a viver em dois lugares -- app/classlib/relationship/regional.py e o <script> de
# server/webpage/view/relationship/relationship.php. Duplicacao sem nada que a vigie diverge
# calada, e quem descobre e o usuario vendo dois resumos diferentes do mesmo mapa.
#
# Os dois rodam sobre o MESMO mapa e o resumo e comparado linha a linha: quais paises, em que
# ordem, com que contagem de entidades e de vinculos, e quantos sem bandeira. Nao se compara
# pixel nem HTML -- o que esta duplicado e a REGRA, e e ela que o teste prende.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/web_regional.py
#
# Precisa de `node` no PATH; sem ele o teste avisa e nao falha (nem toda maquina de dev tem).

import os, sys, inspect, json, re, subprocess, tempfile, shutil;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
REPO = os.path.dirname(ROOT);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
os.environ["HOME"] = tempfile.mkdtemp(prefix="cml_webreg_");

VIEW = os.path.join(REPO, "server", "webpage", "view", "relationship", "relationship.php");

FALHAS = [];
BANDEIRA = "iVBORw0KGgo=";

# O mesmo cenario do app/test/regional.py, de proposito: se os dois testes descrevessem mapas
# diferentes, um poderia passar com uma regra que o outro nem exercita.
#   (id, etype, nome, sub_etype, bandeira)
CAIXAS = [
    ("br",   "other",        "Brasil",        "country", BANDEIRA),
    ("pa",   "other",        "Panamá",        "country", BANDEIRA),
    ("su",   "other",        "Suíça",         "country", None),      # sem bandeira
    # Os quatro abaixo existem para exercitar os DOIS desempates da ordenação. Sem empate, a
    # regra de desempate não é exercitada e o teste passa mesmo com ela invertida de um lado
    # só -- foi o que aconteceu na primeira versão deste arquivo, descoberto sabotando o JS
    # de propósito e vendo o teste aprovar.
    ("cl",   "other",        "Chile",         "country", BANDEIRA),  # 1 entidade, 2 vínculos
    ("pe",   "other",        "Peru",          "country", BANDEIRA),  # 1 entidade, 1 vínculo
    ("ao",   "other",        "Angola",        "country", BANDEIRA),  # 0 e 0, empata com
    ("at",   "other",        "Áustria",       "country", BANDEIRA),  #   Áustria e Suíça
    ("ct",   "other",        "Contrato 44",   None,      None),      # sem sub-tipo: não é país
    ("zeca", "person",       "Zeca",          None,      None),
    ("ana",  "person",       "Ana",           None,      None),
    ("org",  "organization", "Construtora X", None,      None),
];
# (id, verbo, de, para)
VINCULOS = [
    ("v1", "atua em",   "zeca", "br"),
    ("v2", "nasceu em", "zeca", "br"),   # a MESMA pessoa, 3 vínculos: conta 1 entidade
    ("v3", "votou em",  "zeca", "br"),
    ("v4", "atua em",   "ana",  "br"),
    ("v5", "atua em",   "org",  "br"),
    ("v6", "atua em",   "org",  "pa"),
    ("v7", "cita",      "zeca", "ct"),   # não é país: não entra em lugar nenhum
    # Chile e Peru têm a MESMA contagem de entidades (1): quem decide é o número de vínculos.
    ("v8",  "atua em",  "ana",  "cl"),
    ("v9",  "sediada",  "ana",  "cl"),
    ("v10", "atua em",  "ana",  "pe"),
];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def resumo_python():
    from PySide6.QtWidgets import QApplication;
    from classlib.relationship.maprelationship import MapRelationship;
    from classlib.relationship import regional;
    QApplication.instance() or QApplication(sys.argv);
    mapa = MapRelationship();
    por_id = {};
    for ident, etype, nome, subtipo, bandeira in CAIXAS:
        caixa = mapa.addEntity(etype, 0, 0, text=nome);
        caixa.entity.sub_etype_name = subtipo;
        caixa.entity.face = bandeira;
        por_id[ident] = caixa;
    for _ident, verbo, de, para in VINCULOS:
        elo = mapa.addEntity("link", 0, 0, text=verbo);
        elo.addFrom(por_id[de]); elo.addTo(por_id[para]);
    return [{"nome": r["nome"], "entidades": r["entidades"], "vinculos": r["vinculos"],
             "bandeira": bool(r["bandeira"])} for r in regional.agregar(mapa)];


def __js_da_view__():
    """Tira do relationship.php o bloco <script>, do arquivo DE VERDADE -- e o que faz o teste
    acusar quando alguem mexe na view. O PHP interpolado dentro do JS vira `null`, e a chamada
    de carga do fim e cortada: aqui nao ha servidor nem DOM."""
    with open(VIEW, encoding="utf-8") as arquivo:
        texto = arquivo.read();
    corpo = re.search(r"<script>(.*?)</script>", texto, re.S);
    if corpo == None:
        raise Exception("não achei o <script> em " + VIEW);
    js = corpo.group(1);
    js = re.sub(r"<\?php.*?\?>", "null", js, flags=re.S);
    js = js.replace("getMap(MAP_ID, DOMAIN, callbackMap);", "");
    return js;


def payload():
    """O mesmo mapa na forma que o relationship_load.php devolve."""
    elementos = [];
    for ident, etype, nome, subtipo, bandeira in CAIXAS:
        elementos.append({"id": ident, "etype": etype, "text_label": nome,
                          "sub_etype_name": subtipo, "face": bandeira, "to": [], "from": []});
    for ident, verbo, de, para in VINCULOS:
        elementos.append({"id": ident, "etype": "link", "text_label": verbo,
                          "sub_etype_name": None, "face": None,
                          "from": [{"id": de}], "to": [{"id": para}]});
    return {"id": "m", "name": "Regional", "keyword": "", "show_face": 1,
            "elements": elementos, "width": 100, "height": 100};


def resumo_js():
    if shutil.which("node") == None:
        return None;
    programa = __js_da_view__() + """

var JS_MAPA = %s;
var saida = agregarRegional(JS_MAPA).map(function(r){
  return { nome: r.nome, entidades: r.entidades, vinculos: r.vinculos, bandeira: !!r.bandeira };
});
console.log(JSON.stringify({ resumo: saida, sem_bandeira: semBandeira(agregarRegional(JS_MAPA)) }));
""" % json.dumps(payload());

    # O JS da view fala com DOM e jQuery no topo; o teste nao tem nenhum dos dois. O que se
    # compara e a agregacao, que e funcao pura -- o resto vira toco.
    tocos = """
var _elo = new Proxy(function(){ return _elo; }, {
  get: function(){ return function(){ return _elo; }; },
  apply: function(){ return _elo; }
});
var $ = function(){ return _elo; };
$.ajax = function(){ return _elo; };
var document = { getElementById: function(){ return null; },
                 querySelector: function(){ return null; },
                 title: "" };
var window = { location: { search: "" }, devicePixelRatio: 1,
               addEventListener: function(){}, getComputedStyle: function(){ return { getPropertyValue: function(){ return ""; } }; } };
var Image = function(){ return {}; };
""";
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as arquivo:
        arquivo.write(tocos + programa);
        caminho = arquivo.name;
    try:
        saida = subprocess.run(["node", caminho], capture_output=True, text=True, timeout=60);
        if saida.returncode != 0:
            raise Exception(saida.stderr.strip()[:500]);
        return json.loads(saida.stdout.strip().splitlines()[-1]);
    finally:
        os.unlink(caminho);


def main():
    print("resumo do desktop (Python, regional.agregar)");
    py = resumo_python();
    nomes = [r["nome"] for r in py];
    confere(len(py) == 7, "7 países, e o 'Contrato 44' sem sub-tipo ficou fora (%d)" % len(py));
    confere(nomes[0] == "Brasil", "Brasil primeiro (o mais tocado)");
    br = [r for r in py if r["nome"] == "Brasil"][0];
    confere(br["entidades"] == 3 and br["vinculos"] == 5,
            "Brasil: 3 entidades distintas e 5 vínculos (%d/%d)" % (br["entidades"], br["vinculos"]));
    confere(nomes.index("Chile") < nomes.index("Peru"),
            "empate em entidades: mais vínculos primeiro (Chile antes de Peru)");
    confere(nomes.index("Panamá") < nomes.index("Peru"),
            "empate em entidades e vínculos: nome decide (Panamá antes de Peru)");
    # ⚠️ A ordem por nome é por PONTO DE CÓDIGO, não alfabética com acento dobrado: o "s" de
    # Suíça vale 0x73 e o "á" de Áustria vale 0xE1, então Áustria sai DEPOIS de Suíça -- e
    # sairia depois de Zâmbia também. Os dois lados fazem igual (Python compara por code point,
    # o JS compara UTF-16 code unit), e é a igualdade que este teste existe para prender. A
    # asserção descreve o que o sistema FAZ; eu havia escrito aqui o que eu esperava, e o teste
    # acusou a mim, não ao código.
    confere(nomes.index("Angola") < nomes.index("Suíça") < nomes.index("Áustria"),
            "os três sem vínculo saem em ordem de ponto de código: %s" % nomes[-3:]);

    print("\nresumo da web (JavaScript, lido do relationship.php)");
    try:
        js = resumo_js();
    except Exception as erro:
        confere(False, "o JS da view não rodou: %s" % erro);
        js = None;
    if js == None and shutil.which("node") == None:
        print("  --   node não encontrado: comparação pulada (instale node para valer)");
        print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
        return 1 if len(FALHAS) > 0 else 0;

    if js != None:
        web = js["resumo"];
        confere(len(web) == len(py), "mesmo número de países (%d x %d)" % (len(py), len(web)));

        print("\nos dois concordam, linha a linha");
        divergentes = [];
        for i in range(max(len(py), len(web))):
            a = py[i] if i < len(py) else None;
            b = web[i] if i < len(web) else None;
            if a != b:
                divergentes.append("posição %d: desktop=%s web=%s" % (i, a, b));
        confere(len(divergentes) == 0,
                "nenhuma divergência: mesma ordem, mesmas contagens, mesma bandeira"
                if len(divergentes) == 0 else "DIVERGIRAM: " + " | ".join(divergentes[:3]));

        print("\ne o aviso de bandeira que falta é o mesmo nos dois");
        from classlib.relationship import regional;
        faltam_py = len([r for r in py if not r["bandeira"]]);
        confere(js["sem_bandeira"] == faltam_py,
                "%d sem bandeira nos dois (web=%d)" % (faltam_py, js["sem_bandeira"]));
        confere(faltam_py == 1, "e é 1, a Suíça");

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
