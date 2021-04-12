import os
import sys
from PySide2 import QtUiTools, QtWidgets
import logging


def load_ui(parent, file_name):
    loader = QtUiTools.QUiLoader()
    ui_path = os.path.join(os.path.dirname(__file__), 'ui', file_name)
    widget = loader.load(ui_path)
    parent.setLayout(widget.layout())
    parent.__dict__.update(widget.__dict__)


def show(cls):
    app = QtWidgets.QApplication(sys.argv)
    dialog = cls()
    dialog.show()
    sys.exit(app.exec_())
