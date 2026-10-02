"""Gerente dos transforms em segundo plano (padrao do ReportManager: a QThread NAO pertence
ao dialogo nem a janela do mapa — fechar a janela nao mata a execucao).

Fluxo: MdiMap.menu_transforms -> TransformManager.iniciar() -> thread roda o Executor (com
cache e log) e, depois, procura na base cada entidade proposta para oferecer o REAPROVEITAMENTO
(entidades sao globais; buscar antes de criar). Ao terminar, o gerente abre o painel Proposta.
"""

import os, sys, inspect, traceback, itertools;

from PySide6.QtCore import QObject, QThread, Signal, Slot;
from PySide6.QtWidgets import QMessageBox;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( os.path.dirname( CURRENTDIR ) );
sys.path.append( ROOT );

from transform.nucleo import Executor, norm;
from transform.contexto import Contexto;

MAX_BUSCAS = 60;    # cada busca e uma ida ao servidor; alem disso o painel abre sem sugerir reaproveitamento
_ids = itertools.count(1);


class Job:
    def __init__(self, cfg, entrada, mdimap, caixa):
        self.id = next(_ids);
        self.cfg = cfg;
        self.entrada = entrada;
        self.mdimap = mdimap;
        self.caixa = caixa;
        self.cancelado = False;
        self.estado = "executando";
        self.thread = None;
        self.worker = None;
        self.resultado = None;
        self.do_cache = False;

    def nome(self):
        return self.cfg["nome"] + " — " + str(self.entrada.get("text_label"));


class _Worker(QObject):
    progresso = Signal(str);
    terminou  = Signal(object);
    falhou    = Signal(str);

    def __init__(self, job):
        super().__init__();
        self.job = job;

    @Slot()
    def executar(self):
        job = self.job;
        try:
            self.progresso.emit("rodando " + job.cfg["nome"] + "…");
            resultado, do_cache = Executor().executar(job.cfg, job.entrada, lambda cfg: Contexto(cfg, lambda: job.cancelado));
            if job.cancelado:
                raise Exception("cancelado");
            self.progresso.emit("conferindo duplicatas na base…");
            self.__candidatas__(job, resultado);
            job.do_cache = do_cache;
            self.terminou.emit(resultado);
        except Exception as e:
            if str(e) != "cancelado":
                traceback.print_exc();
            self.falhou.emit(str(e) or type(e).__name__);

    def __candidatas__(self, job, resultado):
        from classlib.entity import Entity;
        feitas = 0;
        for e in resultado.entidades:
            e["candidatas"] = [];
            if e.get("id"):
                continue;     # o transform ja disse que e uma entidade da base
            if feitas >= MAX_BUSCAS or job.cancelado:
                continue;
            feitas += 1;
            try:
                # texto exato (sem %): LIKE sem curinga e igualdade sem caixa; a comparacao sem
                # acento/pontuacao e refeita aqui.
                achadas = Entity.search("person,organization,other", e["text_label"]);
            except Exception:
                resultado.aviso("A busca de duplicatas na base falhou; nada foi sugerido para reaproveitar.");
                return;
            e["candidatas"] = [a for a in achadas if norm(a.get("text_label")) == norm(e["text_label"])][:5];
        if feitas >= MAX_BUSCAS:
            resultado.aviso("Duplicatas conferidas só nas primeiras %d entidades." % MAX_BUSCAS);


class TransformManager(QObject):
    mudou = Signal();
    _inst = None;

    @classmethod
    def instancia(cls):
        if cls._inst == None:
            cls._inst = TransformManager();
        return cls._inst;

    def __init__(self):
        super().__init__();
        self.jobs = [];

    def ativos(self):
        return [j for j in self.jobs if j.estado == "executando"];

    def iniciar(self, cfg, entrada, mdimap, caixa):
        job = Job(cfg, entrada, mdimap, caixa);
        job.thread = QThread();
        job.worker = _Worker(job);
        job.worker.moveToThread(job.thread);
        job.thread.started.connect(job.worker.executar);
        # Slots do PROPRIO gerente (que vive na thread da GUI), nao lambdas: lambda sem objeto
        # de contexto roda na thread do emissor, e o thread.wait() do __encerrar__ esperaria
        # por si mesmo.
        job.worker.progresso.connect(self.__on_progresso__);
        job.worker.terminou.connect(self.__on_terminou__);
        job.worker.falhou.connect(self.__on_falhou__);
        self.jobs.append(job);
        job.thread.start();
        self.__status__(job, "iniciado");
        self.mudou.emit();
        return job;

    def cancelar(self, job):
        job.cancelado = True;

    def __status__(self, job, msg, tempo=0):
        try:
            n = len(self.ativos());
            job.mdimap.form_principal.statusBar().showMessage("Transform: %s — %s%s" % (job.nome(), msg, (" (+%d em andamento)" % (n - 1)) if n > 1 else ""), tempo);
        except Exception:
            pass;

    def __encerrar__(self, job, estado):
        job.estado = estado;
        if job.thread != None:
            job.thread.quit(); job.thread.wait();
        job.thread = None;
        self.mudou.emit();

    @Slot(str)
    def __on_progresso__(self, msg):
        self.__status__(self.sender().job, msg);

    @Slot(object)
    def __on_terminou__(self, resultado):
        self.__terminou__(self.sender().job, resultado);

    @Slot(str)
    def __on_falhou__(self, msg):
        self.__falhou__(self.sender().job, msg);

    def __terminou__(self, job, resultado):
        self.__encerrar__(job, "concluido");
        job.resultado = resultado;
        self.__status__(job, "concluído%s: %d entidade(s), %d vínculo(s)" % (" (cache)" if job.do_cache else "", len(resultado.entidades), len(resultado.vinculos)), 15000);
        parent = job.mdimap.form_principal;
        if job.caixa not in job.mdimap.mapa.elements:
            QMessageBox.information(parent, "Transform", "A caixa de origem foi removida do mapa enquanto o transform rodava; o resultado foi descartado.");
            return;
        from view.dialog_transform_proposta import DialogTransformProposta;
        DialogTransformProposta(parent, job).exec();

    def __falhou__(self, job, msg):
        self.__encerrar__(job, "cancelado" if job.cancelado else "falhou");
        if job.cancelado:
            self.__status__(job, "cancelado", 8000);
            return;
        self.__status__(job, "falhou", 15000);
        QMessageBox.warning(job.mdimap.form_principal, "Transform falhou", job.nome() + "\n\n" + msg);
