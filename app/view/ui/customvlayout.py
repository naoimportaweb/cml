

from PySide6.QtWidgets import QVBoxLayout, QWidget

class CustomVLayout(QVBoxLayout):
    def __init__(self):
        super().__init__();
        self.layouts = {};
    
    def addLayout(self, name, layout):
        widget1 = QWidget();
        widget1.setLayout(   layout );
        self.addWidget(      widget1 );
        self.layouts[ name ] =  widget1 ;

    def __enable_disable__(self, name, active):
        self.layouts[ name ].setVisible( active );
    def disable(self, name):
        self.__enable_disable__(name, False);
    def enable(self, name):
        self.__enable_disable__(name, True);
