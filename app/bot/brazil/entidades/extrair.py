"""Bot: extrai sujeitos e vínculos de uma URL usando o rolhama.

Canal proprio (cml/entidades -> 510), separado do report (cml -> 507): o worker serializa
global, mas dois projetos no MESMO canal decifrariam a resposta um do outro (mesma chave).
Canal por projeto e o que mantem report e bot isolados. (No webapi o canal e fixo/semeado;
o r.alocar() aqui so devolve o canal do projeto, sem ida ao servidor. 507/510 sao os canais
LLM livres — 508=WHISPER, 509=EMBED.)

O bot NAO escreve direto no mapa. Um qwen2.5:14b em CPU erra classificacao: nos testes
"Claude for Chrome" saiu ora como organization ora como other, e "Researchers" apareceu
como se fosse um sujeito. Entao ele PROPOE, com tipo editavel, e so entra no mapa o que o
analista marcar.
"""

import os, sys, inspect, json, traceback, re, unicodedata;

from PySide6.QtCore import Qt, QObject, QThread, Signal, Slot;
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                               QComboBox, QMessageBox, QAbstractItemView, QCheckBox, QWidget);

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) );   # .../app
sys.path.append( ROOT );

from classlib.rolhama import Rolhama;
from classlib.report import ler_pagina, MODELO, idioma_frase, instrucao_idioma;
from classlib.configuration import Configuration;

PROJETO_BOT = "cml/entidades";
TIPOS = ["person", "organization", "other"];
ROTULO = {"person": "Pessoa", "organization": "Organização", "other": "Outro"};

# O prompt curto e de proposito. No teste, a versao longa com regras detalhadas produziu
# JSON quebrado; a curta produziu valido. O format=json restringe o decoding, mas nao
# impede o modelo de se enrolar com instrucao comprida.
MAX_ARTIGO = 11000;


def _norm(s):
    # minusculas, sem acento e sem pontuacao: "OpenAI, Inc." e "openai inc" viram a mesma
    # coisa. E o denominador comum para casar a ponta de um vinculo com o nome da entidade.
    s = unicodedata.normalize("NFD", str(s or ""));
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower();
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip();

def _tokens(s):
    return [t for t in _norm(s).split(" ") if t];


class _Extrator(QObject):
    progresso = Signal(str);
    terminou  = Signal(object);
    falhou    = Signal(str);

    def __init__(self, url, idioma_codigo):
        super().__init__();
        self.url = url;
        self.idioma_codigo = idioma_codigo;          # codigo do idioma do mapa (en/pt-BR/es)
        self.idioma = idioma_frase(idioma_codigo);   # frase, para o texto do prompt

    @Slot()
    def executar(self):
        try:
            self.progresso.emit("Lendo a página…");
            # Titulo e descricao saem da propria pagina, na mesma requisicao do texto: sao o
            # que a referencia de origem precisa alem do link, e o rolhama nao e pedido para
            # isso (o modelo erra citacao e nao ve o <title>/<meta>).
            texto, titulo, descricao, erro = ler_pagina(self.url);
            if texto == None:
                raise Exception("Não foi possível ler a página: " + str(erro));
            texto = texto[:MAX_ARTIGO];

            prompt = ('Extraia do artigo os sujeitos e as relações. tipo: person|organization|other.\n'
                      'Escreva "descricao" e "relacao" em ' + self.idioma + '.\n'
                      'Responda SOMENTE JSON: {"entidades":[{"nome":"","tipo":"","descricao":""}],'
                      '"vinculos":[{"origem":"","relacao":"","destino":""}]}\n\nARTIGO:\n' + texto);

            r = Rolhama(projeto=PROJETO_BOT);
            canal = r.alocar(uso="Extrair entidades e vínculos de uma URL");
            self.progresso.emit("Extraindo no rolhama (canal %d, %s) — leva minutos…" % (canal, MODELO));
            saida = r.gerar(prompt, model=MODELO, formato="json", espera_total=900,
                            idioma_instrucao=instrucao_idioma(self.idioma_codigo));

            try:
                js = json.loads(saida);
            except Exception:
                raise Exception("O modelo não devolveu JSON válido. Tente de novo — a saída varia.");
            self.terminou.emit({"entidades": js.get("entidades") or [],
                                "vinculos": js.get("vinculos") or [],
                                "canal": canal,
                                "url": self.url, "url_titulo": titulo, "url_descricao": descricao});
        except Exception as e:
            traceback.print_exc();
            self.falhou.emit(str(e));


class DialogExtrairEntidades(QDialog):
    def __init__(self, form, mapa):
        super().__init__(form);
        self.mapa = mapa;
        self.resize(920, 560);
        self.setWindowTitle("Extrair de URL — " + str(mapa.getName()));
        self.setFont( Configuration.instancia().getFont() );
        self.thread = None;
        self.worker = None;
        self.dados = None;

        principal = QVBoxLayout();
        self.setLayout( principal );

        linha = QHBoxLayout();
        linha.addWidget( QLabel("URL:") );
        self.txt_url = QLineEdit();
        self.txt_url.setPlaceholderText("https://…");
        linha.addWidget( self.txt_url );
        self.btn_extrair = QPushButton("Extrair");
        self.btn_extrair.clicked.connect(self.btn_extrair_click);
        linha.addWidget( self.btn_extrair );
        principal.addLayout( linha );

        self.lbl = QLabel("O modelo lê a página e propõe os sujeitos. Nada entra no mapa sem você marcar.");
        self.lbl.setStyleSheet("color: #666;");
        principal.addWidget( self.lbl );

        principal.addWidget( QLabel("Entidades:") );
        self.tab_ent = QTableWidget(0, 4);
        self.tab_ent.setHorizontalHeaderLabels(["", "Nome", "Tipo", "Descrição"]);
        self.tab_ent.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch);
        self.tab_ent.setColumnWidth(0, 30);
        self.tab_ent.setColumnWidth(1, 220);
        self.tab_ent.setColumnWidth(2, 130);
        principal.addWidget( self.tab_ent );

        principal.addWidget( QLabel("Vínculos:") );
        self.tab_vin = QTableWidget(0, 4);
        self.tab_vin.setHorizontalHeaderLabels(["", "Origem", "Relação", "Destino"]);
        self.tab_vin.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch);
        self.tab_vin.setColumnWidth(0, 30);
        self.tab_vin.setColumnWidth(1, 220);
        self.tab_vin.setColumnWidth(2, 160);
        principal.addWidget( self.tab_vin );

        botoes = QHBoxLayout();
        self.btn_add = QPushButton("Adicionar ao mapa");
        self.btn_add.setEnabled(False);
        self.btn_add.clicked.connect(self.btn_add_click);
        botoes.addWidget( self.btn_add );
        botoes.addStretch();
        principal.addLayout( botoes );

    def __msg__(self, t):
        b = QMessageBox(self); b.setText(str(t)); b.exec();

    def __check__(self, marcado=True):
        # QCheckBox centralizado numa celula: a coluna 0 e so a marca, sem texto.
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setAlignment(Qt.AlignCenter);
        c = QCheckBox(); c.setChecked(marcado); l.addWidget(c);
        return w, c;

    def btn_extrair_click(self):
        url = self.txt_url.text().strip();
        if not url.lower().startswith("http://") and not url.lower().startswith("https://"):
            self.__msg__("Informe uma URL http:// ou https://.");
            return;
        if self.thread != None and self.thread.isRunning():
            return;

        self.btn_extrair.setEnabled(False);
        self.btn_add.setEnabled(False);
        self.thread = QThread();
        self.worker = _Extrator(url, getattr(self.mapa, "language", None));
        self.worker.moveToThread(self.thread);
        self.thread.started.connect(self.worker.executar);
        self.worker.progresso.connect(lambda m: self.lbl.setText("⏳ " + m));
        self.worker.terminou.connect(self.__pronto__);
        self.worker.falhou.connect(self.__falhou__);
        self.thread.start();

    def __encerrar__(self):
        if self.thread != None:
            self.thread.quit(); self.thread.wait();
        self.thread = None; self.worker = None;
        self.btn_extrair.setEnabled(True);

    @Slot(object)
    def __pronto__(self, dados):
        self.__encerrar__();
        self.dados = dados;
        self.__preencher__(dados);
        n = len(dados["entidades"]); v = len(dados["vinculos"]);
        self.lbl.setText("%d sujeito(s) e %d vínculo(s) propostos (canal %d). Confira o tipo — o modelo erra." %
                         (n, v, dados["canal"]));
        self.btn_add.setEnabled(n > 0);

    @Slot(str)
    def __falhou__(self, msg):
        self.__encerrar__();
        self.lbl.setText("Falhou.");
        self.__msg__("Falha ao extrair:\n\n" + msg);

    def __preencher__(self, dados):
        self.tab_ent.setRowCount(0);
        self.checks_ent = [];
        self.combos_ent = [];
        for e in dados["entidades"]:
            i = self.tab_ent.rowCount(); self.tab_ent.insertRow(i);
            w, c = self.__check__(); self.tab_ent.setCellWidget(i, 0, w); self.checks_ent.append(c);
            self.tab_ent.setItem(i, 1, QTableWidgetItem( str(e.get("nome") or "") ));
            combo = QComboBox();
            for t in TIPOS: combo.addItem(ROTULO[t], t);
            tipo = str(e.get("tipo") or "other");
            combo.setCurrentIndex(TIPOS.index(tipo) if tipo in TIPOS else TIPOS.index("other"));
            self.tab_ent.setCellWidget(i, 2, combo); self.combos_ent.append(combo);
            self.tab_ent.setItem(i, 3, QTableWidgetItem( str(e.get("descricao") or "") ));

        self.tab_vin.setRowCount(0);
        self.checks_vin = [];
        for v in dados["vinculos"]:
            i = self.tab_vin.rowCount(); self.tab_vin.insertRow(i);
            w, c = self.__check__(); self.tab_vin.setCellWidget(i, 0, w); self.checks_vin.append(c);
            self.tab_vin.setItem(i, 1, QTableWidgetItem( str(v.get("origem") or "") ));
            self.tab_vin.setItem(i, 2, QTableWidgetItem( str(v.get("relacao") or "") ));
            self.tab_vin.setItem(i, 3, QTableWidgetItem( str(v.get("destino") or "") ));

    def btn_add_click(self):
        if self.dados == None:
            return;
        try:
            # Grade simples: o CML nao tem layout automatico, e sobrepor tudo na mesma
            # coordenada deixaria o mapa ilegivel. O analista arrasta depois.
            criadas = {};
            reusadas = 0;
            refs = 0;

            # A "referencia de insercao": todo objeto marcado — novo OU reaproveitado —
            # recebe uma referencia apontando para a URL de onde veio, com o titulo e a
            # descricao da PAGINA (vieram junto do texto em ler_pagina; nao sao pedidos ao
            # rolhama). Para o reaproveitado e uma referencia a mais no objeto que ja existia.
            url_ref  = str(self.dados.get("url") or "").strip();
            tit_ref  = str(self.dados.get("url_titulo") or "").strip() or url_ref;
            desc_ref = str(self.dados.get("url_descricao") or "").strip();

            def _referenciar(caixa):
                # Nao duplica: extrair a mesma URL duas vezes nao repete a referencia no
                # objeto. Compara por link1 normalizado.
                if url_ref == "":
                    return 0;
                for ref in caixa.entity.references:
                    if str(ref.link1 or "").strip() == url_ref:
                        return 0;
                caixa.addReference(tit_ref, url_ref, descricao=desc_ref);
                return 1;

            # O que JA esta no mapa, por nome. Sem isto, extrair um segundo artigo que cita
            # a mesma entidade cria uma caixa nova E uma entity_id nova no banco: viram dois
            # objetos distintos, cada um com suas referencias, e so o Entity.merge_to
            # conserta depois. Reusar aqui e o que impede o estrago.
            existentes = {};
            for el in self.mapa.elements:
                if el.entity.etype == "link":
                    continue;
                chave = str(el.entity.text or "").strip().lower();
                if chave != "":
                    existentes[chave] = el;

            x, y = 40, 40;
            for i in range(self.tab_ent.rowCount()):
                if not self.checks_ent[i].isChecked():
                    continue;
                nome = self.tab_ent.item(i, 1).text().strip();
                if nome == "":
                    continue;
                chave = nome.lower();

                if chave in existentes:
                    # Ja esta no mapa: aproveita a caixa. A descricao do artigo novo so
                    # entra se a entidade ainda nao tiver uma — sobrescrever apagaria o que
                    # o analista escreveu.
                    caixa = existentes[chave];
                    desc = self.tab_ent.item(i, 3).text().strip();
                    if desc != "" and not str(caixa.entity.full_description or "").strip():
                        caixa.entity.full_description = desc;
                    refs = refs + _referenciar(caixa);   # abre o objeto existente e anexa a URL
                    criadas[chave] = caixa;
                    reusadas = reusadas + 1;
                    continue;

                tipo = self.combos_ent[i].currentData();
                desc = self.tab_ent.item(i, 3).text().strip();
                caixa = self.mapa.addEntity(tipo, x, y, text=nome);
                caixa.entity.full_description = desc;
                refs = refs + _referenciar(caixa);
                criadas[chave] = caixa;
                existentes[chave] = caixa;
                x = x + 260;
                if x > 1000: x = 40; y = y + 120;

            # Vinculos que o mapa ja tem, indexados por (origem, relacao, destino) em
            # minusculas -> a CAIXA do link (nao so a chave): guardar a caixa e o que permite
            # abrir um vinculo reaproveitado e anexar tambem NELE a referencia da URL. O
            # vinculo (etype "link") tambem e uma entity com references.
            vinc_existentes = {};
            for el in self.mapa.elements:
                if el.entity.etype != "link":
                    continue;
                rel_atual = str(el.entity.text or "").strip().lower();
                for a in el.from_entity:
                    for b in el.to_entity:
                        vinc_existentes[( str(a.entity.getText() or "").strip().lower(),
                                          rel_atual,
                                          str(b.entity.getText() or "").strip().lower() )] = el;

            # Indice das pontas por nome normalizado. O problema real: o modelo NAO restringe
            # a ponta do vinculo a lista de entidades — ele escreve "cameras IP" na ponta sem
            # nunca ter listado "cameras IP" como entidade. Casar so por nome derrubava esse
            # vinculo (o mapa ficava so com as caixas das 3 entidades). Aqui, marcar o vinculo
            # VALE como aprovar os nos dele: (1) resolve a ponta por igualdade sem acento/
            # pontuacao ou por conjunto de tokens contido (nome unico) — reaproveita a entidade
            # existente; (2) se ainda assim nao existir, CRIA a ponta como 'other' e liga. O no
            # criado entra no indice, entao "cameras IP vulneraveis" reaproveita "cameras IP".
            existentes_por_norm = {};   # nome normalizado -> caixa
            for chave, caixa in existentes.items():
                existentes_por_norm.setdefault( _norm(chave), caixa );

            def _resolver_ponta(nome):
                n = _norm(nome);
                if n in existentes_por_norm:
                    return existentes_por_norm[n];
                tn = set(_tokens(nome));
                if not tn:
                    return None;
                cand = [];
                for nm, caixa in existentes_por_norm.items():
                    ts = set(nm.split(" ")) if nm else set();
                    if not ts:
                        continue;
                    menor = tn if len(tn) <= len(ts) else ts;
                    # subconjunto e ao menos um token "de peso" (>=3): evita casar so por "us",
                    # "ai" e afins, que apareceriam em varios nomes.
                    if (tn <= ts or ts <= tn) and any(len(t) >= 3 for t in menor):
                        cand.append(caixa);
                if len(cand) == 1:
                    return cand[0];
                return None;   # ausente ou ambiguo -> quem chama decide criar

            # Grade para as pontas que precisarem ser criadas (band proprio, acima dos links).
            xp = 40; yp = y + 140;
            pontas_criadas = [];
            def _obter_ou_criar_ponta(nome):
                nonlocal xp, yp;
                cx = _resolver_ponta(nome);
                if cx != None:
                    return cx;
                if nome == "":
                    return None;
                # Ponta citada no vinculo mas ausente da lista de entidades: cria como 'other'.
                # 'other' e o tipo neutro (pode ser coisa, sistema, alvo — "cameras IP"), e o
                # analista troca depois se for pessoa/organizacao.
                nova = self.mapa.addEntity("other", xp, yp, text=nome);
                _referenciar(nova);   # tambem recebe a referencia de origem
                chave = nome.lower();
                existentes[chave] = nova;
                existentes_por_norm.setdefault( _norm(nome), nova );
                pontas_criadas.append(nome);
                xp = xp + 260;
                if xp > 1000: xp = 40; yp = yp + 120;
                return nova;

            n_vin = 0; vin_reusados = 0;
            yv = yp + 200;
            for i in range(self.tab_vin.rowCount()):
                if not self.checks_vin[i].isChecked():
                    continue;
                nome_o = self.tab_vin.item(i, 1).text().strip();
                nome_d = self.tab_vin.item(i, 3).text().strip();
                rel = self.tab_vin.item(i, 2).text().strip();
                if rel == "":
                    continue;
                cx_o = _obter_ou_criar_ponta(nome_o);
                cx_d = _obter_ou_criar_ponta(nome_d);
                if cx_o == None or cx_d == None:
                    # So cai aqui se o nome da ponta veio vazio — nada a ligar.
                    continue;
                chave_vin = ( str(cx_o.entity.getText() or "").strip().lower(),
                              rel.lower(),
                              str(cx_d.entity.getText() or "").strip().lower() );
                if chave_vin in vinc_existentes:
                    # Vinculo ja existe: abre e anexa tambem nele a referencia da URL.
                    refs = refs + _referenciar( vinc_existentes[chave_vin] );
                    vin_reusados = vin_reusados + 1;
                    continue;
                link = self.mapa.addEntity("link", 40 + (n_vin * 300), yv, text=rel);
                link.addFrom( cx_o );
                link.addTo( cx_d );
                refs = refs + _referenciar(link);   # o vinculo novo tambem recebe a URL
                vinc_existentes[chave_vin] = link;
                n_vin = n_vin + 1;

            novas = len(criadas) - reusadas;
            msg = "Adicionados ao mapa: %d sujeito(s) novo(s) e %d vínculo(s) novo(s)." % (novas, n_vin);
            if pontas_criadas:
                # Transparencia: o analista precisa saber que apareceram nos que ele nao marcou
                # na tabela de entidades — vieram das pontas dos vinculos que ele marcou.
                msg = msg + ("\n\nCriei %d nó(s) 'other' que o modelo citou como ponta de vínculo "
                             "mas não listou como entidade (troque o tipo se precisar):\n  - %s" %
                             (len(pontas_criadas), "\n  - ".join(pontas_criadas)));
            if reusadas or vin_reusados:
                msg = msg + ("\n\nJá existiam no mapa e foram reaproveitados: %d sujeito(s) e "
                             "%d vínculo(s) — não foram duplicados." % (reusadas, vin_reusados));
            if refs:
                msg = msg + ("\n\nReferência de origem (a URL, com título e descrição da página) "
                             "anexada a %d item(ns) — objetos e vínculos." % refs);
            msg = msg + "\n\nOs novos entraram numa grade; arraste para posicionar. Salve o mapa para gravar.";
            self.__msg__(msg);
            self.accept();
        except Exception as e:
            traceback.print_exc();
            self.__msg__("Falha ao adicionar: " + str(e));
