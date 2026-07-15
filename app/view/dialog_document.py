import os, sys, inspect, traceback, tempfile;

from PySide6.QtCore import (Qt, Slot, QThread, Signal, QObject)
from PySide6.QtGui import QAction, QIcon, QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QApplication, QFileDialog, QMessageBox, QDialog, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                               QHeaderView, QAbstractItemView, QProgressDialog)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from classlib.configuration import Configuration;
from classlib.document import Document;
from classlib import report;


class GeradorReport(QObject):
    """Roda a geracao fora da thread da GUI: ler 50 links e esperar o ollama leva minutos,
    e na thread da interface a janela congelaria."""
    progresso = Signal(str);
    terminou  = Signal(object);
    falhou    = Signal(str);

    def __init__(self, mapa, caminho):
        super().__init__();
        self.mapa = mapa;
        self.caminho = caminho;

    @Slot()
    def executar(self):
        try:
            resumo = report.gerar(self.mapa, self.caminho, progresso=lambda m: self.progresso.emit(m));
            self.terminou.emit(resumo);
        except Exception as e:
            traceback.print_exc();
            self.falhou.emit(str(e));


class DialogDocument(QDialog):
    def __init__(self, form, mapa):
        super().__init__(form);
        self.mapa = mapa;
        self.resize(880, 420);
        self.setWindowTitle("Documentos do mapa: " + str(mapa.getName()));
        self.setFont( Configuration.instancia().getFont() );
        self.thread = None;
        self.worker = None;

        principal = QVBoxLayout();
        self.setLayout( principal );

        self.tabela = QTableWidget(0, 5);
        self.tabela.setHorizontalHeaderLabels(["Título", "Origem", "Tamanho", "Mapas", "Criado"]);
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows);
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers);
        self.tabela.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch);
        principal.addWidget( self.tabela );

        self.lbl = QLabel("");
        principal.addWidget( self.lbl );

        botoes = QHBoxLayout();
        self.btn_anexar = QPushButton("Anexar PDF…");
        self.btn_anexar.clicked.connect(self.btn_anexar_click);
        botoes.addWidget(self.btn_anexar);

        self.btn_gerar = QPushButton("Gerar report (rolhama)");
        self.btn_gerar.clicked.connect(self.btn_gerar_click);
        botoes.addWidget(self.btn_gerar);

        self.btn_baixar = QPushButton("Baixar…");
        self.btn_baixar.clicked.connect(self.btn_baixar_click);
        botoes.addWidget(self.btn_baixar);

        self.btn_remover = QPushButton("Desanexar");
        self.btn_remover.clicked.connect(self.btn_remover_click);
        botoes.addWidget(self.btn_remover);

        botoes.addStretch();
        principal.addLayout(botoes);

        self.carregar();

    def __erro__(self, e):
        msg = QMessageBox(self);
        msg.setText(str(e));
        msg.exec();

    def carregar(self):
        try:
            lista = Document.list_by_map( self.mapa.id );
        except Exception as e:
            self.__erro__(e);
            lista = [];
        self.lista = lista;
        self.tabela.setRowCount(0);
        for d in lista:
            i = self.tabela.rowCount();
            self.tabela.insertRow(i);
            self.tabela.setItem(i, 0, QTableWidgetItem( str(d.get("title") or "(sem título)") ));
            self.tabela.setItem(i, 1, QTableWidgetItem( str(d.get("origem") or "") ));
            self.tabela.setItem(i, 2, QTableWidgetItem( self.__tamanho__( d.get("bytes") ) ));
            # "Mapas" mostra em quantos mapas o PDF esta: e o aviso de que desanexar aqui
            # nao o apaga dos outros.
            self.tabela.setItem(i, 3, QTableWidgetItem( str(d.get("mapas") or 1) ));
            self.tabela.setItem(i, 4, QTableWidgetItem( str(d.get("creation_time") or "") ));
        self.lbl.setText( str(len(lista)) + (" documento" if len(lista) == 1 else " documentos") + " neste mapa." );

    @staticmethod
    def __tamanho__(n):
        try:
            n = float(n or 0);
        except Exception:
            return "—";
        for u in ["B", "KB", "MB", "GB"]:
            if n < 1024:
                return ("%.0f %s" % (n, u)) if u == "B" else ("%.1f %s" % (n, u));
            n = n / 1024;
        return "%.1f TB" % n;

    def __selecionado__(self):
        linha = self.tabela.currentRow();
        if linha < 0 or linha >= len(self.lista):
            self.__erro__("Selecione um documento na lista.");
            return None;
        return self.lista[linha];

    def btn_anexar_click(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Escolha o PDF", os.path.expanduser("~"), "PDF (*.pdf)");
        if caminho == "":
            return;
        try:
            r = Document().upload_file( caminho, self.mapa.id );
            if r == False:
                raise Exception("O servidor recusou o arquivo.");
            if r.get("ja_existia"):
                # Dedup por sha256: o mesmo PDF ja estava no servidor, veio de outro mapa.
                self.__erro__("Este PDF já existia no servidor (mesmo conteúdo) e foi vinculado a este mapa.");
            self.carregar();
        except Exception as e:
            self.__erro__(e);

    def btn_baixar_click(self):
        d = self.__selecionado__();
        if d == None:
            return;
        sugerido = os.path.join(os.path.expanduser("~"), (str(d.get("title") or "documento")).replace("/", "_"));
        if not sugerido.lower().endswith(".pdf"):
            sugerido = sugerido + ".pdf";
        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar como", sugerido, "PDF (*.pdf)");
        if caminho == "":
            return;
        try:
            r = Document().download_to( d["id"], caminho );
            if r == False:
                raise Exception("Não foi possível baixar.");
            QDesktopServices.openUrl(QUrl.fromLocalFile(caminho));
        except Exception as e:
            self.__erro__(e);

    def btn_remover_click(self):
        d = self.__selecionado__();
        if d == None:
            return;
        n = int(d.get("mapas") or 1);
        aviso = "Desanexar “" + str(d.get("title")) + "” deste mapa?";
        if n > 1:
            aviso = aviso + "\n\nEle continua em outros " + str(n - 1) + " mapa(s).";
        else:
            aviso = aviso + "\n\nEste é o único mapa que o usa: o arquivo será apagado do servidor.";
        if QMessageBox.question(self, "Desanexar", aviso) != QMessageBox.Yes:
            return;
        try:
            Document().unlink_map( d["id"], self.mapa.id );
            self.carregar();
        except Exception as e:
            self.__erro__(e);

    def btn_gerar_click(self):
        total = len( report.coletar_referencias(self.mapa) );
        if total == 0:
            self.__erro__("Este mapa não tem referências com link; não há o que ler para gerar o report.");
            return;
        lidas = min(total, report.MAX_REFERENCIAS);
        aviso = ("Gerar um report deste mapa com o rolhama?\n\n"
                 "Referências no mapa: " + str(total) + "\n"
                 "Serão lidas: " + str(lidas) + " (limite " + str(report.MAX_REFERENCIAS) + ")");
        if total > report.MAX_REFERENCIAS:
            aviso = aviso + "\nAs outras " + str(total - report.MAX_REFERENCIAS) + " entram na lista “Demais referências”.";
        aviso = aviso + ("\n\nO worker do rolhama atende um pedido por vez, para todos os projetos: "
                         "isso pode levar minutos e segura a fila dos outros enquanto roda.");
        if QMessageBox.question(self, "Gerar report", aviso) != QMessageBox.Yes:
            return;

        self.caminho_tmp = os.path.join(tempfile.gettempdir(), "cml_report_" + str(self.mapa.id)[:16] + ".pdf");

        self.prog = QProgressDialog("Preparando…", "Cancelar", 0, 0, self);
        self.prog.setWindowTitle("Gerando report");
        self.prog.setWindowModality(Qt.WindowModal);
        self.prog.setMinimumWidth(460);
        self.prog.show();

        self.thread = QThread();
        self.worker = GeradorReport(self.mapa, self.caminho_tmp);
        self.worker.moveToThread(self.thread);
        self.thread.started.connect(self.worker.executar);
        self.worker.progresso.connect(lambda m: self.prog.setLabelText(m));
        self.worker.terminou.connect(self.__report_pronto__);
        self.worker.falhou.connect(self.__report_falhou__);
        self.btn_gerar.setEnabled(False);
        self.thread.start();

    def __encerrar__(self):
        self.prog.close();
        self.thread.quit();
        self.thread.wait();
        self.btn_gerar.setEnabled(True);

    def __report_pronto__(self, resumo):
        self.__encerrar__();
        try:
            titulo = "Report — " + str(self.mapa.getName());
            desc = ("Gerado pelo rolhama (canal " + str(resumo["canal"]) + "). " +
                    str(resumo["lidas"]) + " de " + str(resumo["total"]) + " referências lidas.");
            r = Document().upload_file( self.caminho_tmp, self.mapa.id, title=titulo, description=desc, origem="rolhama" );
            if r == False:
                raise Exception("O report foi gerado mas o servidor recusou o upload: " + self.caminho_tmp);
            self.carregar();
            msg = ("Report gerado e anexado.\n\n"
                   "Referências lidas: " + str(resumo["lidas"]) + "\n"
                   "Não puderam ser lidas: " + str(resumo["falhas"]) + "\n"
                   "Em “Demais referências”: " + str(resumo["demais"]) + "\n"
                   "Canal do rolhama: " + str(resumo["canal"]));
            self.__erro__(msg);
        except Exception as e:
            self.__erro__(e);

    def __report_falhou__(self, msg):
        self.__encerrar__();
        self.__erro__("Falha ao gerar o report:\n\n" + msg);
