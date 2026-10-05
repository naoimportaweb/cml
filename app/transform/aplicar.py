"""Aplica uma proposta de transform no mapa. Sem Qt: so mexe no modelo (MapRelationship).

Nada persiste aqui — as caixas entram no modelo e o servidor so ve tudo no save do mapa
(mesmo comportamento do incorporate e do bot de entidades). As novas caixas nascem em
circulo ao redor da caixa de origem (como o Maltego espalha o resultado), nao em grade."""

import os, sys, inspect, math;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( CURRENTDIR ) );

from transform.nucleo import ENTRADA, norm;
from classlib.relationship.comandos import Operacao;

CAMPOS_ENTIDADE = ["id", "etype", "text_label", "description", "default_url", "data_extra", "wikipedia", "small_label", "icon"];


def _referenciar(caixa, refs):
    """Anexa as referencias que a caixa ainda nao tem (comparando link1). Devolve quantas entraram."""
    n = 0;
    for r in refs or []:
        link = str(r.get("link1") or "").strip();
        # cml:// e marcador interno ("veio da base"), nao uma fonte navegavel.
        if link == "" or link.startswith("cml://"):
            continue;
        if any(str(x.link1 or "").strip() == link for x in caixa.entity.references):
            continue;
        caixa.addReference(r.get("title") or link, link, descricao=r.get("descricao") or "");
        n += 1;
    return n;


def _completar(js):
    d = {k: None for k in CAMPOS_ENTIDADE};
    d.update(js);
    for k in ("description", "text_label", "small_label"):
        d[k] = d[k] or "";
    return d;


def aplicar(mapa, origem, resultado, escolhas_entidade, escolhas_vinculo, subtipos_validos=None, aplicar_subtipo=None):
    """resultado: Resultado. escolhas_entidade: {chave: {"aceitar", "etype", "reusar" (dict da base ou None)}}.
    escolhas_vinculo: lista de bool, mesma ordem de resultado.vinculos.
    Devolve um dict-relatorio (novas, reusadas, vinculos, refs, sem_subtipo)."""
    if mapa.getLocked():
        raise Exception("O mapa está travado (somente leitura).");
    # Um transform aceito pode trazer dezenas de caixas e vinculos de uma vez: tem de sair da
    # tela com UM desfazer, nao com trinta.
    with Operacao(mapa, "Aplicar transform"):
        return __aplicar__(mapa, origem, resultado, escolhas_entidade, escolhas_vinculo,
                           subtipos_validos, aplicar_subtipo);


def __aplicar__(mapa, origem, resultado, escolhas_entidade, escolhas_vinculo, subtipos_validos=None, aplicar_subtipo=None):

    cx = origem.x + origem.w / 2.0;
    cy = origem.y + origem.h / 2.0;

    # O que ja esta no mapa, por id de entidade e por nome normalizado: aceitar o mesmo
    # resultado duas vezes (ou um resultado que cita algo ja desenhado) nao duplica caixa.
    por_id, por_nome = {}, {};
    for el in mapa.elements:
        if el.entity.etype == "link":
            continue;
        if el.entity.id:
            por_id[el.entity.id] = el;
        por_nome.setdefault(norm(el.entity.text), el);

    aceitas = [e for e in resultado.entidades if escolhas_entidade.get(e["chave"], {}).get("aceitar")];
    total = len(aceitas);
    caixas = {ENTRADA: origem};
    rel = {"novas": 0, "reusadas": 0, "vinculos": 0, "vinculos_reusados": 0, "refs": 0, "sem_subtipo": []};
    novas_idx = 0;
    raio = 220 + 30 * (total // 10);

    for e in aceitas:
        esc = escolhas_entidade[e["chave"]];
        reusar = esc.get("reusar");
        existente = None;
        if reusar and reusar.get("id") in por_id:
            existente = por_id[reusar["id"]];
        elif not reusar and norm(e["text_label"]) in por_nome:
            existente = por_nome[norm(e["text_label"])];
        if existente != None:
            caixa = existente;
            rel["reusadas"] += 1;
        else:
            ang = -math.pi / 2 + (2 * math.pi * novas_idx / max(total, 1));
            x = int(cx + raio * math.cos(ang)); y = int(cy + raio * math.sin(ang));
            novas_idx += 1;
            if reusar:
                d = _completar(reusar);
                caixa = mapa.addEntity(d["etype"] or e["etype"], x, y, text=d["text_label"], entity_id_=d["id"], wikipedia=d["wikipedia"]);
                from classlib.entity import Entity;
                caixa.entity = Entity.fromJson(d);
                rel["reusadas"] += 1;
            else:
                caixa = mapa.addEntity(esc.get("etype") or e["etype"], x, y, text=e["text_label"]);
                caixa.entity.full_description = e["description"];
                if e.get("small_label"):
                    caixa.entity.small_label = e["small_label"];
                rel["novas"] += 1;
                st = e.get("sub_etype");
                if st and caixa.entity.etype == "other":
                    if subtipos_validos != None and norm(st) in subtipos_validos and aplicar_subtipo != None:
                        try:
                            aplicar_subtipo(caixa, st);
                        except Exception:
                            rel["sem_subtipo"].append(st);
                    else:
                        rel["sem_subtipo"].append(st);
            if caixa.entity.id:
                por_id[caixa.entity.id] = caixa;
            por_nome.setdefault(norm(caixa.entity.text), caixa);
        caixas[e["chave"]] = caixa;
        rel["refs"] += _referenciar(caixa, e.get("referencias"));

    # vinculos ja desenhados: (id da caixa de, verbo, id da caixa para) -> caixa do link
    # (chave pelo objeto da CAIXA: entidades novas ainda nao tem entity.id; as pontas do link
    # guardam a propria caixa em LinkEntity.entity)
    ja = {};
    for el in mapa.elements:
        if el.entity.etype != "link":
            continue;
        for a in el.from_entity:
            for b in el.to_entity:
                ja[(id(a.entity), norm(el.entity.text), id(b.entity))] = el;

    for i, v in enumerate(resultado.vinculos):
        if i >= len(escolhas_vinculo) or not escolhas_vinculo[i]:
            continue;
        de, para = caixas.get(v["de"]), caixas.get(v["para"]);
        if de == None or para == None:
            continue;   # ponta nao aceita: sem ponta nao ha vinculo
        chave = (id(de), norm(v["verbo"]), id(para));
        if chave in ja:
            rel["refs"] += _referenciar(ja[chave], v.get("referencias"));
            rel["vinculos_reusados"] += 1;
            continue;
        mx = int((de.x + para.x) / 2); my = int((de.y + para.y) / 2) + 40;
        link = mapa.addEntity("link", mx, my, text=v["verbo"]);
        link.addFrom(de, v.get("start_date"), v.get("end_date"));
        link.addTo(para, v.get("start_date"), v.get("end_date"));
        rel["refs"] += _referenciar(link, v.get("referencias"));
        ja[chave] = link;
        rel["vinculos"] += 1;
    return rel;
