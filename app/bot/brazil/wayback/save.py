import os, sys, inspect, requests, re, traceback;
import threading

from PySide6.QtCore import (QSettings, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QHeaderView, QTableWidgetItem, QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

from waybackpy import WaybackMachineSaveAPI
from waybackpy import WaybackMachineAvailabilityAPI

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname(os.path.dirname(os.path.dirname( CURRENTDIR )));
sys.path.append( ROOT );

from classlib.configuration import Configuration;

class DialogWayback(QDialog):
    def __init__(self, parent, reference):
        super().__init__(parent);
        if parent != None:
            nWidth = 800;
            nHeight = 600;
            self.setGeometry(parent.x() + parent.width()/2 - nWidth/2, parent.y() + parent.height()/2 - nHeight/2, 600, 500);
        self.reference = reference;
        self.txt = QTextEdit();
        self.txt.setFont( Configuration.instancia().getFont() );
        self.txt.setLineWrapMode(QTextEdit.NoWrap);
        self.txt.setLineWrapMode(QTextEdit.WidgetWidth);  
        self.waybackmachine_url = "";
        self.btn = QPushButton("Start")
        self.btn.clicked.connect(self.btn_click)
        layout = QGridLayout();
        layout.addWidget( self.txt );
        layout.addWidget( self.btn );
        self.setLayout( layout );
        
    def btn_click(self):
        if not self.reference.hasWaybackMachine():
            self.waybackmachine_url = self.execute( self.reference.getUrl() );
            self.txt.setPlainText( self.waybackmachine_url );
        else:
            self.txt.setPlainText( "Reference already has a link to Wayback Machine." );
    
    def consult(self, url, user_agent):
        try:
            availability_api = WaybackMachineAvailabilityAPI(url, user_agent);
            return str(availability_api.newest());
        except:
            return "";

    def execute(self, url):
        user_agent = "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0";
        try:
            self.btn.setText("Wait...");
            self.waybackmachine_url = self.consult(url, user_agent);
            if self.waybackmachine_url ==  "":
                save_api = WaybackMachineSaveAPI(url, user_agent);
                return save_api.save();
            else:
                return self.waybackmachine_url;
        except Exception:
            return traceback.format_exc();
        finally:
            self.btn.setText("Start");
        






