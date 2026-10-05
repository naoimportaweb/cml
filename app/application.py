#!/usr/bin/python3
import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));

sys.path.append(CURRENTDIR);

from argparse import ArgumentParser, RawTextHelpFormatter
from functools import partial


from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QStandardPaths,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow,
                               QMdiArea, QMessageBox, QSystemTrayIcon, QTextEdit)
#import PySide6.QtExampleIcons  # noqa: F401

from view.mdimap import MdiMap;
from view.dialog_relationship import DialogRelationship;
from view.dialog_relationship_check import DialogRelationshipCheck;
from view.dialog_diagram_choice import DialogDiagramChoice;
from view.dialog_diagram_load import DialogDiagramLoad;
from view.dialog_relationship_edit import DialogRelationshipEdit
from view.dialog_connect import DialogConnect;
from view.dialog_import import DialogImport;
from view.dialog_document import DialogDocument;
from view.ui.report_manager import ReportManager;
from classlib.server import Server;
from classlib import exportar_diagrama;

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._mdi_area = QMdiArea()
        self._mdi_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._mdi_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setCentralWidget(self._mdi_area)
        self._mdi_area.subWindowActivated.connect(self.update_menus)
        self.create_actions()
        self.create_menus(); # desativado por padraio
        self.create_tool_bars(); # desativado por padrao
        self.create_status_bar()
        self.update_menus()
        self.read_settings()
        self.setWindowTitle("MDI")
        self.criar_bandeja()
        self.ligar_report()

    def criar_bandeja(self):
        # Nem todo desktop tem bandeja; sem ela o aviso cai na janela nao-modal.
        self._tray = None;
        try:
            if QSystemTrayIcon.isSystemTrayAvailable():
                self._tray = QSystemTrayIcon(QIcon(CURRENTDIR + "/resources/check.png"), self);
                self._tray.setToolTip("CML");
                self._tray.show();
        except Exception:
            self._tray = None;

    def ligar_report(self):
        """A geracao roda no ReportManager, que vive fora dos dialogos. A janela principal
        so escuta: mostra o andamento na barra de status e avisa no fim — sem modal, para
        nao prender a ferramenta."""
        gerente = ReportManager.instancia();
        gerente.progresso.connect(self.report_progresso);
        gerente.concluiu.connect(self.report_concluiu);
        gerente.falhou.connect(self.report_falhou);
        gerente.mudou.connect(self.report_marca);
        self.report_marca();

    @Slot(str)
    def report_progresso(self, msg):
        self.statusBar().showMessage("Report: " + msg);

    def report_marca(self):
        gerente = ReportManager.instancia();
        if gerente.ocupado():
            self._map_documents.setText("Documents ⏳");
        elif gerente.pendente != None:
            # O "*" fica ate o usuario abrir os documentos: e o aviso persistente, para
            # quem estava longe da tela na hora do popup.
            self._map_documents.setText("Documents *");
        else:
            self._map_documents.setText("Documents");

    @Slot(object)
    def report_concluiu(self, resumo):
        mapa = str(resumo.get("mapa_nome") or "(sem nome)");
        self.statusBar().showMessage("Report concluído: " + mapa, 15000);
        # O nome do mapa vai no RESUMO, nao so no corpo: a bandeja mostra pouca coisa, e um
        # aviso que nao diz em qual mapa o report entrou manda o usuario procurar no lugar
        # errado — foi o que aconteceu.
        self.avisar("Report concluído — " + mapa,
                    "Anexado em “" + mapa + "”.",
                    ("Report gerado e anexado.\n\n"
                     "Mapa: " + mapa + "\n"
                     "Referências lidas: " + str(resumo.get("lidas")) + "\n"
                     "Não puderam ser lidas: " + str(resumo.get("falhas")) + "\n"
                     "Em “Demais referências”: " + str(resumo.get("demais")) + "\n"
                     "Canal do rolhama: " + str(resumo.get("canal"))));

    @Slot(str)
    def report_falhou(self, msg):
        gerente = ReportManager.instancia();
        mapa = str((gerente.pendente or {}).get("mapa_nome") or "");
        self.statusBar().showMessage("Report falhou: " + mapa, 15000);
        self.avisar("Report falhou — " + mapa,
                    "Falhou em “" + mapa + "”.",
                    "Falha ao gerar o report de “" + mapa + "”:\n\n" + msg);

    def avisar(self, titulo, resumo, texto):
        """Notificacao do sistema quando houver bandeja; senao, uma janela nao-modal — o
        ponto e nunca bloquear o que o usuario esta fazendo. 'resumo' e a linha curta da
        bandeja; 'texto' e o detalhe da janela."""
        try:
            if self._tray != None and QSystemTrayIcon.supportsMessages():
                self._tray.showMessage(titulo, resumo, QSystemTrayIcon.Information, 10000);
                return;
        except Exception:
            pass;
        box = QMessageBox(self);
        box.setWindowTitle(titulo);
        box.setText(texto);
        box.setWindowModality(Qt.NonModal);   # nao prende a janela principal
        box.show();

    def closeEvent(self, event):
        self._mdi_area.closeAllSubWindows()
        if self._mdi_area.currentSubWindow():
            event.ignore()
        else:
            self.write_settings()
            event.accept()

    @Slot()
    def new_map(self):
        f = DialogDiagramChoice(self);
        f.exec();
        if f.map != None:
            child = MdiMap(self, f.map)
            self._mdi_area.addSubWindow(child);
            child.new_map()
            child.showMaximized();
    
    #def create_mdi_map(self):
    #    f = DialogRelationship(self);
    #    f.exec();
    #    if f.map != None:
    #        child = MdiMap(self, f.map)
    #        self._mdi_area.addSubWindow(child);
    #    return child

    @Slot()
    def open(self):
        f = DialogDiagramLoad(self);
        f.exec();
        # Cancelar o dialogo, ou o load falhar, deixava f.map = None: o MdiMap montava um
        # engine sem mapa e o desenho estourava DENTRO do painter, matando o processo
        # ("Cannot destroy paint device that is being painted" + segfault).
        if f.map == None:
            return;
        child = MdiMap(self, f.map)
        self._mdi_area.addSubWindow(child);
        child.new_map()
        child.showMaximized();

    #def load(self, file_name):
    #    child = self.create_mdi_map()
    #    if child.load_file(file_name):
    #        self.statusBar().showMessage("File loaded", 2000)
    #        child.show()
    #    else:
    #        child.close()

    @Slot()
    def save(self):
        self.active_mdi_child() and self.active_mdi_child().save();
        #if self.active_mdi_child() and self.active_mdi_child().save():
        #    self.statusBar().showMessage("File saved", 2000)

    def __pilha_desfazer__(self):
        # A pilha pertence ao mapa aberto, nao a janela principal: trocar de janela troca de
        # historico, que e o que o usuario espera de documentos separados.
        janela = self.active_mdi_child();
        if janela == None or getattr(janela, "mapa", None) == None:
            return None;
        return getattr(janela.mapa, "desfazer", None);

    @Slot()
    def desfazer(self):
        pilha = self.__pilha_desfazer__();
        if pilha != None and pilha.canUndo():
            pilha.undo();
        self.__atualizar_desfazer__();

    @Slot()
    def refazer(self):
        pilha = self.__pilha_desfazer__();
        if pilha != None and pilha.canRedo():
            pilha.redo();
        self.__atualizar_desfazer__();

    def __atualizar_desfazer__(self):
        # Rotulo que diz O QUE vai ser desfeito ("Desfazer Mover caixa") em vez de so
        # "Desfazer": num mapa, lembrar qual foi a ultima acao e metade do problema.
        pilha = self.__pilha_desfazer__();
        pode_desfazer = pilha != None and pilha.canUndo();
        pode_refazer = pilha != None and pilha.canRedo();
        self._undo_act.setEnabled(pode_desfazer);
        self._redo_act.setEnabled(pode_refazer);
        self._undo_act.setText("Desfazer" + ((" " + pilha.undoText()) if pode_desfazer else ""));
        self._redo_act.setText("Refazer" + ((" " + pilha.redoText()) if pode_refazer else ""));

    @Slot()
    def menu_viewlet(self):
        # Menu na hora do clique: os viewlets de cor/tamanho mais ocultar/mostrar, que sao as
        # duas coisas que mudam a VISTA sem mexer no documento (nao entram no desfazer).
        from PySide6.QtWidgets import QMenu;
        from classlib.relationship import viewlets;
        if self.__mapa_ativo__("MapRelationship") == None:
            return;
        janela = self.active_mdi_child();
        canvas = janela.painter_widget;
        menu = QMenu(self);
        escolhido = [None];
        for nome, texto in viewlets.VIEWLETS:
            acao = menu.addAction(texto);
            acao.setCheckable(True);
            acao.setChecked(canvas.viewlet == nome);
            acao.triggered.connect(lambda _=False, n=nome: escolhido.__setitem__(0, ("viewlet", n)));
        menu.addSeparator();
        acao = menu.addAction("Ocultar selecionadas");
        acao.setEnabled(len(canvas.selecionados()) > 0);
        acao.triggered.connect(lambda _=False: escolhido.__setitem__(0, ("ocultar", None)));
        acao = menu.addAction("Mostrar tudo (%d oculta(s))" % canvas.quantidade_oculta());
        acao.setEnabled(canvas.quantidade_oculta() > 0);
        acao.triggered.connect(lambda _=False: escolhido.__setitem__(0, ("mostrar", None)));
        menu.exec(self._map_tool_bar.mapToGlobal(self._map_tool_bar.rect().bottomLeft()));
        if escolhido[0] == None:
            return;
        acao, valor = escolhido[0];
        if acao == "viewlet":
            canvas.aplicar_viewlet(valor);
            self.statusBar().showMessage("Vista: " + viewlets.rotulo(valor), 5000);
        elif acao == "ocultar":
            self.statusBar().showMessage("%d oculta(s) — nada foi apagado" % canvas.ocultar_selecionados(), 5000);
        else:
            self.statusBar().showMessage("%d voltou(aram) a aparecer" % canvas.mostrar_tudo(), 5000);

    @Slot()
    def buscar_no_mapa(self):
        from PySide6.QtWidgets import QInputDialog;
        if self.__mapa_ativo__("MapRelationship") == None:
            return;
        janela = self.active_mdi_child();
        texto, ok = QInputDialog.getText(self, "Buscar no mapa", "Nome, apelido ou sub-tipo:");
        if not ok or texto.strip() == "":
            return;
        quantas = janela.painter_widget.buscar(texto);
        if quantas == 0:
            self.statusBar().showMessage("Nada encontrado para \"%s\"" % texto, 5000);
        else:
            self.statusBar().showMessage("%d encontrada(s) e selecionada(s)" % quantas, 5000);

    @Slot()
    def menu_layout(self):
        # Menu na hora do clique, em vez de cinco botoes na barra.
        from PySide6.QtWidgets import QMenu;
        from classlib.relationship import layouts;
        mapa = self.__mapa_ativo__("MapRelationship");
        if mapa == None:
            return;
        menu = QMenu(self);
        escolhido = [None];
        for nome, texto in layouts.LAYOUTS:
            acao = menu.addAction(texto);
            acao.triggered.connect(lambda _=False, n=nome: escolhido.__setitem__(0, n));
        posicao = self._map_tool_bar.mapToGlobal(self._map_tool_bar.rect().bottomLeft());
        menu.exec(posicao);
        if escolhido[0] == None:
            return;
        try:
            quantas = layouts.aplicar(mapa, escolhido[0]);
        except Exception as erro:
            QMessageBox.warning(self, "Layout", str(erro));
            return;
        janela = self.active_mdi_child();
        if janela != None:
            janela.redesenhar();
        self.statusBar().showMessage("Layout %s aplicado a %d caixas (Ctrl+Z desfaz)"
                                     % (layouts.rotulo(escolhido[0]), quantas), 5000);

    @Slot()
    def alternar_lista(self):
        # Desenho <-> tabela, na mesma janela. So o mapa de relacionamento tem lista, e o
        # __mapa_ativo__ ja avisa quando a janela em foco e outra coisa.
        if self.__mapa_ativo__("MapRelationship") == None:
            self._lista_act.setChecked(False);
            return;
        janela = self.active_mdi_child();
        self._lista_act.setChecked( janela.alternar_lista() );

    @Slot()
    def export_diagram(self):
        # Exporta o diagrama ABERTO para arquivo do analista. Vale para os tres tipos (mapa,
        # organograma, timeline), por isso nao restringe a classe. Com o report morto, este e
        # o caminho de a entrega sair do app -- ver SPEC.md §3.2.
        mapa = self.__mapa_ativo__();
        if mapa == None:
            return;
        filtros = "PDF vetorial (*.pdf);;PNG em alta (*.png);;SVG (*.svg)";
        pasta = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation);
        sugestao = os.path.join(pasta, exportar_diagrama.nome_de_arquivo(mapa) + ".pdf");
        caminho, filtro = QFileDialog.getSaveFileName(self, "Exportar diagrama", sugestao, filtros);
        if caminho == None or caminho.strip() == "":
            return;
        formato = "png" if "*.png" in filtro else ("svg" if "*.svg" in filtro else "pdf");
        # Extensao digitada a mao ganha do filtro: quem escreve "mapa.svg" quer SVG.
        extensao = os.path.splitext(caminho)[1].lstrip(".").lower();
        if extensao in exportar_diagrama.FORMATOS:
            formato = extensao;
        try:
            destino = exportar_diagrama.exportar(mapa, caminho, formato=formato);
        except exportar_diagrama.ErroExportacao as erro:
            QMessageBox.warning(self, "Exportar diagrama", str(erro));
            return;
        except Exception as erro:
            QMessageBox.critical(self, "Exportar diagrama",
                                 "Não foi possível exportar: %s" % erro);
            return;
        self.statusBar().showMessage("Diagrama exportado em " + destino, 5000);

    def __mapa_ativo__(self, classe=None):
        # "(x and x).mapa" estoura quando nao ha janela ativa: (None and None) e None, e
        # .mapa em None da AttributeError antes do teste != None adiantar alguma coisa.
        child = self.active_mdi_child();
        if child == None or getattr(child, "mapa", None) == None:
            QMessageBox.information(self, "Mapa", "Abra um mapa antes.");
            return None;
        # Sao tres tipos de diagrama na mesma janela MDI, e quase toda acao da barra so faz
        # sentido so no mapa de relacionamento (Property, Check, Documents, Extrair).
        # Sem esta checagem, com um organograma ou uma timeline em foco a acao estourava
        # AttributeError la dentro do dialogo.
        if classe != None and child.mapa.__class__.__name__ != classe:
            QMessageBox.information(self, "Mapa", "Esta ação vale para o mapa de relacionamento.");
            return None;
        return child.mapa;

    @Slot()
    def map_propert(self):
        buffer = self.__mapa_ativo__("MapRelationship");
        if buffer != None:
            f = DialogRelationshipEdit(self, buffer);
            f.exec();

    @Slot()
    def map_errors(self):
        buffer = self.__mapa_ativo__("MapRelationship");
        if buffer != None:
            f = DialogRelationshipCheck(self, buffer);
            f.exec();
    @Slot()
    def import_data(self):
        f = DialogImport(self);
        f.exec();

    @Slot()
    def open_subtypes(self):
        # Tela global de sub-tipos (nao depende de mapa aberto).
        from view.dialog_subtypes import DialogSubtypes;
        f = DialogSubtypes(self);
        f.exec();

    @Slot()
    def map_extrair(self):
        buffer = self.__mapa_ativo__("MapRelationship");
        if buffer == None:
            return;
        janela = self.active_mdi_child();   # quem sabe redesenhar e o MdiMap, nao o mapa
        # Carrega pelo config.json, como o QBot faz: o bot continua plugavel — trocar o
        # modulo ou a classe e editar o JSON, sem tocar aqui.
        try:
            import json, importlib.util;
            cfg = json.loads( open( CURRENTDIR + "/bot/brazil/entidades/config.json" ).read() );
            spec = importlib.util.spec_from_file_location( cfg["module"], CURRENTDIR + "/" + cfg["path"] );
            modulo = importlib.util.module_from_spec(spec);
            sys.modules[ cfg["module"] ] = modulo;
            spec.loader.exec_module(modulo);
            cls = getattr( modulo, cfg["class"] );
            f = cls(self, buffer);
            f.exec();
            # O bot mexe no modelo sem passar por evento de mouse: sem redesenhar, as
            # caixas novas so aparecem quando algo mais forcar o repaint.
            if janela != None:
                janela.redesenhar();
        except Exception as e:
            import traceback; traceback.print_exc();
            QMessageBox.information(self, "Extrair de URL", str(e));

    @Slot()
    def map_documents(self):
        buffer = self.__mapa_ativo__("MapRelationship");
        if buffer != None:
            # Abrir os documentos e o "eu vi": limpa a marca, senao o "*" ficaria para
            # sempre depois do primeiro report.
            ReportManager.instancia().marcar_visto();
            f = DialogDocument(self, buffer);
            f.exec();

    #@Slot()
    #def save_as(self):
    #    if self.active_mdi_child() and self.active_mdi_child().save_as():
    #        self.statusBar().showMessage("File saved", 2000)

    #@Slot()
    #def cut(self):
    #    if self.active_mdi_child():
    #        self.active_mdi_child().cut()

    #@Slot()
    #def copy(self):
    #    if self.active_mdi_child():
    #        self.active_mdi_child().copy()

    #@Slot()
    #def paste(self):
    #    if self.active_mdi_child():
    #        self.active_mdi_child().paste()

    @Slot()
    def about(self):
        QMessageBox.about(self, "About Relationship", "")

    @Slot()
    def update_menus(self):
        has_mdi_child = (self.active_mdi_child() is not None)
        if self.active_mdi_child() is not None:
            buffer_area = self.active_mdi_child() and self.active_mdi_child();
            # O titulo dizia "Relationship MAP" para qualquer diagrama; com tres tipos isso
            # passou a mentir na cara do usuario.
            prefixos = {"OrganizationChart" : "Organization Chart", "Timeline" : "Timeline"};
            title = prefixos.get( buffer_area.mapa.__class__.__name__, "Relationship MAP" ) + ": " + buffer_area.mapa.getName() ;
            if buffer_area.mapa.getLocked() and len(buffer_area.mapa.lock_list) > 0 :
                title = title + " (ReadOnly at " + buffer_area.mapa.lock_list[-1]["lock_time"] + " ISO DATE)";
            self.setWindowTitle( title )
            # A marca do botao Lista pertence a JANELA, nao a barra: sem isto ele continuaria
            # marcado ao trocar para outro mapa que esta no desenho.
            self._lista_act.setChecked( getattr(buffer_area, "mostrando_lista", lambda: False)() );
            self.__atualizar_desfazer__();

    @Slot()
    def update_window_menu(self):
        self._window_menu.clear()
        self._window_menu.addAction(self._close_act)
        self._window_menu.addAction(self._close_all_act)
        self._window_menu.addSeparator()
        self._window_menu.addAction(self._tile_act)
        self._window_menu.addAction(self._cascade_act)
        self._window_menu.addSeparator()
        self._window_menu.addAction(self._next_act)
        self._window_menu.addAction(self._previous_act)
        self._window_menu.addAction(self._separator_act)

        windows = self._mdi_area.subWindowList()
        self._separator_act.setVisible(len(windows) != 0)

        for i, window in enumerate(windows):
            child = window.widget()

            f = child.user_friendly_current_file()
            text = f'{i + 1} {f}'
            if i < 9:
                text = '&' + text

            action = self._window_menu.addAction(text)
            action.setCheckable(True)
            action.setChecked(child is self.active_mdi_child())
            slot_func = partial(self.set_active_sub_window, window=window)
            action.triggered.connect(slot_func)

    def create_actions(self):

        icon = QIcon.fromTheme(QIcon.ThemeIcon.DocumentNew)
        self._new_act = QAction(icon, "&New", self, shortcut=QKeySequence.New, statusTip="Create a new Map",  triggered=self.new_map)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpen)
        self._open_act = QAction(icon, "&Open...", self,
                                 shortcut=QKeySequence.Open, statusTip="Open an existing map",
                                 triggered=self.open)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.DocumentSave)
        self._save_act = QAction(icon, "&Save", self,
                                 shortcut=QKeySequence.Save,
                                 statusTip="Save the document to disk", triggered=self.save)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.DocumentSaveAs)
        self._export_act = QAction(icon, "Exportar diagrama...", self,
                                 statusTip="Exportar o diagrama aberto para PDF, PNG ou SVG",
                                 triggered=self.export_diagram)

        #self._save_as_act = QAction("Save &As...", self,
        #                            shortcut=QKeySequence.SaveAs,
        #                            statusTip="Save the document under a new name",
        #                            triggered=self.save_as)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.ApplicationExit)
        self._exit_act = QAction(icon, "E&xit", self, shortcut=QKeySequence.Quit,
                                 statusTip="Exit the application",
                                 triggered=QApplication.instance().closeAllWindows)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.DocumentProperties)
        self._map_edit_act = QAction(icon, "Property", self,
                                shortcut=QKeySequence.Cut,
                                statusTip="Edit map property",
                                triggered=self.map_propert)
        #icon = QIcon.fromTheme(QIcon.ThemeIcon.ToolsCheckSpelling)
        icon = QIcon( CURRENTDIR + "/resources/check.png");
        self._map_edit_check = QAction(icon, "Check", self,
                                shortcut=QKeySequence.Cut,
                                statusTip="Check map",
                                triggered=self.map_errors)

        icon = QIcon( CURRENTDIR + "/resources/upload.png");
        self._import_data = QAction(icon, "Import", self,
                                shortcut=QKeySequence.Cut,
                                statusTip="Import",
                                triggered=self.import_data)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.EditFind);
        self._map_extrair = QAction(icon, "Extrair de URL", self,
                                statusTip="Extrair sujeitos e vínculos de uma URL (rolhama)",
                                triggered=self.map_extrair)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.DocumentPrint);
        self._map_documents = QAction(icon, "Documents", self,
                                statusTip="Documentos (PDF) do mapa",
                                triggered=self.map_documents)


        icon = QIcon.fromTheme(QIcon.ThemeIcon.EditUndo)
        self._undo_act = QAction(icon, "Desfazer", self, shortcut=QKeySequence.Undo,
                                statusTip="Desfazer a última alteração do mapa",
                                triggered=self.desfazer)
        icon = QIcon.fromTheme(QIcon.ThemeIcon.EditRedo)
        self._redo_act = QAction(icon, "Refazer", self, shortcut=QKeySequence.Redo,
                                statusTip="Refazer a alteração desfeita",
                                triggered=self.refazer)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.ViewFullscreen)
        self._viewlet_act = QAction(icon, "Vista", self,
                                statusTip="Cor e tamanho das caixas por uma propriedade do mapa",
                                triggered=self.menu_viewlet)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.EditFind)
        self._buscar_act = QAction(icon, "Buscar", self, shortcut=QKeySequence.Find,
                                statusTip="Procurar caixas pelo nome no mapa aberto",
                                triggered=self.buscar_no_mapa)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.ViewRefresh)
        self._layout_act = QAction(icon, "Layout", self,
                                statusTip="Arrumar as caixas automaticamente (um passo de desfazer)",
                                triggered=self.menu_layout)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.FormatJustifyFill);
        self._lista_act = QAction(icon, "Lista", self, checkable=True,
                                statusTip="Ver o mapa em tabela (entidades e vínculos) em vez de desenho",
                                triggered=self.alternar_lista)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.AddressBookNew);
        self._subtypes_act = QAction(icon, "Sub-tipos", self,
                                statusTip="Editar sub-tipos válidos (global) e seus rostos default",
                                triggered=self.open_subtypes)


        #icon = QIcon.fromTheme(QIcon.ThemeIcon.EditCopy)
        #self._copy_act = QAction(icon, "&Copy", self,
        #                         shortcut=QKeySequence.Copy,
        #                         statusTip="Copy the current selection's contents to the clipboard",
        #                         triggered=self.copy)

        #icon = QIcon.fromTheme(QIcon.ThemeIcon.EditPaste)
        #self._paste_act = QAction(icon, "&Paste", self,
        #                          shortcut=QKeySequence.Paste,
        #                          statusTip="Paste the clipboard's contents into the current "
        #                                    "selection",
        #                          triggered=self.paste)

        self._close_act = QAction("Cl&ose", self,
                                  statusTip="Close the active window",
                                  triggered=self._mdi_area.closeActiveSubWindow)

        self._close_all_act = QAction("Close &All", self,
                                      statusTip="Close all the windows",
                                      triggered=self._mdi_area.closeAllSubWindows)

        self._tile_act = QAction("&Tile", self, statusTip="Tile the windows",
                                 triggered=self._mdi_area.tileSubWindows)

        self._cascade_act = QAction("&Cascade", self,
                                    statusTip="Cascade the windows",
                                    triggered=self._mdi_area.cascadeSubWindows)

        self._next_act = QAction("Ne&xt", self, shortcut=QKeySequence.NextChild,
                                 statusTip="Move the focus to the next window",
                                 triggered=self._mdi_area.activateNextSubWindow)

        self._previous_act = QAction("Pre&vious", self,
                                     shortcut=QKeySequence.PreviousChild,
                                     statusTip="Move the focus to the previous window",
                                     triggered=self._mdi_area.activatePreviousSubWindow)

        self._separator_act = QAction(self)
        self._separator_act.setSeparator(True)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.HelpAbout)
        self._about_act = QAction(icon, "&About", self,
                                  statusTip="Show the application's About box",
                                  triggered=self.about)

        self._about_qt_act = QAction("About &Qt", self,
                                     statusTip="Show the Qt library's About box",
                                     triggered=QApplication.instance().aboutQt)

    def create_menus(self):
        self._file_menu = self.menuBar().addMenu("&File")
        self._file_menu.addAction(self._new_act)
        self._file_menu.addAction(self._open_act)
        self._file_menu.addAction(self._save_act)
        self._file_menu.addAction(self._export_act)
        #self._file_menu.addAction(self._save_as_act)
        self._file_menu.addSeparator()
        self._file_menu.addAction(self._subtypes_act)
        action = self._file_menu.addAction("Switch layout direction")
        action.triggered.connect(self.switch_layout_direction)
        self._file_menu.addAction(self._exit_act)

        #self._edit_menu = self.menuBar().addMenu("&Edit")
        #self._edit_menu.addAction(self._cut_act)
        #self._edit_menu.addAction(self._copy_act)
        #self._edit_menu.addAction(self._paste_act)

        self._window_menu = self.menuBar().addMenu("&Window")
        self.update_window_menu()
        self._window_menu.aboutToShow.connect(self.update_window_menu)

        self.menuBar().addSeparator()

        self._help_menu = self.menuBar().addMenu("&Help")
        self._help_menu.addAction(self._about_act)
        self._help_menu.addAction(self._about_qt_act)

        #self._file_menu.setEnabled(False);
        #self._window_menu.setEnabled(False);
        #self._edit_menu.setEnabled(False);
        #self._help_menu.setEnabled(False);

    def create_tool_bars(self):
        self._file_tool_bar = self.addToolBar("File")
        self._file_tool_bar.addAction(self._new_act)
        self._file_tool_bar.addAction(self._open_act)
        self._file_tool_bar.addAction(self._save_act)
        self._file_tool_bar.addAction(self._export_act)
        self._map_tool_bar = self.addToolBar("Map")
        # Sem isto o QToolBar desenha SO o icone e o texto da acao — que e onde a marca de
        # "gerando" e "terminou" aparece — fica invisivel.
        self._map_tool_bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);
        self._map_tool_bar.addAction(self._undo_act);
        self._map_tool_bar.addAction(self._redo_act);
        self._map_tool_bar.addSeparator();
        self._map_tool_bar.addAction(self._map_edit_act);
        self._map_tool_bar.addAction(self._map_edit_check);
        self._map_tool_bar.addAction(self._import_data);
        self._map_tool_bar.addAction(self._map_documents);
        self._map_tool_bar.addAction(self._map_extrair);
        self._map_tool_bar.addAction(self._viewlet_act);
        self._map_tool_bar.addAction(self._buscar_act);
        self._map_tool_bar.addAction(self._layout_act);
        self._map_tool_bar.addAction(self._lista_act);
        self._map_tool_bar.addAction(self._subtypes_act);
        #self._edit_tool_bar.addAction(self._copy_act)
        #self._edit_tool_bar.addAction(self._paste_act)
        #self._file_tool_bar.setEnabled(False);
        #self._edit_tool_bar.setEnabled(False);

    def create_status_bar(self):
        self.statusBar().showMessage("Ready")

    def read_settings(self):
        settings = QSettings('QtProject', 'CML')
        geometry = settings.value('geometry', QByteArray())
        if geometry.size():
            self.restoreGeometry(geometry)

    def write_settings(self):
        settings = QSettings('QtProject', 'CML')
        settings.setValue('geometry', self.saveGeometry())

    def active_mdi_child(self):
        active_sub_window = self._mdi_area.activeSubWindow()
        if active_sub_window:
            return active_sub_window.widget()
        return None

    def find_mdi_child(self, fileName):
        canonical_file_path = QFileInfo(fileName).canonicalFilePath()

        for window in self._mdi_area.subWindowList():
            if window.widget().current_file() == canonical_file_path:
                return window
        return None

    @Slot()
    def switch_layout_direction(self):
        if self.layoutDirection() == Qt.LeftToRight:
            QApplication.setLayoutDirection(Qt.RightToLeft)
        else:
            QApplication.setLayoutDirection(Qt.LeftToRight)

    def set_active_sub_window(self, window):
        if window:
            self._mdi_area.setActiveSubWindow(window)


if __name__ == '__main__':
    argument_parser = ArgumentParser(description='CML',
                                     formatter_class=RawTextHelpFormatter)
    argument_parser.add_argument("files", help="Files",
                                 nargs='*', type=str)
    options = argument_parser.parse_args()

    app = QApplication(sys.argv)

    icon_paths = QIcon.themeSearchPaths()
    QIcon.setThemeSearchPaths(icon_paths + [":/qt-project.org/icons"])
    QIcon.setFallbackThemeName("example_icons")

    dlg = DialogConnect();
    dlg.exec(); 
    server = Server();
    if server.status:
        main_win = MainWindow()
        #for f in options.files:
        #    main_win.load(f)
        main_win.show()
        sys.exit(app.exec())
    else:
        sys.exit(0);