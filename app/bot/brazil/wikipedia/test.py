import os, sys, inspect, requests, re;
import importlib

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QHeaderView, QTableWidgetItem, QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)
from bs4 import BeautifulSoup;



class EntityTest():
    def __init__(self):
        self.wikipedia = "https://en.wikipedia.org/wiki/Glenn_Greenwald";
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My App")
        f = self.instance( "wikipedia" ,"/home/well/desenv/cml/app/bot/brazil/wikipedia/search.py", "DialogBotWikipedia", EntityTest() );
        f.exec();

    def instance(self, module_name, path_module, class_name, obj_parameter):
        spec = importlib.util.spec_from_file_location(module_name, path_module)
        module = importlib.util.module_from_spec(spec);
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        cls = getattr(module, class_name)
        inst = cls(self, obj_parameter)
        return inst

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
    