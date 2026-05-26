import os, sys, inspect, requests, re;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QHeaderView, QTableWidgetItem, QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)
from bs4 import BeautifulSoup;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(os.path.dirname(os.path.dirname( CURRENTDIR )));
sys.path.append( ROOT );

from view.ui.customvlayout import CustomVLayout;
from classlib.configuration import Configuration;

class DialogBotWikipedia(QDialog):
    def __init__(self, parent, entity):
        super().__init__(parent);
        if parent != None:
            nWidth = 800;
            nHeight = 600;
            self.setGeometry(parent.x() + parent.width()/2 - nWidth/2, parent.y() + parent.height()/2 - nHeight/2, 600, 500);
        self.entity = entity;
        self.txt = QTextEdit();
        self.txt.setFont( Configuration.instancia().getFont() );
        self.txt.setLineWrapMode(QTextEdit.NoWrap);
        self.txt.setLineWrapMode(QTextEdit.WidgetWidth);  
        layout = QGridLayout();
        layout.addWidget( self.txt );
        self.setLayout( layout );
        self.execute( self.entity.wikipedia );
    
    def clear(self, text):
        text = re.sub(r'\[\d*\]', "", text) ;
        text = re.sub(r'\((.*?)\d+\s*\,\s*\d+\s*\)', "", text) ;
        return text;

    def execute(self, url):
        page = requests.get( url );
        soup = BeautifulSoup(page.content, 'html.parser');
        html = soup.prettify();
        divs = soup.find_all("div", {"class": "mw-content-ltr"})
        final_text = "";
        for div in divs:
            ps = div.find_all('p');
            for p in ps:
                if p.text.strip() == "":
                    continue;
                final_text += self.clear(p.text) + "\r\n" ;
        self.txt.setPlainText( final_text  );
        return;
