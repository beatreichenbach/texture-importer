import os
import re
import glob
import logging

from PySide2 import QtWidgets, QtCore, QtGui

import importer
import networks_dialog
from gui_utils import show, load_ui
import plugin_utils
import utils


class ImporterDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, dcc=''):
        super(ImporterDialog, self).__init__(parent)

        self.setObjectName('ImporterDialog')
        self.dcc = dcc
        self.settings = utils.Settings()

        self.load_config_files()

        self.init_ui()
        self._connect_ui()

        self.update_config_cmb()
        self.load_settings()

    def init_ui(self):
        load_ui(self, 'importer_dialog.ui')

        self.list_widget = ListWidget(widget=ChannelItem)
        self.list_widget.item_changed.connect(self.connect_item)

        self.config_lay.insertWidget(self.config_lay.count() - 1, self.list_widget)

        # load renderers
        for renderer in plugin_utils.render_plugins(self.dcc).keys():
            self.renderer_cmb.addItem(renderer.title(), renderer)

        menu = QtWidgets.QMenu(self)
        action = menu.addAction('New...')
        action.triggered.connect(self.new_config)

        action = menu.addAction('Save')
        action.triggered.connect(self.save_config)
        self.config_btn.setDefaultAction(action)

        action = menu.addAction('Save As...')
        action.triggered.connect(self.save_config_as)

        action = menu.addAction('Rename...')
        action.triggered.connect(self.rename_config)

        action = menu.addAction('Delete')
        action.triggered.connect(self.delete_config)

        self.config_btn.setMenu(menu)

        menu_bar = QtWidgets.QMenuBar(self)
        menu = QtWidgets.QMenu('File')
        action = menu.addAction('Import Config')
        action.triggered.connect(self.import_config)

        action = menu.addAction('Edit Configs')
        action.triggered.connect(self.edit_configs)
        menu_bar.addMenu(menu)

        menu = QtWidgets.QMenu('Settings')
        action = menu.addAction('Edit Settings')
        action.triggered.connect(self.edit_settings)

        action = menu.addAction('Reset Settings')
        action.triggered.connect(self.reset_settings)
        menu_bar.addMenu(menu)

        menu = QtWidgets.QMenu('Help')
        menu.addAction('Documentation')
        menu.addAction('About')
        menu.addAction('Check for Updates')
        menu_bar.addMenu(menu)

        self.layout().setMenuBar(menu_bar)

        self.main_prgbar.setVisible(False)

    def _connect_ui(self):
        self.config_cmb.currentTextChanged.connect(self.config_changed)

        self.path_browse_btn.clicked.connect(self.browse_path)

        self.main_btnbox.accepted.connect(self.accept)
        self.main_btnbox.rejected.connect(self.reject)

    def connect_item(self, item):
        item.widget.attribute_cmb.currentIndexChanged.connect(self.lock_channels)
        self.lock_channels()

    def lock_channels(self):
        used_channels = []
        for item in self.list_widget.items():
            attribute_cmb = item.widget.attribute_cmb
            if attribute_cmb.currentIndex() in used_channels:
                attribute_cmb.setCurrentIndex(-1)
            else:
                used_channels.append(attribute_cmb.currentIndex())

        for item in self.list_widget.items():
            attribute_cmb = item.widget.attribute_cmb
            for i in range(attribute_cmb.count()):
                cmb_item = attribute_cmb.model().item(i)
                cmb_item.setEnabled(i not in used_channels)

    def config_changed(self, text):
        logging.debug(('config_changed', text))
        self.load_config(text)

    def new_config(self):
        name, result = QtWidgets.QInputDialog.getText(self, 'New Config', 'Config:', text='New Config')
        if result:
            while name in self._configs.keys():
                m = re.search(r'\d+$', name)
                name = re.sub(r'\d+$', lambda m: str(int(m.group()) + 1), name) if m else name + '1'

            config = utils.Config(name)
            self.config_cmb.insertItem(0, name, config)
            self.config_cmb.setCurrentIndex(0)
            self.list_widget.clear()

            self.save_config(name)

    def save_config(self, name=''):
        if not name:
            name = self.config_cmb.currentText()
            if not name:
                self.save_config_as()

        # Update config object
        config = self.config_cmb.itemData(self.config_cmb.findText(name))
        config.name = name
        config.renderer = self.renderer_cmb.currentData()
        config.channels = []
        for item in self.list_widget.items():
            channel = utils.ConfigChannel(
                attribute=item.widget.attribute_cmb.currentText(),
                pattern=item.widget.pattern_line.text(),
                colorspace=item.widget.colorspace_cmb.currentText())
            config.channels.append(channel)

        self._configs[name] = config

        self.update_config_cmb()
        self.config_cmb.setCurrentIndex(self.config_cmb.findText(name))

        self.save_config_files()

    def save_config_as(self):
        name, result = QtWidgets.QInputDialog.getText(self, 'Save As...', 'Config:')
        if result:
            self.save_config(name)

    def rename_config(self):
        name, result = QtWidgets.QInputDialog.getText(self, 'Rename Config', 'Config:', text=self.config_cmb.currentText())
        if result:
            del self._configs[self.config_cmb.currentText()]
            self.save_config(name)

    def delete_config(self):
        name = self.config_cmb.currentText()
        del self._configs[name]
        os.remove(os.path.join(self.settings.configs_path, '{}.json'.format(name)))
        self.update_config_cmb()

    def reset_config(self):
        self.renderer_cmb.setCurrentIndex(0)
        self.list_widget.clear()

    def load_config(self, name):
        logging.debug('load_config')
        config = self._configs.get(name)
        if not config:
            return

        self.reset_config()

        logging.debug(name)
        self.renderer_cmb.setCurrentText(config.renderer)
        for channel in config.channels:
            item = self.list_widget.add_item()
            item.widget.attribute_cmb.setCurrentText(channel.attribute)
            item.widget.pattern_line.setText(channel.pattern)
            item.widget.colorspace_cmb.setCurrentText(channel.colorspace)

    def update_config_cmb(self):
        self.config_cmb.blockSignals(True)
        self.config_cmb.clear()
        name = ''
        for name, config in utils.sorted_dict(self._configs.items()):
            self.config_cmb.addItem(config.name, config)
        self.config_cmb.setCurrentText(name)
        self.config_cmb.blockSignals(False)
        self.config_changed(name)

    def save_config_files(self):
        for name, config in self._configs.items():
            path = os.path.join(self.settings.configs_path, '{}.json'.format(name))
            config.to_json(path)

    def load_config_files(self):
        # handle broken ass json files
        self._configs = {}
        for path in glob.glob(os.path.join(self.settings.configs_path, '*.json')):
            config = utils.Config.from_json(path)
            self._configs[config.name] = config

    def browse_path(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(dir=self.path_cmb.currentText())

        if path:
            self.path_cmb.setCurrentText(path)
            recent = self.settings.list('importer/recent_paths')

            if path in recent:
                del recent[recent.index(path)]
                self.path_cmb.removeItem(self.path_cmb.findText(path))

            recent.insert(0, path)
            self.settings.setValue('importer/recent_paths', recent[:9])
            self.path_cmb.insertItem(0, path)
            self.path_cmb.setCurrentIndex(0)

    def accept(self):
        self.save_config()
        self.save_settings()

        path = self.path_cmb.currentText()
        config = self.config_cmb.currentData()
        include_subfolders = self.subfolders_chk.isChecked()

        importer_ = importer.Importer.from_plugin(self.dcc, config.renderer)
        networks = importer_.get_networks(path, config, include_subfolders)
        if not networks:
            QtWidgets.QMessageBox.information(
                self,
                'Nothing to Import',
                'There were no textures found to import with the current config.',
                QtWidgets.QMessageBox.Ok)
            return

        dialog = networks_dialog.NetworksDialog(self)
        dialog.populate(networks)
        dialog.setModal(True)
        result = dialog.exec_()

        if result:
            super(ImporterDialog, self).accept()

    def reject(self):
        self.save_settings()
        super(ImporterDialog, self).reject()

    def closeEvent(self, event):
        logging.debug('closeEvent')
        self.save_settings()

    def save_settings(self):
        logging.debug('save_settings')
        self.settings.setValue('importer_dialog/pos', self.pos())
        self.settings.setValue('importer_dialog/size', self.size())
        self.settings.setValue('importer/current_config', self.config_cmb.currentText())
        self.settings.setValue('importer/include_subfolders', self.subfolders_chk.isChecked())

    def load_settings(self):
        logging.debug('load_settings')
        if self.settings.value('importer_dialog/pos'):
            self.move(self.settings.value('importer_dialog/pos'))
        if self.settings.value('importer_dialog/size'):
            self.resize(self.settings.value('importer_dialog/size'))

        index = self.config_cmb.findText(self.settings.value('importer/current_config', ''))
        self.config_cmb.setCurrentIndex(max(0, index))
        self.config_changed(self.config_cmb.currentText())

        for path in self.settings.list('importer/recent_paths'):
            self.path_cmb.addItem(path)

        self.subfolders_chk.setChecked(self.settings.bool('importer/include_subfolders'))

    def edit_settings(self):
        os.startfile(self.settings.fileName())

    def reset_settings(self):
        result = QtWidgets.QMessageBox.question(
            self,
            'Reset Settings',
            'Are you sure you want to reset the settings?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            self.settings.clear()

    def edit_configs(self):
        os.startfile(self.settings.configs_path)

    def import_config(self):
        path, file_filter = QtWidgets.QFileDialog.getOpenFileName(
            caption='Import Config',
            dir=self.settings.configs_path,
            filter='Configs (*.json)')
        if path:
            import shutil
            logging.debug(path)
            shutil.copy2(path, self.settings.configs_path)
            self.load_config_files()
            self.update_config_cmb()


class ListWidget(QtWidgets.QWidget):
    item_changed = QtCore.Signal(object)

    def __init__(self, parent=None, widget=QtWidgets.QWidget):
        super(ListWidget, self).__init__(parent)

        self.setAcceptDrops(True)

        self._show_drop_line = False
        self._drop_line_index = -1
        self._widget_cls = widget

        # create the layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(9)
        # layout.setSpacing(0)
        # layout.addStretch(1)

        self.setLayout(layout)

        self.add_btn = ListAddButton()
        self.layout().insertWidget(-1, self.add_btn)
        self.layout().addStretch(1)

        self.add_btn.clicked.connect(self.add_item)

    def add_item(self):
        logging.debug('add_item')
        item = ListItem(parent=self, widget=self._widget_cls)
        self.layout().insertWidget(self.layout().count() - 2, item)
        self.layout().setStretchFactor(item, 0)

        self.item_changed.emit(item)

        return item

    def delete_item(self, item=None):
        self.item_changed.emit(item)
        self.layout().removeWidget(item)
        item.deleteLater()

    def clear(self):
        # self.setUpdatesEnabled(False)
        while self.layout().count() > 2:
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # self.setUpdatesEnabled(True)

    def items(self):
        return [self.layout().itemAt(i).widget() for i in range(self.layout().count() - 2)]

    def draw_drop_line(self, index=-1):
        if index == self._drop_line_index:
            return

        self._drop_line_index = index
        self.repaint()

    def dragEnterEvent(self, event):
        logging.debug('dragEnterEvent')
        source = event.source()
        if not source:
            return
        if source != self and isinstance(source, ListItem):
            self._show_drop_line = True
            self.repaint()
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.source() and isinstance(event.source(), ListItem):
            new_index = self.drop_index(event)

            self.draw_drop_line(new_index)

    def dragLeaveEvent(self, event):
        self.draw_drop_line(-1)

    def dropEvent(self, event):
        self.draw_drop_line(-1)

        item = event.source()
        new_index = self.drop_index(event)
        current_index = self.layout().indexOf(item)

        if new_index > current_index:
            new_index -= 1

        logging.debug(new_index)
        self.layout().insertWidget(new_index, item)

    def drop_index(self, event):
        cursor = QtGui.QCursor.pos()
        pos_y = self.mapFromGlobal(cursor).y()

        new_index = 0
        for i in range(self.layout().count() - 2):
            item = self.layout().itemAt(i).widget()
            if pos_y > item.pos().y() + item.height() / 2:
                new_index = i + 1

        return new_index

    def paintEvent(self, event):
        if self._drop_line_index >= 0:
            painter = QtGui.QPainter()
            painter.begin(self)

            margins = self.layout().contentsMargins()
            spacing = self.layout().spacing()

            if self._drop_line_index >= self.layout().count() - 2:
                item = self.layout().itemAt(self.layout().count() - 3).widget()
                pos_y = item.pos().y() + item.height() + spacing / 2
            else:
                item = self.layout().itemAt(self._drop_line_index).widget()
                pos_y = item.pos().y() - spacing / 2

            painter.drawLine(margins.left() + 4, pos_y, self.width() - margins.right() - 4, pos_y)
            painter.end()


class ListItem(QtWidgets.QWidget):
    def __init__(self, parent=None, widget=QtWidgets.QWidget):
        super(ListItem, self).__init__(parent)

        self._list_widget = parent
        self.widget = widget()

        self.init_ui()

    def init_ui(self):

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        frame = QtWidgets.QFrame()
        frame.setFrameShadow(QtWidgets.QFrame.Sunken)
        frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        layout.addWidget(frame)

        self.widget_layout = QtWidgets.QHBoxLayout()
        self.widget_layout.setContentsMargins(30, 10, 10, 10)
        frame.setLayout(self.widget_layout)

        self.widget_layout.addWidget(self.widget)

        self.delete_btn = QtWidgets.QPushButton()
        self.delete_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_TitleBarCloseButton))
        self.delete_btn.setFlat(True)
        self.delete_btn.setFixedWidth(20)
        self.delete_btn.setFixedHeight(20)
        self.widget_layout.addWidget(self.delete_btn)

        self.delete_btn.clicked.connect(self.delete)

    def delete(self):
        self._list_widget.delete_item(self)

    def dragDropRect(self):
        return QtCore.QRect(10, 10, 10, self.height() - 20)

    def mousePressEvent(self, event):
        logging.debug('mousePressEvent')
        if event.button() == QtCore.Qt.LeftButton and self.dragDropRect().contains(event.pos()):
            logging.debug('drag')

            pixmap = self.grab()
            pixmap_transparent = QtGui.QPixmap(pixmap.size())
            pixmap_transparent.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pixmap_transparent)
            painter.setOpacity(0.9)
            painter.drawPixmap(QtCore.QPoint(), pixmap)
            painter.end()

            mimeData = QtCore.QMimeData()

            drag = QtGui.QDrag(self)
            drag.setMimeData(mimeData)
            drag.setPixmap(pixmap_transparent)
            drag.setHotSpot(event.pos())

            drag.exec_()
            event.accept()

        else:
            event.ignore()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        brush = painter.brush()
        brush.setStyle(QtCore.Qt.Dense7Pattern)
        brush.setColor(painter.pen().color())
        painter.setBrush(brush)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.dragDropRect())
        painter.end()


class ListAddButton(QtWidgets.QPushButton):
    def __init__(self, parent=None):
        super(ListAddButton, self).__init__(parent)

        self.setText('+')
        self.setMinimumHeight(40)

        effect = QtWidgets.QGraphicsOpacityEffect(self)
        effect.setOpacity(0.4)
        self.setGraphicsEffect(effect)


class ChannelItem(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ChannelItem, self).__init__(parent)

        self._load_ui()

    def _load_ui(self):
        load_ui(self, 'channel_item.ui')

        self.attribute_cmb.setCurrentIndex(-1)
        self.attribute_cmb.currentIndexChanged.emit(0)

        for text in ['$mesh', '$material', '$udim']:
            action = QtWidgets.QAction(text, self)
            action.triggered.connect(self.add_placeholder)
            self.pattern_line.addAction(action)

        self.pattern_line.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def add_placeholder(self):
        action = self.sender()
        text = self.pattern_line.displayText()
        if self.pattern_line.selectionStart() != -1:
            start = self.pattern_line.selectionStart()
            end = self.pattern_line.selectionStart() + self.pattern_line.selectionLength()
            text = text[:start] + action.text() + text[end:]
            pos = start
        else:
            pos = self.pattern_line.cursorPosition()
            text = text[:pos] + action.text() + text[pos:]

        self.pattern_line.setText(text)
        self.pattern_line.setCursorPosition(pos + len(action.text()))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    show(ImporterDialog)
