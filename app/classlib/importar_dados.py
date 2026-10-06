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

import csv, io, json, os, sys, inspect, re;
from xml.etree import ElementTree;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append(os.path.dirname(CURRENTDIR));

from transform.nucleo import Resultado;

FORMATOS = ("csv", "graphml", "stix");

# Como um objeto STIX vira entidade do CML. E o inverso do mapa do exportar_dados: o que sai
# como threat-actor volta como Other com sub-tipo "threat actor", e identity volta como pessoa
# ou organizacao conforme o identity_class -- que e a unica coisa que distingue as duas la.
STIX_PARA_ETYPE = {"identity": "other", "threat-actor": "other", "malware": "other",
                   "tool": "other", "campaign": "other", "location": "other",
                   "vulnerability": "other", "intrusion-set": "other", "infrastructure": "other"};
STIX_SUBTIPO = {"threat-actor": "threat actor", "malware": "malware", "tool": "tool",
                "campaign": "campanha", "location": "country", "vulnerability": "vulnerabilidade",
                "intrusion-set": "threat actor", "infrastructure": "infraestrutura"};
IDENTITY_CLASS = {"individual": "person", "organization": "organization", "group": "organization",
                  "class": "other", "system": "other", "unknown": "other"};
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


def de_stix(caminho):
    """Bundle STIX 2.1 -> Resultado. Le o que o nosso exportar_dados escreve e tambem bundle de
    fora (MISP, OpenCTI): e o formato em que CTI circula, e o banco de entidades do CML ja nasce
    de MISP Galaxy.

    O `relationship` do STIX aponta por `source_ref`/`target_ref`, que sao ids de objeto -- a
    aresta que cita objeto ausente do bundle e IGNORADA, nao importada torta."""
    try:
        with open(caminho, "r", encoding="utf-8", errors="replace") as arquivo:
            dados = json.load(arquivo);
    except ValueError as erro:
        raise ErroImportacao("O arquivo não é um JSON válido: %s" % erro);
    if not isinstance(dados, dict):
        raise ErroImportacao("O arquivo não tem a forma de um bundle STIX.");
    objetos = dados.get("objects");
    if not isinstance(objetos, list) or len(objetos) == 0:
        raise ErroImportacao("O bundle não tem objetos.");

    resultado = Resultado();
    chave_por_id = {};
    relacoes = [];
    for objeto in objetos:
        if not isinstance(objeto, dict):
            continue;
        tipo = str(objeto.get("type") or "").strip().lower();
        if tipo == "relationship":
            relacoes.append(objeto);
            continue;
        if tipo not in STIX_PARA_ETYPE:
            continue;   # marking-definition, note, observed-data...: nao viram entidade
        nome = __norm__(objeto.get("name"));
        if nome == "":
            continue;
        chave = "e%d" % (len(chave_por_id) + 1);
        chave_por_id[objeto.get("id")] = chave;
        if tipo == "identity":
            etype = IDENTITY_CLASS.get(str(objeto.get("identity_class") or "").lower(), "other");
            sub = "";
        else:
            etype = STIX_PARA_ETYPE[tipo];
            sub = STIX_SUBTIPO.get(tipo, "");
        apelidos = objeto.get("aliases") or [];
        resultado.entidade(chave, nome, etype=etype, sub_etype=sub,
                           small_label=__norm__(apelidos[0]) if len(apelidos) > 0 else "",
                           description=__norm__(objeto.get("description")));
    if len(resultado.entidades) == 0:
        raise ErroImportacao("Nenhum objeto do bundle virou entidade (só há relacionamentos?).");

    for relacao in relacoes:
        de = chave_por_id.get(relacao.get("source_ref"));
        para = chave_por_id.get(relacao.get("target_ref"));
        if de == None or para == None:
            continue;
        verbo = str(relacao.get("relationship_type") or "").replace("-", " ").strip();
        resultado.vinculo(de, para, verbo or "relacionado a",
                          start_date=__data_stix__(relacao.get("start_time")),
                          end_date=__data_stix__(relacao.get("stop_time")));
    resultado.aviso("Vindo de STIX: confira o tipo e o sub-tipo de cada entidade antes de aceitar.");
    return resultado;


def __data_stix__(valor):
    """STIX usa timestamp ISO; o CML guarda a data. Fica so a parte da data, e so se tiver a
    forma certa -- inventar data a partir de texto solto e pior que nao ter data."""
    texto = str(valor or "").strip();
    if len(texto) >= 10 and re.match(r"^\d{4}-\d{2}-\d{2}", texto):
        return texto[:10];
    return None;


def importar(caminho, formato=None):
    if not os.path.exists(caminho):
        raise ErroImportacao("Arquivo não encontrado: %s" % caminho);
    if formato == None:
        formato = os.path.splitext(caminho)[1].lstrip(".").lower();
    formato = (formato or "").lower();
    if formato == "json":
        formato = "stix";   # o bundle STIX sai com extensao .json
    if formato not in FORMATOS:
        raise ErroImportacao("Formato não suportado: %s (use csv, graphml ou stix)." % (formato or "?"));
    if formato == "csv":
        return de_csv(caminho);
    if formato == "stix":
        return de_stix(caminho);
    return de_graphml(caminho);
