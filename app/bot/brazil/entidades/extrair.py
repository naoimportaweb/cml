"""Bot: extrai sujeitos e vínculos de uma URL usando o rolhama.

Canal proprio (cml/entidades -> 508), separado do report (cml -> 507): o alocar e
idempotente POR PROJETO, entao pedir como "cml" devolveria o mesmo 507 e um report rodando
junto colidiria — um leria a resposta do outro.

O bot NAO escreve direto no mapa. Um qwen2.5:14b em CPU erra classificacao: nos testes
"Claude for Chrome" saiu ora como organization ora como other, e "Researchers" apareceu
como se fosse um sujeito. Entao ele PROPOE, com tipo editavel, e so entra no mapa o que o
analista marcar.
"""

import os, sys, inspect, json, traceback;

from PySide6.QtCore import Qt, QObject, QThread, Signal, Slot;
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                               QComboBox, QMessageBox, QAbstractItemView, QCheckBox, QWidget);

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) );   # .../app
sys.path.append( ROOT );

from classlib.rolhama import Rolhama;
from classlib.report import _texto_da_pagina, MODELO;
from classlib.configuration import Configuration;

PROJETO_BOT = "cml/entidades";
TIPOS = ["person", "organization", "other"];
ROTULO = {"person": "Pessoa", "organization": "Organização", "other": "Outro"};

# O prompt curto e de proposito. No teste, a versao longa com regras detalhadas produziu
# JSON quebrado; a curta produziu valido. O format=json restringe o decoding, mas nao
# impede o modelo de se enrolar com instrucao comprida.
MAX_ARTIGO = 11000;


class _Extrator(QObject):
    progresso = Signal(str);
    terminou  = Signal(object);
    falhou    = Signal(str);

    def __init__(self, url):
        super().__init__();
        self.url = url;

    @Slot()
    def executar(self):
        try:
            self.progresso.emit("Lendo a página…");
            texto, erro = _texto_da_pagina(self.url);
            if texto == None:
                raise Exception("Não foi possível ler a página: " + str(erro));
            texto = texto[:MAX_ARTIGO];

            prompt = ('Extraia do artigo os sujeitos e as relações. tipo: person|organization|other.\n'
                      'Responda SOMENTE JSON: {"entidades":[{"nome":"","tipo":"","descricao":""}],'
                      '"vinculos":[{"origem":"","relacao":"","destino":""}]}\n\nARTIGO:\n' + texto);

            r = Rolhama(projeto=PROJETO_BOT);
            canal = r.alocar(uso="Extrair entidades e vínculos de uma URL");
            self.progresso.emit("Extraindo no rolhama (canal %d, %s) — leva minutos…" % (canal, MODELO));
            saida = r.gerar(prompt, model=MODELO, formato="json", espera_total=900);

            try:
                js = json.loads(saida);
            except Exception:
                raise Exception("O modelo não devolveu JSON válido. Tente de novo — a saída varia.");
            self.terminou.emit({"entidades": js.get("entidades") or [],
                                "vinculos": js.get("vinculos") or [],
                                "canal": canal});
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
        self.worker = _Extrator(url);
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
            x, y = 40, 40;
            for i in range(self.tab_ent.rowCount()):
                if not self.checks_ent[i].isChecked():
                    continue;
                nome = self.tab_ent.item(i, 1).text().strip();
                if nome == "":
                    continue;
                tipo = self.combos_ent[i].currentData();
                desc = self.tab_ent.item(i, 3).text().strip();
                caixa = self.mapa.addEntity(tipo, x, y, text=nome);
                caixa.entity.full_description = desc;
                criadas[nome.lower()] = caixa;
                x = x + 260;
                if x > 1000: x = 40; y = y + 120;

            n_vin = 0;
            yv = y + 140;
            for i in range(self.tab_vin.rowCount()):
                if not self.checks_vin[i].isChecked():
                    continue;
                o = self.tab_vin.item(i, 1).text().strip().lower();
                d = self.tab_vin.item(i, 3).text().strip().lower();
                rel = self.tab_vin.item(i, 2).text().strip();
                # So liga o que existe: o modelo cita nomes que nao estao em "entidades",
                # ou que o analista desmarcou. Criar a caixa por conta propria traria de
                # volta justamente o que ele recusou.
                if o not in criadas or d not in criadas or rel == "":
                    continue;
                link = self.mapa.addEntity("link", 40 + (n_vin * 300), yv, text=rel);
                link.addFrom( criadas[o] );
                link.addTo( criadas[d] );
                n_vin = n_vin + 1;

            self.__msg__("Adicionados ao mapa: %d sujeito(s) e %d vínculo(s).\n\n"
                         "Eles entraram numa grade; arraste para posicionar. "
                         "Salve o mapa para gravar." % (len(criadas), n_vin));
            self.accept();
        except Exception as e:
            traceback.print_exc();
            self.__msg__("Falha ao adicionar: " + str(e));
