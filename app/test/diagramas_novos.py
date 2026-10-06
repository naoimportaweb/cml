#!/usr/bin/env python3
# Os dois diagramas que o New monta A PARTIR DO BANCO: Estrela (SPEC.md §4) e Regional (§5).
#
# Os outros documentos nascem vazios. Estes dois nao: o analista escolhe entidade(s) na busca e
# o servidor devolve o que se liga a elas (Entity.neighborhood). O que este teste cobra e a
# MONTAGEM -- o que o cliente faz com a resposta --, com o servidor trocado por uma resposta
# fixa. A consulta em si so se testa contra banco; o que da para prender aqui e que a resposta
# vira um mapa correto.
#
# O teste passa pela BUSCA de verdade (DialogEntityFind trocado, devolvendo o mesmo tipo que ele
# devolve: um objeto Entity, nao o dicionario da consulta). Alimentar o campo a mao escondia
# justamente o defeito que havia ali -- o codigo lia .get("text_label") de um objeto Entity.
#
#   QT_QPA_PLATFORM=offscreen python3 app/test/diagramas_novos.py

import os, sys, inspect, tempfile;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(CURRENTDIR);
sys.path.append(ROOT);

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen");
os.environ["HOME"] = tempfile.mkdtemp(prefix="cml_diagnovos_");

from PySide6.QtWidgets import QApplication;

FALHAS = [];


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def encavalados(mapa):
    """Pares de elementos cujos retangulos se cruzam. Os dois layouts prometem AUSENCIA de
    colisao, e a promessa so vale depois de medir: mapa criado do banco nunca foi desenhado, e
    com w/h em None o algoritmo mediria folga pela largura de reserva, nao pelos nomes de
    verdade. O vinculo entra na briga -- a caixinha do verbo e desenho como as outras."""
    saida = [];
    itens = [e for e in mapa.elements if e.w and e.h];
    for i in range(len(itens)):
        for j in range(i + 1, len(itens)):
            a, b = itens[i], itens[j];
            if (a.x < b.x + b.w and b.x < a.x + a.w and
                a.y < b.y + b.h and b.y < a.y + a.h):
                saida.append((str(a.entity.text), str(b.entity.text)));
    return saida;


def entidade(ident, nome, etype="person", nivel=1, subtipo=None, face=None):
    return {"id": ident, "text_label": nome, "etype": etype, "nivel": nivel,
            "description": "", "wikipedia": None, "default_url": None, "data_extra": "",
            "references": [], "classification": [], "images": [], "face": face,
            "small_label": None, "start_date": None, "end_date": None,
            "format_date": "yyyy-MM-dd", "sub_etype_id": None, "sub_etype_name": subtipo,
            "subtype_face": None, "icon": None};


BANDEIRA = "iVBORw0KGgo=";

# --- resposta para a estrela: a construtora e quem gira em volta dela -------------------------
ESTRELA = {
    "entidades": [
        entidade("c", "Construtora X", "organization", 0),
        entidade("p1", "Zeca Silva", "person", 1),
        entidade("p2", "Ana Souza", "person", 1),
        entidade("p3", "Bruno Lima", "person", 1),
        entidade("o1", "Contrato 44", "other", 2),
    ],
    "vinculos": [
        {"de": "p1", "para": "c", "verbo": "dirige"},
        {"de": "p2", "para": "c", "verbo": "dirige"},
        {"de": "p3", "para": "c", "verbo": ""},             # associação do MISP: vem sem verbo
        {"de": "p1", "para": "o1", "verbo": "assina"},
        {"de": "p1", "para": "FANTASMA", "verbo": "cita"},  # ponta cortada pelo teto
    ],
    "cortados": 7,
};

# --- resposta para o regional: dois países, e UMA pessoa que toca os dois --------------------
REGIONAL = {
    "br": {"entidades": [entidade("br", "Brasil", "other", 0, subtipo="country", face=BANDEIRA),
                         entidade("z", "Zeca", "person", 1),
                         entidade("ponte", "Ana", "person", 1)],
           "vinculos": [{"de": "z", "para": "br", "verbo": "atua em"},
                        {"de": "ponte", "para": "br", "verbo": "atua em"}],
           "cortados": 2},
    "pa": {"entidades": [entidade("pa", "Panamá", "other", 0, subtipo="country", face=BANDEIRA),
                         entidade("ponte", "Ana", "person", 1),          # a MESMA Ana
                         entidade("off", "Offshore Y", "organization", 1)],
           "vinculos": [{"de": "ponte", "para": "pa", "verbo": "atua em"},
                        {"de": "off", "para": "pa", "verbo": "sediada em"},
                        # o mesmo vínculo que o Brasil já trouxe: não pode virar dois
                        {"de": "ponte", "para": "br", "verbo": "atua em"}],
           "cortados": 3},
};


def main():
    app = QApplication(sys.argv);
    from view.ui import estilo;
    estilo.aplicar(app);

    from classlib.entity import Entity;
    from classlib.relationship.maprelationship import MapRelationship;
    from classlib.relationship import regional as paises_;
    import view.dialog_entity_find as busca;
    import view.dialog_diagram_choice as escolha;

    # O create/exists do mapa fala com o servidor, e não é isso que está em teste.
    MapRelationship.exists = lambda self, nome: False;
    MapRelationship.create = lambda self: True;
    escolha.QMessageBox.information = staticmethod(lambda *a, **k: None);

    # A busca, trocada por uma que devolve o que a de verdade devolve: Entity.fromJson(linha).
    escolhida = {"valor": None};
    class BuscaFalsa:
        def __init__(self, pai):
            self.entity = escolhida["valor"];
        def exec(self):
            return 1;
    busca.DialogEntityFind = BuscaFalsa;
    sys.modules["view.dialog_entity_find"].DialogEntityFind = BuscaFalsa;

    print("Entity.fromJson carrega subtipo e rosto, não só o nome");
    pais = Entity.fromJson( entidade("br", "Brasil", "other", 0, subtipo="country", face=BANDEIRA) );
    confere(pais.sub_etype_name == "country", "o sub-tipo sobrevive ao fromJson");
    confere(pais.face == BANDEIRA, "e o rosto também");
    confere(paises_.eh_pais_entidade(pais), "por isso o regional reconhece o país");
    com_data = Entity.fromJson( dict(entidade("x", "X"), start_date="2020-01-01", end_date="2021-02-03") );
    confere(com_data.start_date == "2020-01-01" and com_data.end_date == "2021-02-03",
            "as datas da entidade também (regra do CLAUDE.md: toda ponta de data sobrevive ao load)");

    #-------------------------------------------------------------------- ESTRELA
    print("\nESTRELA: a busca entrega um Entity, e o painel o aceita");
    Entity.neighborhood = staticmethod(
        lambda eid, niveis=1, limite=60, rosto=False: (ESTRELA["entidades"], ESTRELA["vinculos"], ESTRELA["cortados"]));
    janela = escolha.DialogDiagramChoice(None);
    escolhida["valor"] = Entity.fromJson( entidade("c", "Construtora X", "organization", 0) );
    janela.btn_estrela_buscar_click();
    confere("Construtora X" in janela.lbl_estrela_entidade.text(),
            "o nome aparece na tela: %s" % janela.lbl_estrela_entidade.text());
    confere(janela.txt_estrela_name.text() == "Estrela - Construtora X", "nome do diagrama sugerido");
    confere(janela.txt_estrela_key.text() == "Construtora X", "keyword sugerida");

    janela.spin_estrela_niveis.setValue(2);
    janela.btn_new_estrela_click();
    mapa = janela.map;
    confere(mapa != None, "o diagrama foi criado");
    if mapa == None:
        print("\nFALHAS: %d" % len(FALHAS));
        return 1;
    confere(mapa.__class__.__name__ == "MapRelationship",
            "é um MapRelationship comum (salva, reabre e exporta como os outros)");

    caixas = [e for e in mapa.elements if e.entity.etype != "link"];
    confere(sorted(c.entity.id for c in caixas) == ["c", "o1", "p1", "p2", "p3"],
            "5 caixas, com os ids do banco (buscar antes de criar)");
    confere(sorted(set(c.entity.etype for c in caixas)) == ["organization", "other", "person"],
            "tipos preservados");

    vinculos = [e for e in mapa.elements if e.entity.etype == "link"];
    confere(len(vinculos) == 4, "4 vínculos: o de ponta inexistente não entrou (%d)" % len(vinculos));
    confere("associado a" in [v.entity.text for v in vinculos],
            "associação do MISP, que vem sem verbo, ganhou rótulo honesto");
    confere("cita" not in [v.entity.text for v in vinculos], "e o de ponta cortada ficou de fora");
    for vinculo in vinculos:
        pontas = [p.entity for p in list(vinculo.to_entity) + list(vinculo.from_entity)];
        confere(len(pontas) == 2 and all(p in caixas for p in pontas),
                "o vínculo '%s' tem as duas pontas no mapa" % vinculo.entity.text);

    print("\n  desenhado em estrela, com a entidade escolhida no centro");
    def meio(caixa):
        return (caixa.x + (caixa.w or 0) / 2.0, caixa.y + (caixa.h or 0) / 2.0);
    def distancia(a, b):
        ax, ay = meio(a); bx, by = meio(b);
        return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5;
    centro = [c for c in caixas if c.entity.id == "c"][0];
    raios = [distancia(c, centro) for c in caixas if c.entity.id in ("p1", "p2", "p3")];
    confere(max(raios) - min(raios) < 2, "os três do nível 1 à mesma distância do centro");
    confere(distancia([c for c in caixas if c.entity.id == "o1"][0], centro) > max(raios),
            "e o do nível 2 mais longe");
    confere(all(c.x >= 0 and c.y >= 0 for c in mapa.elements), "tudo em coordenada positiva");
    confere(all(c.w and c.h for c in mapa.elements),
            "as caixas foram MEDIDAS antes do layout (mapa novo nunca foi desenhado)");
    choques = encavalados(mapa);
    confere(len(choques) == 0, "nada encavalado, verbos incluídos: %s" % choques[:3]);

    print("\n  recusas da estrela");
    outra = escolha.DialogDiagramChoice(None);
    outra.btn_new_estrela_click();
    confere("centro" in outra.lbl_message.text(), "sem entidade: %s" % outra.lbl_message.text());
    escolhida["valor"] = Entity.fromJson( entidade("c", "X", "person", 0) );
    outra.btn_estrela_buscar_click();
    outra.txt_estrela_name.setText(""); outra.txt_estrela_key.setText("");
    outra.btn_new_estrela_click();
    confere("name" in outra.lbl_message.text().lower(), "sem nome: %s" % outra.lbl_message.text());

    print("\n  servidor sem o método novo (antes do deploy) é dito, não silenciado");
    Entity.neighborhood = staticmethod(
        lambda eid, niveis=1, limite=60, rosto=False: (None, None, "O servidor não respondeu a Entity.neighborhood (falta o deploy?)."));
    terceira = escolha.DialogDiagramChoice(None);
    escolhida["valor"] = Entity.fromJson( entidade("c", "X", "person", 0) );
    terceira.btn_estrela_buscar_click();
    terceira.btn_new_estrela_click();
    confere("deploy" in terceira.lbl_message.text(), "a mensagem explica: %s" % terceira.lbl_message.text());
    confere(terceira.map == None, "e nenhum diagrama meia-boca foi criado");

    #-------------------------------------------------------------------- REGIONAL
    print("\nREGIONAL: vários países, uma consulta por país");
    pedidos = [];
    def vizinhanca_regional(eid, niveis=1, limite=60, rosto=False):
        pedidos.append((eid, rosto));
        bloco = REGIONAL[eid];
        return (bloco["entidades"], bloco["vinculos"], bloco["cortados"]);
    Entity.neighborhood = staticmethod(vizinhanca_regional);

    reg = escolha.DialogDiagramChoice(None);
    escolhida["valor"] = Entity.fromJson( entidade("br", "Brasil", "other", 0, subtipo="country", face=BANDEIRA) );
    reg.btn_regional_add_click();
    confere(reg.lbl_regional_aviso.text() == "", "país com sub-tipo não gera aviso");
    escolhida["valor"] = Entity.fromJson( entidade("pa", "Panamá", "other", 0, subtipo="country", face=BANDEIRA) );
    reg.btn_regional_add_click();
    confere(reg.lst_regional.count() == 2, "dois países na lista");
    reg.btn_regional_add_click();
    confere(reg.lst_regional.count() == 2, "o mesmo país duas vezes não acrescenta nada");

    reg.btn_new_regional_click();
    mapa = reg.map;
    confere(mapa != None, "o mapa regional foi criado");
    if mapa == None:
        print("\nFALHAS: %d" % len(FALHAS));
        return 1;
    confere(sorted(p[0] for p in pedidos) == ["br", "pa"], "uma consulta por país: %s" % pedidos);
    confere(all(p[1] for p in pedidos), "e pedindo o rosto (a bandeira é o desenho)");
    confere(mapa.show_face, "o mapa nasce com “exibir rosto” ligado");

    caixas = [e for e in mapa.elements if e.entity.etype != "link"];
    confere(sorted(c.entity.id for c in caixas) == ["br", "off", "pa", "ponte", "z"],
            "a Ana, que os dois países trouxeram, é UMA caixa só: %s" % sorted(c.entity.id for c in caixas));
    vinculos = [e for e in mapa.elements if e.entity.etype == "link"];
    confere(len(vinculos) == 4, "4 vínculos: o repetido entre os dois países não dobrou (%d)" % len(vinculos));
    bandeira = [c for c in caixas if c.entity.id == "br"][0];
    confere(bandeira.entity.face == BANDEIRA, "a bandeira chegou à caixa do país");

    print("\n  um grupo por país, e a ponte fora dos dois");
    br = [c for c in caixas if c.entity.id == "br"][0];
    pa = [c for c in caixas if c.entity.id == "pa"][0];
    zeca = [c for c in caixas if c.entity.id == "z"][0];
    off = [c for c in caixas if c.entity.id == "off"][0];
    ponte = [c for c in caixas if c.entity.id == "ponte"][0];
    confere(distancia(zeca, br) < distancia(zeca, pa), "Zeca, só do Brasil, fica no grupo do Brasil");
    confere(distancia(off, pa) < distancia(off, br), "Offshore Y, só do Panamá, no grupo do Panamá");
    confere(ponte.y > max(br.y, pa.y),
            "a Ana, que toca os dois, vai para a faixa de baixo e não se esconde num grupo");
    confere(all(c.x >= 0 and c.y >= 0 for c in mapa.elements), "tudo em coordenada positiva");
    confere(all(c.w and c.h for c in mapa.elements), "as caixas foram medidas antes do layout");
    choques = encavalados(mapa);
    confere(len(choques) == 0, "nada encavalado, verbos incluídos: %s" % choques[:3]);

    print("\n  o layout regional também atende o mapa que já existe");
    from classlib.relationship import layouts;
    confere("regional" in dict(layouts.LAYOUTS), "aparece no menu Layout");
    sem_pais = MapRelationship();
    sem_pais.addEntity("person", 0, 0, text="Alguém");
    sem_pais.addEntity("person", 0, 0, text="Outro");
    confere(layouts.aplicar(sem_pais, "regional") == 2,
            "mapa sem país nenhum não quebra: cai no espalhar, que é dizer a verdade");

    print("\n  avisa quando a entidade escolhida não tem o sub-tipo country");
    quarta = escolha.DialogDiagramChoice(None);
    escolhida["valor"] = Entity.fromJson( entidade("br", "Brasil", "other", 0) );   # sem sub-tipo
    quarta.btn_regional_add_click();
    confere("sub-tipo" in quarta.lbl_regional_aviso.text(),
            "o aviso aparece: %s" % quarta.lbl_regional_aviso.text()[:60]);

    print("\n  recusas do regional");
    quinta = escolha.DialogDiagramChoice(None);
    quinta.btn_new_regional_click();
    confere("país" in quinta.lbl_message.text(), "sem país: %s" % quinta.lbl_message.text());

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
