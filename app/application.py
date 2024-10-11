# Copyright (C) 2013 Riverbank Computing Limited.
# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause

"""PySide6 port of the widgets/mainwindows/mdi example from Qt v5.x, originating from PyQt"""
import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));

sys.path.append(CURRENTDIR);

from argparse import ArgumentParser, RawTextHelpFormatter
from functools import partial


from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow,
                               QMdiArea, QMessageBox, QTextEdit)
import PySide6.QtExampleIcons  # noqa: F401

from view.mdimap import MdiMap;
from view.dialog_relationship import DialogRelationship;
from view.dialog_diagram_choice import DialogDiagramChoice;
from view.dialog_relationship_load import DialogRelationshipLoad;
from view.dialog_relationship_edit import DialogRelationshipEdit
from view.dialogconnect import DialogConnect;
from classlib.server import Server;

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
        #child = self.create_mdi_map()
        #child.new_map()
        #child.showMaximized();

    @Slot()
    def open(self):
        f = DialogRelationshipLoad(self);
        f.exec();
        child = MdiMap(self, f.map)
        self._mdi_area.addSubWindow(child);
        child.new_map()
        child.showMaximized();

    def load(self, file_name):
        child = self.create_mdi_map()
        if child.load_file(file_name):
            self.statusBar().showMessage("File loaded", 2000)
            child.show()
        else:
            child.close()

    @Slot()
    def save(self):
        self.active_mdi_child() and self.active_mdi_child().save();
        #if self.active_mdi_child() and self.active_mdi_child().save():
        #    self.statusBar().showMessage("File saved", 2000)

    @Slot()
    def map_propert(self):
        buffer = (self.active_mdi_child() and self.active_mdi_child()).mapa;
        if buffer != None:
            f = DialogRelationshipEdit(self, buffer);
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
            title = "Relationship MAP: " + buffer_area.mapa.name ;
            if buffer_area.mapa.locked and len(buffer_area.mapa.lock_list) > 0 :
                title = title + " (ReadOnly at " + buffer_area.mapa.lock_list[-1]["lock_time"] + " ISO DATE)";
            self.setWindowTitle( title )
        #self._save_act.setEnabled(has_mdi_child)
        #self._save_as_act.setEnabled(has_mdi_child)
        #self._paste_act.setEnabled(has_mdi_child)
        #self._close_act.setEnabled(has_mdi_child)
        #self._close_all_act.setEnabled(has_mdi_child)
        #self._tile_act.setEnabled(has_mdi_child)
        #self._cascade_act.setEnabled(has_mdi_child)
        #self._next_act.setEnabled(has_mdi_child)
        #self._previous_act.setEnabled(has_mdi_child)
        #self._separator_act.setVisible(has_mdi_child)
        #has_selection = (self.active_mdi_child() is not None
        #                 and self.active_mdi_child().textCursor().hasSelection())
        #self._cut_act.setEnabled(has_selection)
        #self._copy_act.setEnabled(has_selection)

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

    def create_mdi_map(self):
        f = DialogRelationship(self);
        f.exec();
        if f.map != None:
            child = MdiMap(self, f.map)
            self._mdi_area.addSubWindow(child);

        return child

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
        #self._file_menu.addAction(self._save_as_act)
        self._file_menu.addSeparator()
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
        self._map_tool_bar = self.addToolBar("Map")
        self._map_tool_bar.addAction(self._map_edit_act)
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
    argument_parser = ArgumentParser(description='MDI Example',
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