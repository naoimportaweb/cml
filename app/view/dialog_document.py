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
from view.ui.report_manager import ReportManager;


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

        # Linha de estado do report: fica visivel enquanto gera, mesmo se a geracao tiver
        # sido disparada de outro mapa.
        self.lbl_report = QLabel("");
        self.lbl_report.setStyleSheet("color: #666;");
        principal.addWidget( self.lbl_report );

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

        # O dialogo escuta o gerente: se um report ja estiver rodando (disparado daqui ou
        # de outro mapa, antes desta janela existir), o botao ja nasce desabilitado. Estado
        # tem que ser visivel, nao descoberto errando.
        gerente = ReportManager.instancia();
        gerente.progresso.connect(self.__estado_report__);
        gerente.mudou.connect(self.__estado_report__);
        gerente.concluiu.connect(self.__report_terminou__);
        gerente.falhou.connect(self.__report_terminou__);

        self.carregar();
        self.__estado_report__();

    def __estado_report__(self, *args):
        gerente = ReportManager.instancia();
        if gerente.ocupado():
            self.btn_gerar.setEnabled(False);
            self.btn_gerar.setText("Gerando report…");
            alvo = str(gerente.mapa_nome or "");
            if gerente.mapa_id != self.mapa.id:
                self.btn_gerar.setToolTip("Um report de “" + alvo + "” está em andamento. O rolhama atende um por vez.");
                self.lbl_report.setText("⏳ Gerando report de “" + alvo + "” — " + str(gerente.ultimo));
            else:
                self.btn_gerar.setToolTip("Gerando o report deste mapa.");
                self.lbl_report.setText("⏳ " + str(gerente.ultimo));
        else:
            self.btn_gerar.setEnabled(True);
            self.btn_gerar.setText("Gerar report (rolhama)");
            self.btn_gerar.setToolTip("");
            self.lbl_report.setText("");

    def __report_terminou__(self, *args):
        self.__estado_report__();
        self.carregar();   # o PDF novo entra na lista sem o usuario reabrir a janela

    def closeEvent(self, event):
        # Desliga do gerente ao fechar. Sem isto o dialogo morto continua escutando: quando
        # um report termina, ele chama carregar() e recarrega a lista do SEU mapa, que pode
        # nao ser o do report — gastando requisicao e atualizando a janela errada.
        gerente = ReportManager.instancia();
        for sinal, slot in ((gerente.progresso, self.__estado_report__),
                            (gerente.mudou,     self.__estado_report__),
                            (gerente.concluiu,  self.__report_terminou__),
                            (gerente.falhou,    self.__report_terminou__)):
            try:
                sinal.disconnect(slot);
            except (RuntimeError, TypeError):
                pass;   # ja desconectado
        super().closeEvent(event);

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
        gerente = ReportManager.instancia();
        if gerente.ocupado():
            self.__erro__("Já existe um report sendo gerado: “" + str(gerente.mapa_nome or "") + "”.\n\n"
                          "O rolhama atende um pedido por vez. Espere terminar.");
            return;

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
        aviso = aviso + ("\n\nRoda em segundo plano: pode fechar esta janela e continuar trabalhando. "
                         "O aviso aparece quando terminar.\n\n"
                         "O worker do rolhama atende um pedido por vez, para todos os projetos.");
        if QMessageBox.question(self, "Gerar report", aviso) != QMessageBox.Yes:
            return;

        try:
            gerente.iniciar( self.mapa );
        except Exception as e:
            self.__erro__(e);
            return;
        # Fecha e devolve a ferramenta: quem acompanha o progresso e a barra de status da
        # janela principal, e o gerente sobrevive a este dialogo.
        self.accept();
