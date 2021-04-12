import sys
from PySide2 import QtWidgets
from textureimporter import importer_dialog


def run():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    main_window = next(w for w in app.topLevelWidgets() if w.objectName() == 'MayaWindow')
    dialog = importer_dialog.ImporterDialog(main_window, dcc='maya')
    dialog.show()
    return main_window
