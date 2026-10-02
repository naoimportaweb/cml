"""Painel Proposta: o resultado de um transform NUNCA grava direto no mapa. O analista marca o
que quer, confere o tipo e escolhe, por entidade, entre criar nova ou reaproveitar a que ja
existe na base. So entao o aplicar() insere as caixas e os vinculos."""

import os, sys, inspect;

from PySide6.QtCore import Qt;
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                               QHeaderView, QComboBox, QMessageBox, QCheckBox, QWidget, QAbstractItemView);

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from classlib.configuration import Configuration;
from transform.nucleo import ENTRADA, ROTULO_FONTE, norm;
from transform.aplicar import aplicar;

TIPOS = ["person", "organization", "other"];
ROTULO = {"person": "Pessoa", "organization": "Organização", "other": "Outro"};


class DialogTransformProposta(QDialog):
    def __init__(self, form, job):
        super().__init__(form);
        self.job = job;
        self.resultado = job.resultado;
        self.mdimap = job.mdimap;
        self.setWindowTitle("Proposta — " + job.nome());
        self.resize(1060, 620);
        self.setFont( Configuration.instancia().getFont() );

        L = QVBoxLayout(); self.setLayout(L);
        origem = ROTULO_FONTE.get(job.cfg["fonte"], job.cfg["fonte"]);
        cab = QLabel("Fonte: %s%s. Nada entra no mapa sem você marcar; o mapa só grava quando você salvá-lo." %
                     (origem, " (resultado do cache)" if job.do_cache else ""));
        cab.setStyleSheet("color: #666;"); cab.setWordWrap(True);
        L.addWidget(cab);

        L.addWidget(QLabel("Entidades:"));
        self.tab_ent = QTableWidget(0, 6);
        self.tab_ent.setHorizontalHeaderLabels(["", "Nome", "Tipo", "Ação", "Descrição", "Fonte"]);
        self.tab_ent.setSelectionBehavior(QAbstractItemView.SelectRows);
        h = self.tab_ent.horizontalHeader();
        h.setSectionResizeMode(4, QHeaderView.Stretch);
        self.tab_ent.setColumnWidth(0, 30); self.tab_ent.setColumnWidth(1, 220);
        self.tab_ent.setColumnWidth(2, 120); self.tab_ent.setColumnWidth(3, 230); self.tab_ent.setColumnWidth(5, 170);
        L.addWidget(self.tab_ent);

        L.addWidget(QLabel("Vínculos:"));
        self.tab_vin = QTableWidget(0, 4);
        self.tab_vin.setHorizontalHeaderLabels(["", "De", "Relação", "Para"]);
        self.tab_vin.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch);
        self.tab_vin.setColumnWidth(0, 30); self.tab_vin.setColumnWidth(1, 240); self.tab_vin.setColumnWidth(2, 200);
        L.addWidget(self.tab_vin);

        self.lbl_avisos = QLabel(""); self.lbl_avisos.setWordWrap(True); self.lbl_avisos.setStyleSheet("color: #a15c00;");
        L.addWidget(self.lbl_avisos);

        bt = QHBoxLayout();
        b_todos = QPushButton("Marcar todos"); b_todos.clicked.connect(lambda: self.__marcar__(True));
        b_nenhum = QPushButton("Desmarcar todos"); b_nenhum.clicked.connect(lambda: self.__marcar__(False));
        self.btn_add = QPushButton("Adicionar ao mapa"); self.btn_add.clicked.connect(self.adicionar);
        b_cancel = QPushButton("Cancelar"); b_cancel.clicked.connect(self.reject);
        for b in (b_todos, b_nenhum): bt.addWidget(b);
        bt.addStretch();
        bt.addWidget(self.btn_add); bt.addWidget(b_cancel);
        L.addLayout(bt);

        self.checks_ent, self.combos_tipo, self.combos_acao, self.checks_vin = [], [], [], [];
        self.__preencher__();

    def __nome_ponta__(self, chave):
        if chave == ENTRADA:
            return "● " + str(self.job.entrada.get("text_label"));
        for e in self.resultado.entidades:
            if e["chave"] == chave:
                return e["text_label"];
        return chave;

    def __check__(self, marcado=True):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0, 0, 0, 0); l.setAlignment(Qt.AlignCenter);
        c = QCheckBox(); c.setChecked(marcado); l.addWidget(c);
        return w, c;

    def __preencher__(self):
        for e in self.resultado.entidades:
            i = self.tab_ent.rowCount(); self.tab_ent.insertRow(i);
            w, c = self.__check__(); self.tab_ent.setCellWidget(i, 0, w); self.checks_ent.append(c);
            it = QTableWidgetItem(e["text_label"]); it.setFlags(it.flags() & ~Qt.ItemIsEditable);
            self.tab_ent.setItem(i, 1, it);
            tipo = QComboBox();
            for t in TIPOS: tipo.addItem(ROTULO[t], t);
            tipo.setCurrentIndex(TIPOS.index(e["etype"]) if e["etype"] in TIPOS else 2);
            self.tab_ent.setCellWidget(i, 2, tipo); self.combos_tipo.append(tipo);

            acao = QComboBox();
            if e.get("id"):
                # o transform ja devolveu uma entidade da base
                acao.addItem("Reaproveitar a da base", {"id": e["id"], "text_label": e["text_label"], "etype": e["etype"],
                             "description": e["description"], "small_label": e["small_label"]});
                tipo.setEnabled(False);
            else:
                acao.addItem("Criar nova", None);
                for cand in e.get("candidatas") or []:
                    acao.addItem("Reaproveitar: %s (%s) %s" % (cand.get("text_label"), ROTULO.get(cand.get("etype"), cand.get("etype")), str(cand.get("description") or "")[:40]), cand);
                if e.get("candidatas"):
                    acao.setCurrentIndex(1);     # ja existe: o padrao e NAO duplicar
            acao.currentIndexChanged.connect(lambda _i, a=acao, t=tipo: t.setEnabled(a.currentData() == None));
            tipo.setEnabled(acao.currentData() == None);
            self.tab_ent.setCellWidget(i, 3, acao); self.combos_acao.append(acao);

            d = QTableWidgetItem(e["description"]); d.setFlags(d.flags() & ~Qt.ItemIsEditable); self.tab_ent.setItem(i, 4, d);
            ref = (e.get("referencias") or [{}])[0];
            f = QTableWidgetItem(str(ref.get("title") or "—")); f.setToolTip(str(ref.get("link1") or "")); f.setFlags(f.flags() & ~Qt.ItemIsEditable);
            self.tab_ent.setItem(i, 5, f);

        for v in self.resultado.vinculos:
            i = self.tab_vin.rowCount(); self.tab_vin.insertRow(i);
            w, c = self.__check__(); self.tab_vin.setCellWidget(i, 0, w); self.checks_vin.append(c);
            for col, txt in ((1, self.__nome_ponta__(v["de"])), (2, v["verbo"]), (3, self.__nome_ponta__(v["para"]))):
                it = QTableWidgetItem(txt); it.setFlags(it.flags() & ~Qt.ItemIsEditable); self.tab_vin.setItem(i, col, it);
        self.lbl_avisos.setText("\n".join("⚠ " + a for a in self.resultado.avisos[:8]));
        self.btn_add.setEnabled(bool(self.resultado.entidades or self.resultado.vinculos));

    def __marcar__(self, v):
        for c in self.checks_ent + self.checks_vin:
            c.setChecked(v);

    def adicionar(self):
        try:
            esc_e = {};
            for i, e in enumerate(self.resultado.entidades):
                esc_e[e["chave"]] = {"aceitar": self.checks_ent[i].isChecked(), "etype": self.combos_tipo[i].currentData(),
                                     "reusar": self.combos_acao[i].currentData()};
            esc_v = [c.isChecked() for c in self.checks_vin];

            subtipos, aplicar_st = None, None;
            if any(e.get("sub_etype") for e in self.resultado.entidades):
                # Subtipo so existe se o analista ja o cadastrou (nao ha criacao automatica:
                # o cadastro de subtipos e global e deliberado).
                from classlib.entity import Entity;
                subtipos = {norm(s.get("name")): s.get("name") for s in Entity().load_subetypes()};
                aplicar_st = lambda caixa, nome: caixa.entity.set_subetype(subtipos[norm(nome)]);

            rel = aplicar(self.mdimap.mapa, self.job.caixa, self.resultado, esc_e, esc_v,
                          subtipos_validos=set(subtipos.keys()) if subtipos != None else None, aplicar_subtipo=aplicar_st);
            self.mdimap.redesenhar();
            msg = "Entraram no mapa: %d entidade(s) nova(s), %d reaproveitada(s), %d vínculo(s) novo(s)." % (rel["novas"], rel["reusadas"], rel["vinculos"]);
            if rel["vinculos_reusados"]:
                msg += "\n%d vínculo(s) já existiam e receberam só a referência." % rel["vinculos_reusados"];
            if rel["refs"]:
                msg += "\n%d referência(s) de fonte anexada(s)." % rel["refs"];
            if rel["sem_subtipo"]:
                msg += "\n\nSubtipo não cadastrado (cadastre em File > Sub-tipos se quiser): " + ", ".join(sorted(set(rel["sem_subtipo"])));
            msg += "\n\nSalve o mapa para gravar.";
            QMessageBox.information(self, "Transform", msg);
            self.accept();
        except Exception as e:
            QMessageBox.warning(self, "Transform", "Falha ao adicionar: " + str(e));
