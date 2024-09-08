
class MainWindow(QMainWindow):
    """An Application example to draw using a pen """

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)

        self.painter_widget = PainterWidget()
        self.bar = self.addToolBar("Menu")
        self.bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._save_action = self.bar.addAction(
            qApp.style().standardIcon(QStyle.SP_DialogSaveButton),  # noqa: F821
            "Save", self.on_save
        )
        self._save_action.setShortcut(QKeySequence.Save)
        self._open_action = self.bar.addAction(
            qApp.style().standardIcon(QStyle.SP_DialogOpenButton),  # noqa: F821
            "Open", self.on_open
        )
        self._open_action.setShortcut(QKeySequence.Open)
        self.bar.addAction(
            qApp.style().standardIcon(QStyle.SP_DialogResetButton),  # noqa: F821
            "Clear",
            self.painter_widget.clear,
        )
        self.bar.addSeparator()

        self.color_action = QAction(self)
        self.color_action.triggered.connect(self.on_color_clicked)
        self.bar.addAction(self.color_action)

        self.setCentralWidget(self.painter_widget)

        self.color = Qt.black
        self.set_color(self.color)

        self.mime_type_filters = ["image/png", "image/jpeg"]

    @Slot()
    def on_save(self):

        dialog = QFileDialog(self, "Save File")
        dialog.setMimeTypeFilters(self.mime_type_filters)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setDefaultSuffix("png")
        dialog.setDirectory(
            QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        )

        if dialog.exec() == QFileDialog.Accepted:
            if dialog.selectedFiles():
                self.painter_widget.save(dialog.selectedFiles()[0])

    @Slot()
    def on_open(self):

        dialog = QFileDialog(self, "Save File")
        dialog.setMimeTypeFilters(self.mime_type_filters)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setDefaultSuffix("png")
        dialog.setDirectory(
            QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        )

        if dialog.exec() == QFileDialog.Accepted:
            if dialog.selectedFiles():
                self.painter_widget.load(dialog.selectedFiles()[0])

    @Slot()
    def on_color_clicked(self):

        color = QColorDialog.getColor(self.color, self)

        if color:
            self.set_color(color)

    def set_color(self, color: QColor = Qt.black):

        self.color = color
        # Create color icon
        pix_icon = QPixmap(32, 32)
        pix_icon.fill(self.color)

        self.color_action.setIcon(QIcon(pix_icon))
        self.painter_widget.pen.setColor(self.color)
        self.color_action.setText(QColor(self.color).name())


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = MainWindow()
    w.show()
    sys.exit(app.exec())