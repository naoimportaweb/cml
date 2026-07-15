"""Gerente da geracao de report em segundo plano.

Existe para a thread NAO pertencer ao dialogo: se o QThread e filho do DialogDocument,
fechar o dialogo mata (ou orfana) a geracao, e o usuario fica preso olhando a barra. Aqui o
gerente e um singleton de modulo, vive enquanto o app viver, e o dialogo so consulta.

O trabalho todo — ler os links, falar com o rolhama, montar o PDF e subir — roda na thread
do worker. Nada disso pode voltar para a thread da GUI, senao a janela congela por minutos.
"""

import os, sys, inspect, traceback, tempfile;

from PySide6.QtCore import QObject, QThread, Signal, Slot;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( os.path.dirname( CURRENTDIR ) );
sys.path.append( ROOT );

from classlib.document import Document;
from classlib import report;


class _Gerador(QObject):
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
            resumo = report.gerar(self.mapa, self.caminho,
                                  progresso=lambda m: self.progresso.emit(m));
            # O upload vai aqui dentro, na thread do worker: se ficasse no dialogo, fechar
            # a janela antes do fim deixaria o PDF gerado e nao anexado.
            self.progresso.emit("Anexando o PDF ao mapa…");
            titulo = "Report — " + str(self.mapa.getName());
            desc = ("Gerado pelo rolhama (canal " + str(resumo.get("canal")) + "). " +
                    str(resumo.get("lidas")) + " de " + str(resumo.get("total")) + " referências lidas.");
            r = Document().upload_file( self.caminho, self.mapa.id, title=titulo,
                                        description=desc, origem="rolhama" );
            if r == False:
                raise Exception("O report foi gerado mas o servidor recusou o upload. O arquivo está em " + self.caminho);
            resumo["document_id"] = r.get("id");
            self.terminou.emit(resumo);
        except Exception as e:
            traceback.print_exc();
            self.falhou.emit(str(e));


class ReportManager(QObject):
    # A GUI escuta estes sinais para mostrar progresso e avisar no fim, sem prender ninguem.
    progresso = Signal(str);
    concluiu  = Signal(object);   # resumo (com mapa_nome)
    falhou    = Signal(str);
    mudou     = Signal();         # ocupado/livre mudou: hora de atualizar marcas

    _inst = None;

    @staticmethod
    def instancia():
        if ReportManager._inst == None:
            ReportManager._inst = ReportManager();
        return ReportManager._inst;

    def __init__(self):
        super().__init__();
        self.thread = None;
        self.worker = None;
        self.mapa_id = None;
        self.mapa_nome = None;
        self.ultimo = "";
        self.pendente = None;     # resumo do ultimo job terminado e ainda nao visto

    def ocupado(self):
        return self.thread != None and self.thread.isRunning();

    def iniciar(self, mapa):
        if self.ocupado():
            # Trava local. A do banco (report_job) e a que vale entre maquinas; esta so
            # evita o usuario disparar dois no mesmo cliente.
            raise Exception("Já existe um report sendo gerado: " + str(self.mapa_nome or "") + ".");

        caminho = os.path.join(tempfile.gettempdir(), "cml_report_" + str(mapa.id)[:16] + ".pdf");
        self.mapa_id = mapa.id;
        self.mapa_nome = mapa.getName();
        self.ultimo = "Preparando…";

        self.thread = QThread();
        self.worker = _Gerador(mapa, caminho);
        self.worker.moveToThread(self.thread);
        self.thread.started.connect(self.worker.executar);
        self.worker.progresso.connect(self.__progresso__);
        self.worker.terminou.connect(self.__terminou__);
        self.worker.falhou.connect(self.__falhou__);
        self.thread.start();
        self.mudou.emit();
        return caminho;

    @Slot(str)
    def __progresso__(self, msg):
        self.ultimo = msg;
        self.progresso.emit(msg);

    def __encerrar__(self):
        if self.thread != None:
            self.thread.quit();
            self.thread.wait();
        self.thread = None;
        self.worker = None;

    @Slot(object)
    def __terminou__(self, resumo):
        resumo["mapa_nome"] = self.mapa_nome;
        resumo["mapa_id"] = self.mapa_id;
        self.__encerrar__();
        self.ultimo = "Concluído";
        self.pendente = resumo;
        self.concluiu.emit(resumo);
        self.mudou.emit();

    @Slot(str)
    def __falhou__(self, msg):
        nome = self.mapa_nome;
        self.__encerrar__();
        self.ultimo = "Falhou";
        self.pendente = {"erro": msg, "mapa_nome": nome};
        self.falhou.emit(msg);
        self.mudou.emit();

    def marcar_visto(self):
        self.pendente = None;
        self.mudou.emit();
