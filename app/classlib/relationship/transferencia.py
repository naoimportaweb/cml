# Copiar e colar caixas e vinculos entre mapas (SPEC.md §3.3).
#
# A decisao que manda aqui e a lei do modelo: ENTIDADE E GLOBAL. Colar nao duplica a entidade --
# cria uma CAIXA nova apontando para a MESMA entidade (mesmo `entity_id`). Dois mapas passam a
# mostrar a mesma pessoa, que e exatamente o que o analista quer ao levar um pedaço de uma
# investigacao para outra. Duplicar a entidade criaria um irmao gemeo que o merge_to teria de
# juntar depois.
#
# O que viaja e TEXTO (JSON) na area de transferencia do sistema, com um cabecalho proprio:
# assim funciona entre janelas e entre duas execucoes do CML, e colar texto de qualquer outro
# lugar e recusado sem susto.
#
# Vinculo so viaja se AS DUAS PONTAS estiverem na selecao: meia aresta nao e dado, e colada
# viraria ponta solta no mapa de destino.

import json;

CABECALHO = "CML-MAPA-1";
# Tipos que o mapa aceita. Nao e redundante com o cabecalho: o addEntity do modelo tem quatro
# elif e NENHUM else -- tipo desconhecido escapa dos quatro e a funcao devolve
# `self.elements[-1]`, que e uma caixa JA EXISTENTE; os dados colados eram escritos por cima
# dela (ou estourava IndexError num mapa vazio). Texto da area de transferencia e dado de fora,
# mesmo tendo o nosso cabecalho.
ETYPES = ("person", "organization", "other");
DESLOCAMENTO = 30;   # colar no mesmo lugar esconderia a copia debaixo do original


class ErroTransferencia(Exception):
    pass;


def __caixa_para_json__(caixa):
    entidade = caixa.entity;
    return {"entity_id": entidade.id, "etype": entidade.etype,
            "text": entidade.text, "small_label": entidade.small_label,
            "description": entidade.full_description, "wikipedia": entidade.wikipedia,
            "default_url": entidade.default_url, "sub_etype_id": entidade.sub_etype_id,
            "sub_etype_name": entidade.sub_etype_name,
            "x": caixa.x, "y": caixa.y,
            "start_date": caixa.start_date, "end_date": caixa.end_date,
            "format_date": caixa.format_date};


def __pontas_para_json__(lista, indice_por_caixa):
    saida = [];
    for ponta in lista:
        if ponta.entity in indice_por_caixa:
            saida.append({"caixa": indice_por_caixa[ponta.entity],
                          "start_date": ponta.start_date, "end_date": ponta.end_date,
                          "format_date": ponta.format_date});
    return saida;


def copiar(elementos):
    """Serializa a selecao. Devolve o texto que vai para a area de transferencia."""
    caixas = [e for e in elementos if e.entity.etype != "link"];
    if len(caixas) == 0:
        raise ErroTransferencia("Selecione ao menos uma caixa para copiar.");
    indice = {caixa: i for i, caixa in enumerate(caixas)};
    vinculos = [];
    for elemento in elementos:
        if elemento.entity.etype != "link":
            continue;
        de = __pontas_para_json__(elemento.from_entity, indice);
        para = __pontas_para_json__(elemento.to_entity, indice);
        # As duas pontas tem de estar na selecao: vinculo pela metade vira ponta solta no
        # destino, que e pior que nao colar o vinculo.
        if len(de) == len(elemento.from_entity) and len(para) == len(elemento.to_entity) \
           and len(de) > 0 and len(para) > 0:
            vinculos.append({"text": elemento.entity.text, "de": de, "para": para});
    return json.dumps({"cabecalho": CABECALHO, "caixas": [__caixa_para_json__(c) for c in caixas],
                       "vinculos": vinculos}, ensure_ascii=False);


def pode_colar(texto):
    try:
        dados = json.loads(texto or "");
    except Exception:
        return False;
    return isinstance(dados, dict) and dados.get("cabecalho") == CABECALHO;


def colar(mapa, texto, deslocamento=DESLOCAMENTO):
    """Cria as caixas e vinculos no mapa. Devolve (caixas, vinculos, novos_elementos).

    Nao empilha desfazer sozinho: quem chama envolve em Operacao, para colar e qualquer ajuste
    que venha junto sairem com UM Ctrl+Z."""
    if mapa.getLocked():
        raise ErroTransferencia("O mapa está travado (somente leitura).");
    if not pode_colar(texto):
        raise ErroTransferencia("A área de transferência não tem um pedaço de mapa do CML.");
    dados = json.loads(texto);
    caixas_json = [c for c in dados.get("caixas", []) if (c.get("etype") or "other") != "link"];
    # Confere TUDO antes de criar qualquer coisa: colagem pela metade num mapa e pior que
    # colagem recusada.
    for item in caixas_json:
        if (item.get("etype") or "other") not in ETYPES:
            raise ErroTransferencia("A área de transferência tem um tipo de caixa desconhecido: %s."
                                    % item.get("etype"));
    for vinculo_json in dados.get("vinculos", []):
        for ponta in list(vinculo_json.get("de", [])) + list(vinculo_json.get("para", [])):
            indice = ponta.get("caixa");
            if not isinstance(indice, int) or indice < 0 or indice >= len(caixas_json):
                raise ErroTransferencia("A área de transferência tem um vínculo com ponta inválida.");
    criadas = [];
    for item in caixas_json:
        etype = item.get("etype") or "other";
        caixa = mapa.addEntity(etype, int(item.get("x") or 0) + deslocamento,
                               int(item.get("y") or 0) + deslocamento,
                               text=item.get("text"),
                               entity_id_=item.get("entity_id"),
                               wikipedia=item.get("wikipedia"));
        entidade = caixa.entity;
        entidade.small_label = item.get("small_label");
        entidade.full_description = item.get("description") or "";
        entidade.default_url = item.get("default_url");
        entidade.sub_etype_id = item.get("sub_etype_id");
        entidade.sub_etype_name = item.get("sub_etype_name");
        caixa.start_date = item.get("start_date");
        caixa.end_date = item.get("end_date");
        caixa.format_date = item.get("format_date") or "yyyy-MM-dd";
        criadas.append(caixa);

    vinculos = 0;
    novos = list(criadas);
    for item in dados.get("vinculos", []):
        pontas_de = list(item.get("de", []));
        pontas_para = list(item.get("para", []));
        if len(pontas_de) == 0 or len(pontas_para) == 0:
            continue;
        meio_x = sum(criadas[p["caixa"]].x for p in pontas_de + pontas_para) / float(len(pontas_de) + len(pontas_para));
        meio_y = sum(criadas[p["caixa"]].y for p in pontas_de + pontas_para) / float(len(pontas_de) + len(pontas_para));
        vinculo = mapa.addEntity("link", int(meio_x), int(meio_y), text=item.get("text"));
        for ponta in pontas_de:
            vinculo.addFrom(criadas[ponta["caixa"]], ponta.get("start_date"), ponta.get("end_date"),
                            ponta.get("format_date") or "yyyy-MM-dd");
        for ponta in pontas_para:
            vinculo.addTo(criadas[ponta["caixa"]], ponta.get("start_date"), ponta.get("end_date"),
                          ponta.get("format_date") or "yyyy-MM-dd");
        novos.append(vinculo);
        vinculos = vinculos + 1;
    return (len(criadas), vinculos, novos);
