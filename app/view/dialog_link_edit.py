import os, sys, inspect;

from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings, QDate, QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QDateEdit, QComboBox, QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
ROOT = os.path.dirname( CURRENTDIR );
sys.path.append( ROOT );

from view.ui.customvlayout import CustomVLayout;
from view.dialogentityload import DialogEntityLoad;

class DialogLinkEdit(QDialog):
    def __init__(self, form, link):
        super().__init__(form)
        self.link = link;
        self.resize(600, 600);
        self.layout_principal = CustomVLayout();
        self.setLayout( self.layout_principal );
        self.btn_start_date_enable = QPushButton("Disable");
        self.btn_end_date_enable = QPushButton("Disable");
        self.start_date_flag = True;
        self.end_date_flag = True;
        self.btn_start_date_enable.setFocusPolicy(Qt.NoFocus);
        self.btn_end_date_enable.setFocusPolicy(Qt.NoFocus);
        self.btn_start_date_enable.clicked.connect(self.btn_start_date_enable_click);
        self.btn_end_date_enable.clicked.connect(self.btn_end_date_enable_click);
        self.start_date = QDateEdit(self);
        self.end_date =   QDateEdit(self);
        self.start_date.setDate(QDate.fromString( self.link.start_date, "yyyy-MM-dd" ));
        self.end_date.setDate(QDate.fromString( self.link.end_date    , "yyyy-MM-dd" ));
        self.start_date.setDisplayFormat(self.link.format_date);
        self.end_date.setDisplayFormat(self.link.format_date);
        lbl_start_date = QLabel("Start Date");
        lbl_end_date = QLabel("End Date");
        CustomVLayout.widget_linha(self, self.layout_principal, [lbl_start_date, self.start_date, self.btn_start_date_enable] );
        CustomVLayout.widget_linha(self, self.layout_principal, [lbl_end_date, self.end_date, self.btn_end_date_enable] );
        self.combo_format_date = QComboBox();
        self.combo_format_date.addItem("yyyy-MM-dd");
        self.combo_format_date.addItem("yyyy-MM");
        self.combo_format_date.addItem("yyyy");
        self.combo_format_date.currentTextChanged.connect(self.combo_format_date_changed)
        index = self.combo_format_date.findText(self.link.format_date, Qt.MatchFixedString)
        if index >= 0:
             self.combo_format_date.setCurrentIndex(index)
        CustomVLayout.widget_linha(self, self.layout_principal, [self.combo_format_date] );

        if self.link.start_date == None:
            self.start_date.setVisible(False);
            self.start_date_flag = False;
            self.btn_start_date_enable.setText("Enable");
        if self.link.end_date == None:
            self.end_date.setVisible(False);
            self.end_date_flag = False;
            self.btn_end_date_enable.setText("Enable");

        self.btn_save = QPushButton("Save");
        self.btn_save.setFocusPolicy(Qt.NoFocus);
        self.btn_save.clicked.connect(self.btn_save_click);
        CustomVLayout.widget_linha(self, self.layout_principal, [ self.btn_save] );
        self.ok = False;

    def btn_start_date_enable_click(self):
        if self.start_date_flag:
            self.start_date_flag = False;
            self.start_date.setVisible(False);
            self.btn_start_date_enable.setText("Enable");
        else:
            self.start_date_flag = True;
            self.start_date.setVisible(True);
            self.btn_start_date_enable.setText("Disable");

    def btn_end_date_enable_click(self):
        if self.end_date_flag:
            self.end_date_flag = False;
            self.end_date.setVisible(False);
            self.btn_end_date_enable.setText("Enable");
        else:
            self.end_date_flag = True;
            self.end_date.setVisible(True);
            self.btn_end_date_enable.setText("Disable");
    
    def btn_save_click(self):
        self.link.start_date = None;
        self.link.end_date = None;
        if self.start_date_flag:
            self.link.start_date = self.start_date.date().toString("yyyy-MM-dd");
        if self.end_date_flag:
            self.link.end_date =   self.end_date.date().toString("yyyy-MM-dd");
        self.link.format_date = self.combo_format_date.currentText();
        self.ok = True;
        self.close();
    
    def combo_format_date_changed(self):
        self.start_date.setDisplayFormat(self.combo_format_date.currentText());
        self.end_date.setDisplayFormat(self.combo_format_date.currentText());