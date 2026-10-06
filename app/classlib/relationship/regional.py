# Mapa regional: que paises/regioes a investigacao toca, e com que peso (SPEC.md §5).
#
# NAO E UMA PROJECAO GEOGRAFICA, e isto e decisao, nao limitacao escondida. O banco do CML
# **nao guarda coordenada nenhuma** -- nao ha lat/lon em entity nem em lugar algum do schema --
# e o repositorio nao traz geometria de pais. Desenhar um mapa de verdade exigiria uma das
# duas, e inventar contorno ou centroide de memoria daria um desenho que parece certo e esta
# errado, que num produto de investigacao e pior do que nao ter o desenho.
#
# O que ele FAZ com o que existe: agrupa pelas entidades-pais que ja estao no mapa, conta
# quantas entidades tocam cada uma, e desenha com a BANDEIRA que o country_seed.py ja gravou
# em entity_face. Responde "quais paises esta investigacao toca e com que peso", que e a
# pergunta do mapa regional; so nao responde "onde no globo".
#
# Quando houver geometria (um GeoJSON em app/resources/paises.geojson) a vista passa a
# desenhar o coropleto de verdade -- ver mapa_regional.py. O ponto de juncao ja existe e e
# confiavel: o id de um pais semeado e uuid5 do ISO, entao da para casar com qualquer base
# externa pelo codigo, sem depender do nome escrito.

import os, sys, inspect;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append(os.path.dirname(os.path.dirname(CURRENTDIR)));

# Como se reconhece um pais. O country_seed.py passou a gravar sub_etype "country"; estas
# outras grafias existem para quem cadastrou a mao antes disso.
SUBTIPOS_PAIS = ("country", "pais", "país", "countries", "nacao", "nação");


def eh_pais(elemento):
    if elemento == None or elemento.entity == None:
        return False;
    if elemento.entity.etype == "link":
        return False;
    return str(elemento.entity.sub_etype_name or "").strip().lower() in SUBTIPOS_PAIS;


def __vinculos__(mapa):
    return [e for e in mapa.elements if e.entity.etype == "link"];


def agregar(mapa):
    """[{caixa, nome, bandeira, entidades, vinculos}] por pais, do mais tocado ao menos.

    `entidades` conta quantas caixas DISTINTAS se ligam ao pais -- nao quantos vinculos. Duas
    pessoas ligadas ao mesmo pais por tres vinculos cada sao duas entidades, nao seis: o que
    o mapa regional responde e "quanta gente desta investigacao passa por aqui".
    """
    paises = [e for e in mapa.elements if eh_pais(e)];
    if len(paises) == 0:
        return [];
    saida = [];
    for pais in paises:
        tocam = set();
        quantos_vinculos = 0;
        for vinculo in __vinculos__(mapa):
            pontas = [p.entity for p in list(vinculo.to_entity) + list(vinculo.from_entity) if p.entity != None];
            if pais not in pontas:
                continue;
            quantos_vinculos = quantos_vinculos + 1;
            for outra in pontas:
                if outra is not pais and outra.entity.etype != "link":
                    tocam.add(id(outra));
        saida.append({"caixa": pais,
                      "nome": str(pais.entity.text or "").strip() or "(sem nome)",
                      "bandeira": pais.entity.face,
                      "entidades": len(tocam),
                      "vinculos": quantos_vinculos});
    # Do mais tocado ao menos; empate pelo nome, para a ordem nao dancar entre aberturas.
    saida.sort(key=lambda r: (-r["entidades"], -r["vinculos"], r["nome"].lower()));
    return saida;


def sem_bandeira(resumo):
    """Quantos paises do resumo nao tem bandeira. A vista avisa em vez de desenhar um buraco:
    bandeira que falta e dado que falta (o country_seed nao rodou, ou a entidade foi criada a
    mao), nao defeito do desenho."""
    return len([r for r in resumo if not r["bandeira"]]);
