"""Bot: procura referências para uma entidade.

Confianca por procedencia, e nao por fonte "boa" ou "ruim":

- CONFIAVEL: o que ja esta na SUA base. Se a entidade existe em outro mapa deste domain,
  as referencias dela foram curadas por um analista — sao dado seu. De quebra isso revela
  entidade duplicada, que e o caso que o Entity.merge_to existe para resolver.

- NAO CONFIAVEL: o que veio da web (Wikipedia e DuckDuckGo). Nada entra sem alguem ler.
  Clicar na linha baixa o texto e mostra ao lado; so entao aprova.

Sem LLM aqui de proposito: o ollama da 90 nao tem acesso a internet, entao pedir
referencias a ele produziria URLs inventadas — o pior resultado possivel numa ferramenta
de inteligencia.
"""

import os, sys, inspect, re, json, html, traceback;

from PySide6.QtCore import Qt, QObject, QThread, Signal, Slot;
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
                               QMessageBox, QAbstractItemView, QCheckBox, QWidget, QSplitter);

import requests;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) );   # .../app
sys.path.append( ROOT );

from classlib.configuration import Configuration;
from classlib.entity import Entity;
from classlib.report import _texto_da_pagina;

TIMEOUT = 20;
UA = "Mozilla/5.0 (compatible; CML/1.0)";
MAX_WEB = 8;


def _wikipedia(nome):
    """API oficial de busca. Livre, sem chave."""
    achados = [];
    try:
        r = requests.get("https://en.wikipedia.org/w/api.php",
                         params={"action": "query", "list": "search", "srsearch": nome,
                                 "format": "json", "srlimit": 3},
                         timeout=TIMEOUT, headers={"User-Agent": UA});
        for it in (r.json().get("query", {}).get("search") or []):
            t = it.get("title") or "";
            achados.append({
                "titulo": t,
                "link": "https://en.wikipedia.org/wiki/" + t.replace(" ", "_"),
                "fonte": "Wikipedia",
                "descricao": re.sub(r"<[^>]+>", "", html.unescape(it.get("snippet") or "")),
            });
    except Exception as e:
        achados.append({"titulo": "(Wikipedia falhou: " + type(e).__name__ + ")", "link": "",
                        "fonte": "Wikipedia", "descricao": ""});
    return achados;


def _duckduckgo(nome):
    """HTML do DDG. Sem chave, mas e scraping: se o layout mudar, para de achar — dai a
    lista vir vazia em vez de estourar."""
    achados = [];
    try:
        r = requests.post("https://html.duckduckgo.com/html/", data={"q": nome},
                          timeout=TIMEOUT, headers={"User-Agent": UA});
        pares = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.S);
        for u, tit in pares[:MAX_WEB]:
            u = html.unescape(u);
            if not u.startswith("http"):
                continue;
            achados.append({"titulo": re.sub(r"<[^>]+>", "", html.unescape(tit)).strip(),
                            "link": u, "fonte": "DuckDuckGo", "descricao": ""});
    except Exception as e:
        achados.append({"titulo": "(DuckDuckGo falhou: " + type(e).__name__ + ")", "link": "",
                        "fonte": "DuckDuckGo", "descricao": ""});
    return achados;


def _da_base(nome, etype):
    """Entidades de mesmo nome na base e o que elas ja carregam. O servidor anexa as
    referencias no proprio search (Entity::appendData), entao nao ha chamada extra."""
    achados = [];
    try:
        for e in Entity.search("person,organization,other", "%" + nome + "%", proxy=True):
            for ref in (e.get("references") or []):
                link = (ref.get("link1") or "").strip();
                if link == "":
                    continue;
                achados.append({
                    "titulo": ref.get("title") or "(sem título)",
                    "link": link,
                    "fonte": "base: " + str(e.get("text_label")) + " [" + str(e.get("server") or "local") + "]",
                    "descricao": ref.get("descricao") or "",
                    "link2": ref.get("link2") or "", "link3": ref.get("link3") or "",
                });
    except Exception as e:
        traceback.print_exc();
        achados.append({"titulo": "(a busca na base falhou: " + str(e)[:60] + ")", "link": "",
                        "fonte": "base", "descricao": ""});
    return achados;


class _Buscador(QObject):
    progresso = Signal(str);
    terminou  = Signal(object);

    def __init__(self, nome, etype):
        super().__init__();
        self.nome = nome; self.etype = etype;

    @Slot()
    def executar(self):
        self.progresso.emit("Procurando na sua base…");
        base = _da_base(self.nome, self.etype);
        self.progresso.emit("Consultando a Wikipedia…");
        web = _wikipedia(self.nome);
        self.progresso.emit("Consultando o DuckDuckGo…");
        web = web + _duckduckgo(self.nome);

        # Um link que ja veio da base nao precisa aparecer de novo como suspeito.
        vistos = set(x["link"] for x in base if x["link"]);
        web = [x for x in web if x["link"] == "" or x["link"] not in vistos];
        self.terminou.emit({"base": base, "web": web});


class _Leitor(QObject):
    """Baixa o texto de uma URL para o painel de leitura."""
    pronto = Signal(str, str);   # link, texto

    def __init__(self, link):
        super().__init__(); self.link = link;

    @Slot()
    def executar(self):
        texto, erro = _texto_da_pagina(self.link);
        self.pronto.emit(self.link, texto if texto != None else "Não foi possível ler: " + str(erro));


class DialogBuscarReferencias(QDialog):
    def __init__(self, parent, entity):
        super().__init__(parent);
        self.entity = entity;
        self.resize(1060, 620);
        self.setWindowTitle("Procurar referências — " + str(entity.text or ""));
        self.setFont( Configuration.instancia().getFont() );
        self.thread = None; self.worker = None;
        self.t_ler = None; self.w_ler = None;
        self.cache = {};

        principal = QVBoxLayout(); self.setLayout(principal);

        topo = QHBoxLayout();
        topo.addWidget( QLabel("Entidade: <b>" + html.escape(str(entity.text or "")) + "</b>") );
        self.btn_buscar = QPushButton("Procurar");
        self.btn_buscar.clicked.connect(self.btn_buscar_click);
        topo.addWidget(self.btn_buscar);
        topo.addStretch();
        principal.addLayout(topo);

        self.lbl = QLabel("A base é dado seu, já curado. A web é suspeita até você ler.");
        self.lbl.setStyleSheet("color:#666;");
        principal.addWidget(self.lbl);

        div = QSplitter(Qt.Horizontal);

        esq = QWidget(); lesq = QVBoxLayout(esq); lesq.setContentsMargins(0,0,0,0);
        lesq.addWidget( QLabel("<b>Confiáveis</b> — da sua base") );
        self.tab_base = self.__tabela__();
        lesq.addWidget(self.tab_base);
        lesq.addWidget( QLabel("<b>Não confiáveis</b> — da web. Clique para ler antes de aprovar.") );
        self.tab_web = self.__tabela__();
        self.tab_web.itemSelectionChanged.connect(self.__ler_selecionada__);
        lesq.addWidget(self.tab_web);
        div.addWidget(esq);

        dir_ = QWidget(); ldir = QVBoxLayout(dir_); ldir.setContentsMargins(0,0,0,0);
        ldir.addWidget( QLabel("<b>Leitura</b>") );
        self.txt = QTextEdit(); self.txt.setReadOnly(True);
        self.txt.setPlaceholderText("Clique numa referência não confiável para baixar e ler o texto.");
        ldir.addWidget(self.txt);
        div.addWidget(dir_);
        div.setSizes([620, 440]);
        principal.addWidget(div);

        botoes = QHBoxLayout();
        self.btn_anexar = QPushButton("Anexar marcadas");
        self.btn_anexar.setEnabled(False);
        self.btn_anexar.clicked.connect(self.btn_anexar_click);
        botoes.addWidget(self.btn_anexar);
        botoes.addStretch();
        principal.addLayout(botoes);

    def __tabela__(self):
        t = QTableWidget(0, 4);
        t.setHorizontalHeaderLabels(["", "Título", "Fonte", "Link"]);
        t.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch);
        t.setColumnWidth(0, 28); t.setColumnWidth(1, 250); t.setColumnWidth(2, 160);
        t.setSelectionBehavior(QAbstractItemView.SelectRows);
        t.setEditTriggers(QAbstractItemView.NoEditTriggers);
        return t;

    def __msg__(self, t):
        b = QMessageBox(self); b.setText(str(t)); b.exec();

    def __check__(self, marcado):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setAlignment(Qt.AlignCenter);
        c = QCheckBox(); c.setChecked(marcado); l.addWidget(c);
        return w, c;

    def btn_buscar_click(self):
        nome = str(self.entity.text or "").strip();
        if nome == "":
            self.__msg__("A entidade não tem nome."); return;
        if self.thread != None and self.thread.isRunning():
            return;
        self.btn_buscar.setEnabled(False);
        self.thread = QThread();
        self.worker = _Buscador(nome, self.entity.etype);
        self.worker.moveToThread(self.thread);
        self.thread.started.connect(self.worker.executar);
        self.worker.progresso.connect(lambda m: self.lbl.setText("⏳ " + m));
        self.worker.terminou.connect(self.__pronto__);
        self.thread.start();

    @Slot(object)
    def __pronto__(self, r):
        self.thread.quit(); self.thread.wait();
        self.thread = None; self.worker = None;
        self.btn_buscar.setEnabled(True);

        self.achados_base = r["base"]; self.achados_web = r["web"];
        self.checks_base = []; self.checks_web = [];

        # Confiavel ja nasce marcado; suspeito nasce desmarcado. E a diferenca entre
        # "voce ja aprovou isso um dia" e "isso apareceu numa busca".
        self.__preencher__(self.tab_base, r["base"], self.checks_base, True);
        self.__preencher__(self.tab_web,  r["web"],  self.checks_web,  False);

        self.lbl.setText("%d confiável(is) da sua base · %d da web para revisar." %
                         (len(r["base"]), len(r["web"])));
        self.btn_anexar.setEnabled( len(r["base"]) + len(r["web"]) > 0 );

    def __preencher__(self, tab, itens, checks, marcado):
        tab.setRowCount(0); del checks[:];
        for it in itens:
            i = tab.rowCount(); tab.insertRow(i);
            w, c = self.__check__(marcado and it["link"] != "");
            c.setEnabled(it["link"] != "");
            tab.setCellWidget(i, 0, w); checks.append(c);
            tab.setItem(i, 1, QTableWidgetItem(it["titulo"]));
            tab.setItem(i, 2, QTableWidgetItem(it["fonte"]));
            tab.setItem(i, 3, QTableWidgetItem(it["link"]));

    def __ler_selecionada__(self):
        i = self.tab_web.currentRow();
        if i < 0 or i >= len(self.achados_web):
            return;
        link = self.achados_web[i]["link"];
        if link == "":
            return;
        if link in self.cache:
            self.txt.setPlainText(self.cache[link]); return;
        self.txt.setPlainText("Baixando " + link + " …");
        if self.t_ler != None and self.t_ler.isRunning():
            return;
        self.t_ler = QThread();
        self.w_ler = _Leitor(link);
        self.w_ler.moveToThread(self.t_ler);
        self.t_ler.started.connect(self.w_ler.executar);
        self.w_ler.pronto.connect(self.__texto__);
        self.t_ler.start();

    @Slot(str, str)
    def __texto__(self, link, texto):
        self.t_ler.quit(); self.t_ler.wait(); self.t_ler = None; self.w_ler = None;
        self.cache[link] = texto;
        if self.tab_web.currentRow() >= 0 and self.achados_web[self.tab_web.currentRow()]["link"] == link:
            self.txt.setPlainText(texto);

    def btn_anexar_click(self):
        n = 0; ja = 0;
        existentes = set((r.link1 or "").strip() for r in self.entity.references);
        for itens, checks in ((self.achados_base, self.checks_base), (self.achados_web, self.checks_web)):
            for i, it in enumerate(itens):
                if i >= len(checks) or not checks[i].isChecked() or it["link"] == "":
                    continue;
                if it["link"] in existentes:
                    ja = ja + 1; continue;   # nao duplica o que a entidade ja tem
                self.entity.addReference(it["titulo"], it["link"], it.get("link2", ""),
                                         it.get("link3", ""), descricao=it.get("descricao", ""));
                existentes.add(it["link"]);
                n = n + 1;
        self.__msg__("Anexadas %d referência(s)." % n +
                     ("\n%d já estavam na entidade." % ja if ja else "") +
                     "\n\nSalve o mapa para gravar.");
        self.accept();
