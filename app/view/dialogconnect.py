
from PySide6.QtCore import (QByteArray, QFile, QFileInfo, QSettings,
                            QSaveFile, QTextStream, Qt, Slot)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow,
                               QMdiArea, QMessageBox, QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton)

class DialogConnect(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Connect")
        self.ui_register();
        self.conectado = False;

    def ui_login(self):
        self.layout_login = QGridLayout()
        self.layout_login.setContentsMargins(20, 20, 20, 20)
        self.layout_login.setSpacing(10)
        self.setWindowTitle("CodersLegacy")
        self.setLayout(self.layout_login)

        # Username Label and Input
        user = QLabel("Username:")
        user.setProperty("class", "normal")
        self.layout_login.addWidget(user, 1, 0)
        self.input1 = QLineEdit()
        self.layout_login.addWidget(self.input1, 1, 1, 1, 2)

        # Password Label and Input
        pwd = QLabel("Password")
        pwd.setProperty("class", "normal")
        self.layout_login.addWidget(pwd, 2, 0)
        self.input2 = QLineEdit()
        self.input2.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout_login.addWidget(self.input2, 2, 1, 1, 2)

        # Register and Login Buttons
        button1 = QPushButton("Register")
        self.layout_login.addWidget(button1, 4, 1)

        button2 = QPushButton("Login")
        button2.clicked.connect(self.login)
        self.layout_login.addWidget(button2, 4, 2)

    def ui_register(self):
        self.layout_register = QGridLayout()
        self.layout_register.setContentsMargins(20, 20, 20, 20)
        self.layout_register.setSpacing(10)
        self.setWindowTitle("CodersLegacy")
        self.setLayout(self.layout_register)

        # Username Label and Input
        user = QLabel("Username:")
        user.setProperty("class", "normal")
        self.layout_register.addWidget(user, 1, 0)
        self.input1 = QLineEdit()
        self.layout_register.addWidget(self.input1, 1, 1, 1, 2)

        # Password Label and Input
        pwd = QLabel("Password")
        pwd.setProperty("class", "normal")
        self.layout_register.addWidget(pwd, 2, 0)
        self.input2 = QLineEdit()
        self.input2.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout_register.addWidget(self.input2, 2, 1, 1, 2)

        # Password Label and Input
        pwd1 = QLabel("Password")
        pwd1.setProperty("class", "normal")
        self.layout_register.addWidget(pwd1, 3, 0)
        self.input3 = QLineEdit()
        self.input3.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout_register.addWidget(self.input3, 3, 1, 1, 2)

        # Password Label and Input
        mail = QLabel("E-mail")
        mail.setProperty("class", "normal")
        self.layout_register.addWidget(mail, 4, 0)
        self.input4 = QLineEdit()
        self.input4.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout_register.addWidget(self.input4, 4, 1, 1, 2)

        # Register and Login Buttons
        button1 = QPushButton("Register")
        self.layout_register.addWidget(button1, 6, 1)

        #self.layout_register.addStretch();

    def login(self):
        print();




        #QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        #self.buttonBox = QDialogButtonBox(QBtn)
        #self.buttonBox.accepted.connect(self.accept)
        #self.buttonBox.rejected.connect(self.reject)
        #self.layout = QVBoxLayout()
        #message = QLabel("")
        #self.layout.addWidget(message)
        #self.layout.addWidget(self.buttonBox)
        #self.setLayout(self.layout)