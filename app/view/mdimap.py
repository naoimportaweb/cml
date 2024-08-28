

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow,
                               QMdiArea, QMessageBox, QTextEdit)

class MdiMap(QTextEdit):
    sequence_number = 1

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self._is_untitled = True

    def new_map(self):
        self._is_untitled = True
        self._cur_file = f"document{MdiMap.sequence_number}.txt"
        MdiMap.sequence_number += 1
        self.setWindowTitle(f"{self._cur_file}[*]")
        self.document().contentsChanged.connect(self.document_was_modified)

    def load_file(self, fileName):
        file = QFile(fileName)
        if not file.open(QFile.ReadOnly | QFile.Text):
            reason = file.errorString()
            message = f"Cannot read file {fileName}:\n{reason}."
            QMessageBox.warning(self, "MDI", message)
            return False
        instr = QTextStream(file)
        with QApplication.setOverrideCursor(Qt.WaitCursor):
            self.setPlainText(instr.readAll())
        self.set_current_file(fileName)
        self.document().contentsChanged.connect(self.document_was_modified)
        return True

    def save(self):
        if self._is_untitled:
            return self.save_as()
        else:
            return self.save_file(self._cur_file)

    def save_as(self):
        fileName, _ = QFileDialog.getSaveFileName(self, "Save As", self._cur_file)
        if not fileName:
            return False
        return self.save_file(fileName)

    def save_file(self, fileName):
        error = None
        with QApplication.setOverrideCursor(Qt.WaitCursor):
            file = QSaveFile(fileName)
            if file.open(QFile.WriteOnly | QFile.Text):
                outstr = QTextStream(file)
                outstr << self.toPlainText()
                if not file.commit():
                    reason = file.errorString()
                    error = f"Cannot write file {fileName}:\n{reason}."
            else:
                reason = file.errorString()
                error = f"Cannot open file {fileName}:\n{reason}."

        if error:
            QMessageBox.warning(self, "MDI", error)
            return False

        self.set_current_file(fileName)
        return True

    def user_friendly_current_file(self):
        return self.stripped_name(self._cur_file)

    def current_file(self):
        return self._cur_file

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def document_was_modified(self):
        self.setWindowModified(self.document().isModified())

    def maybe_save(self):
        if self.document().isModified():
            f = self.user_friendly_current_file()
            message = f"'{f}' has been modified.\nDo you want to save your changes?"
            ret = QMessageBox.warning(self, "MDI", message,
                                      QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if ret == QMessageBox.Save:
                return self.save()
            if ret == QMessageBox.Cancel:
                return False
        return True

    def set_current_file(self, fileName):
        self._cur_file = QFileInfo(fileName).canonicalFilePath()
        self._is_untitled = False
        self.document().setModified(False)
        self.setWindowModified(False)
        self.setWindowTitle(f"{self.user_friendly_current_file()}[*]")

    def stripped_name(self, fullFileName):
        return QFileInfo(fullFileName).fileName()
