# Importa CSV e GraphML como PROPOSTA (SPEC.md §6).
#
# A escolha de desenho que importa: o arquivo NAO entra direto no mapa. Ele e lido para um
# `Resultado` -- a mesma estrutura que um transform devolve -- e entregue ao painel Proposta,
# que ja faz o que a lei do projeto manda: buscar antes de criar, oferecer reaproveitar a
# entidade que ja existe, e so gravar no save do mapa.
#
# Era o unico jeito de importar sem furar duas regras de uma vez: "entidade e global" e
# "curadoria humana". Um importador proprio criaria entidade nova para cada linha da planilha,
# e um mapa de 300 linhas viraria 300 duplicatas para o merge_to limpar depois.
#
# Le o que o exportar_dados.py escreve, e tambem planilha de fora: as colunas sao reconhecidas
# por NOME (varias grafias), nao por posicao.

import csv, io, os, sys, inspect, re;
from xml.etree import ElementTree;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append(os.path.dirname(CURRENTDIR));

from transform.nucleo import Resultado;

FORMATOS = ("csv", "graphml");
ETYPES = ("person", "organization", "other");

# Grafias aceitas por coluna. O arquivo do CML usa a primeira; as outras existem para planilha
# escrita a mao e para export de outras ferramentas.
COLUNAS = {
    "nome":        ("nome", "name", "label", "text_label", "titulo", "título"),
    "tipo":        ("tipo", "type", "etype", "categoria"),
    "sub_tipo":    ("sub_tipo", "subtipo", "sub_type", "subtype"),
    "apelido":     ("apelido", "small_label", "sigla", "alias"),
    "descricao":   ("descricao", "descrição", "description", "obs", "observacao"),
    # inicio_de/fim_de/inicio_para/fim_para sao os nomes que o NOSSO exportar_dados escreve
    # (e os atributos da aresta no GraphML). Sem eles, exportar e reimportar perdia as datas do
    # vinculo em silencio -- justamente a ida e volta para a qual o modulo foi escrito.
    "inicio":      ("inicio", "início", "start", "start_date", "data_inicio", "inicio_de", "inicio_para"),
    "fim":         ("fim", "end", "end_date", "data_fim", "fim_de", "fim_para"),
    "de":          ("de", "source", "from", "origem"),
    "para":        ("para", "target", "to", "destino"),
    "verbo":       ("verbo", "label", "relacao", "relação", "tipo_vinculo"),
};

TIPOS = {"person": "person", "pessoa": "person", "people": "person",
         "organization": "organization", "organizacao": "organization", "organização": "organization",
         "empresa": "organization", "org": "organization",
         "other": "other", "outro": "other", "coisa": "other"};


class ErroImportacao(Exception):
    pass;


def __norm__(texto):
    return " ".join(str(texto or "").split());


def __chave__(nome):
    return re.sub(r"[^a-z0-9_]", "", str(nome or "").strip().lower().replace(" ", "_"));


def __mapear__(cabecalho):
    """Posicao de cada coluna conhecida, pelo NOME. Coluna desconhecida e ignorada em silencio:
    planilha de fora costuma ter colunas que nao nos dizem respeito."""
    posicao = {};
    for i in range(len(cabecalho)):
        chave = __chave__(cabecalho[i]);
        for campo, grafias in COLUNAS.items():
            if chave in [__chave__(g) for g in grafias] and campo not in posicao:
                posicao[campo] = i;
    return posicao;


def __valor__(linha, posicao, campo):
    i = posicao.get(campo);
    if i == None or i >= len(linha):
        return "";
    return __norm__(linha[i]);


def __etype__(texto, padrao="other"):
    return TIPOS.get(__chave__(texto), padrao);


def __dialeto__(amostra):
    # Planilha brasileira sai com ';' e a de fora com ',': detectar evita obrigar o usuario a
    # saber disso.
    try:
        return csv.Sniffer().sniff(amostra, delimiters=";,\t").delimiter;
    except Exception:
        return ";" if amostra.count(";") >= amostra.count(",") else ",";


def __ler_csv__(caminho):
    with open(caminho, "r", encoding="utf-8-sig", errors="replace") as arquivo:
        bruto = arquivo.read();
    if bruto.strip() == "":
        raise ErroImportacao("O arquivo está vazio.");
    delimitador = __dialeto__(bruto[:4000]);
    linhas = list(csv.reader(io.StringIO(bruto), delimiter=delimitador));
    linhas = [l for l in linhas if any(str(c).strip() != "" for c in l)];
    if len(linhas) < 2:
        raise ErroImportacao("O CSV não tem cabeçalho e pelo menos uma linha.");
    return linhas[0], linhas[1:];


def de_csv(caminho):
    """Um CSV de ENTIDADES (tem coluna de nome) ou de VINCULOS (tem de/para). Devolve Resultado.

    O de vinculos cria tambem as entidades citadas nas pontas: importar so a aresta deixaria
    ponta solta, e a planilha de vinculos costuma ser a unica que a pessoa tem."""
    cabecalho, linhas = __ler_csv__(caminho);
    posicao = __mapear__(cabecalho);
    resultado = Resultado();
    if "de" in posicao and "para" in posicao:
        chaves = {};
        def chave_de(nome):
            if nome not in chaves:
                chaves[nome] = "e%d" % (len(chaves) + 1);
                resultado.entidade(chaves[nome], nome, etype="other");
            return chaves[nome];
        for linha in linhas:
            de = __valor__(linha, posicao, "de");
            para = __valor__(linha, posicao, "para");
            if de == "" or para == "":
                continue;
            resultado.vinculo(chave_de(de), chave_de(para),
                              __valor__(linha, posicao, "verbo") or "relacionado a",
                              start_date=__valor__(linha, posicao, "inicio") or None,
                              end_date=__valor__(linha, posicao, "fim") or None);
        if len(resultado.vinculos) == 0:
            raise ErroImportacao("Nenhuma linha com 'de' e 'para' preenchidos.");
        resultado.aviso("Entidades criadas a partir das pontas dos vínculos: confira o tipo de cada uma.");
        return resultado;

    if "nome" not in posicao:
        raise ErroImportacao("Não achei a coluna de nome. Esperado algo como: %s."
                             % ", ".join(COLUNAS["nome"]));
    for i in range(len(linhas)):
        nome = __valor__(linhas[i], posicao, "nome");
        if nome == "":
            continue;
        resultado.entidade("e%d" % (i + 1), nome,
                           etype=__etype__(__valor__(linhas[i], posicao, "tipo")),
                           sub_etype=__valor__(linhas[i], posicao, "sub_tipo"),
                           small_label=__valor__(linhas[i], posicao, "apelido"),
                           description=__valor__(linhas[i], posicao, "descricao"));
    if len(resultado.entidades) == 0:
        raise ErroImportacao("Nenhuma linha com nome preenchido.");
    return resultado;


def de_graphml(caminho):
    """GraphML de qualquer ferramenta (o nosso, Gephi, yEd). Devolve Resultado."""
    try:
        raiz = ElementTree.parse(caminho).getroot();
    except ElementTree.ParseError as erro:
        raise ErroImportacao("O arquivo não é um GraphML válido: %s" % erro);
    ns = "";
    if raiz.tag.startswith("{"):
        ns = raiz.tag[:raiz.tag.index("}") + 1];

    # <key id="d0" attr.name="nome"/> -> traduz o id da chave para o nome do atributo
    nome_da_chave = {};
    for chave in raiz.findall("%skey" % ns):
        nome_da_chave[chave.get("id")] = __chave__(chave.get("attr.name") or chave.get("id"));

    def atributos(elemento):
        saida = {};
        for dado in elemento.findall("%sdata" % ns):
            saida[nome_da_chave.get(dado.get("key"), __chave__(dado.get("key")))] = __norm__(dado.text);
        return saida;

    def campo(atrs, nome_campo, padrao=""):
        for grafia in COLUNAS[nome_campo]:
            if __chave__(grafia) in atrs:
                return atrs[__chave__(grafia)];
        return padrao;

    resultado = Resultado();
    chave_por_id = {};
    nos = raiz.findall(".//%snode" % ns);
    if len(nos) == 0:
        raise ErroImportacao("O GraphML não tem nenhum nó.");
    for i in range(len(nos)):
        atrs = atributos(nos[i]);
        nome = campo(atrs, "nome") or nos[i].get("id") or "";
        if __norm__(nome) == "":
            continue;
        chave = "e%d" % (i + 1);
        chave_por_id[nos[i].get("id")] = chave;
        resultado.entidade(chave, nome, etype=__etype__(campo(atrs, "tipo")),
                           sub_etype=campo(atrs, "sub_tipo"), small_label=campo(atrs, "apelido"),
                           description=campo(atrs, "descricao"));
    for aresta in raiz.findall(".//%sedge" % ns):
        de = chave_por_id.get(aresta.get("source"));
        para = chave_por_id.get(aresta.get("target"));
        if de == None or para == None:
            continue;   # aresta apontando para no que nao existe: ignorada, nao importada torta
        atrs = atributos(aresta);
        resultado.vinculo(de, para, campo(atrs, "verbo") or "relacionado a",
                          start_date=campo(atrs, "inicio") or None,
                          end_date=campo(atrs, "fim") or None);
    if len(resultado.entidades) == 0:
        raise ErroImportacao("Nenhum nó com nome.");
    return resultado;


def importar(caminho, formato=None):
    if not os.path.exists(caminho):
        raise ErroImportacao("Arquivo não encontrado: %s" % caminho);
    if formato == None:
        formato = os.path.splitext(caminho)[1].lstrip(".").lower();
    formato = (formato or "").lower();
    if formato not in FORMATOS:
        raise ErroImportacao("Formato não suportado: %s (use csv ou graphml)." % (formato or "?"));
    return de_csv(caminho) if formato == "csv" else de_graphml(caminho);
