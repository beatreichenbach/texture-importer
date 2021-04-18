import os
import re
import glob
import logging

from PySide2 import QtWidgets, QtCore, QtGui

import importer
import networks_dialog
import gui_utils
import plugin_utils
import utils
import setup


class ImporterDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, dcc=''):
        super(ImporterDialog, self).__init__(parent)

        self.setObjectName('ImporterDialog')
        self.dcc = dcc
        self.settings = utils.Settings()

        self.load_config_files()

        self.init_ui()
        self.update_config_cmb()

        self._connect_ui()
        self.load_settings()

    def init_ui(self):
        gui_utils.load_ui(self, 'importer_dialog.ui')

        self.config_wdg = ConfigWidget(self, self.dcc)
        self.config_scroll.setWidget(self.config_wdg)

        # Config Button Menu
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

        # Menu Bar
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
        action = menu.addAction('Documentation')
        action = menu.addAction('About')
        action = menu.addAction('Update Textureimporter')
        action.triggered.connect(self.update)
        menu_bar.addMenu(menu)
        self.layout().setMenuBar(menu_bar)

        self.main_prgbar.setVisible(False)
        size_policy = self.main_prgbar.sizePolicy()
        size_policy.setRetainSizeWhenHidden(True)
        self.main_prgbar.setSizePolicy(size_policy)

    def _connect_ui(self):
        self.path_browse_btn.clicked.connect(self.browse_path)
        self.config_cmb.currentTextChanged.connect(self.config_changed)

        self.search_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def config_changed(self, text=None):
        logging.debug(('config_changed', text))
        if text is None:
            text = self.config_cmb.currentText()
        if not text:
            return
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
            self.config_wdg.list_wdg.clear()

            self.save_config(name)

    def save_config(self, name=''):
        logging.debug(('save_config', name))
        if not name:
            name = self.config_cmb.currentText()
            if not name:
                self.save_config_as()

        # Update config object
        config = self.config_wdg.config
        config.name = name

        self._configs[name] = config
        self.save_config_files()
        self.update_config_cmb()
        self.config_cmb.setCurrentText(name)

    def save_config_as(self):
        name, result = QtWidgets.QInputDialog.getText(
            self, 'Save As...', 'Config:', text=self.config_cmb.currentText())
        if result:
            self.save_config(name)

    def rename_config(self):
        name, result = QtWidgets.QInputDialog.getText(
            self, 'Rename Config', 'Config:', text=self.config_cmb.currentText())
        if result:
            del self._configs[self.config_cmb.currentText()]
            self.save_config(name)

    def delete_config(self):
        name = self.config_cmb.currentText()
        del self._configs[name]
        os.remove(os.path.join(self.settings.configs_path, '{}.json'.format(name)))
        self.update_config_cmb()
        self.config_cmb.setCurrentIndex(0)

    def load_config(self, name):
        logging.debug(('load_config', name))
        config = self._configs.get(name)
        if not config:
            return

        self.config_wdg.config = config

    def update_config_cmb(self):
        self.config_cmb.blockSignals(True)
        self.config_cmb.clear()
        for name, config in utils.sorted_dict(self._configs.items()):
            self.config_cmb.addItem(config.name, config)
        self.config_cmb.setCurrentIndex(-1)
        self.config_cmb.blockSignals(False)

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

        plugin = '{}_{}'.format(self.dcc, config.renderer)
        self.importer = importer.Importer.from_plugin(plugin)

        networks = self.importer.get_networks(path, config, include_subfolders)
        if not networks:
            QtWidgets.QMessageBox.information(
                self,
                'Nothing to Import',
                'There were no textures found to import with the current config.',
                QtWidgets.QMessageBox.Ok)
            return

        networks = networks_dialog.NetworksDialog.selected_networks(networks)
        for network in networks:
            self.importer.create_network(network)

        # if result:
        #    super(ImporterDialog, self).accept()

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
        self.settings.setValue('importer/current_path', self.path_cmb.currentText())
        self.settings.setValue('importer/include_subfolders', self.subfolders_chk.isChecked())
        self.settings.setValue('importer/on_conflict', self.conflict_cmb.currentText())
        self.settings.setValue('importer/assign_materials', self.assign_chk.isChecked())

    def load_settings(self):
        logging.debug('load_settings')
        if self.settings.value('importer_dialog/pos'):
            self.move(self.settings.value('importer_dialog/pos'))
        if self.settings.value('importer_dialog/size'):
            self.resize(self.settings.value('importer_dialog/size'))

        for path in self.settings.list('importer/recent_paths'):
            self.path_cmb.addItem(path)

        index = self.config_cmb.findText(self.settings.value('importer/current_config', ''))
        self.config_cmb.blockSignals(True)
        self.config_cmb.setCurrentIndex(max(0, index))
        self.config_cmb.blockSignals(False)
        self.config_cmb.currentTextChanged.emit(self.config_cmb.currentText())

        index = self.path_cmb.findText(self.settings.value('importer/current_path', ''))
        self.path_cmb.setCurrentIndex(max(0, index))

        self.subfolders_chk.setChecked(self.settings.bool('importer/include_subfolders'))

        current_index = self.conflict_cmb.findText(self.settings.value('importer/on_conflict', ''))
        current_index = max(0, current_index)
        self.conflict_cmb.setCurrentIndex(current_index)

        self.assign_chk.setChecked(self.settings.bool('importer/assign_materials'))

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
            config_path = shutil.copy2(path, self.settings.configs_path)
            config = utils.Config.from_json(config_path)
            self._configs[config.name] = config
            self.update_config_cmb()
            self.config_cmb.setCurrentText(config.name)

    def update(self):
        setup.Installer.update(self.dcc)


class ListWidget(QtWidgets.QWidget):
    items_changed = QtCore.Signal(object)

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

        self.add_btn = ListAddButton()
        layout.insertWidget(-1, self.add_btn)

        layout.addStretch(1)
        self.setLayout(layout)

        self.add_btn.clicked.connect(self.add_item)

    def add_item(self):
        item = ListItem(parent=self, widget=self._widget_cls)
        self.layout().insertWidget(self.layout().count() - 2, item)
        self.layout().setStretchFactor(item, 0)
        self.items_changed.emit(item)
        return item

    def delete_item(self, item=None):
        self.items_changed.emit(None)
        self.layout().removeWidget(item)
        item.deleteLater()

    def clear(self):
        # self.setUpdatesEnabled(False)
        # oh god please fix this -2
        while self.layout().count() > 2:
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # self.setUpdatesEnabled(True)

    def items(self):
        # oh god please fix this -2
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
    def __init__(self, parent, widget=QtWidgets.QWidget):
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
        self.parent().delete_item(self)

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


class ChannelWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ChannelWidget, self).__init__(parent)

        self._load_ui()

    def _load_ui(self):
        gui_utils.load_ui(self, 'channel_widget.ui')

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

    @property
    def attributes(self):
        return [self.attribute_cmb.itemText(i) for i in range(self.attribute_cmb.count())]

    @attributes.setter
    def attributes(self, attributes):
        self.attribute_cmb.blockSignals(True)
        self.attribute_cmb.clear()
        self.attribute_cmb.addItems(attributes)
        self.attribute_cmb.setCurrentIndex(-1)
        self.attribute_cmb.adjustSize()
        self.attribute_cmb.blockSignals(False)

    @property
    def colorspaces(self):
        return [self.colorspace_cmb.itemText(i) for i in range(self.colorspace_cmb.count())]

    @colorspaces.setter
    def colorspaces(self, colorspaces):
        self.colorspace_cmb.blockSignals(True)
        self.colorspace_cmb.clear()
        self.colorspace_cmb.addItems(colorspaces)
        self.colorspace_cmb.setCurrentIndex(0)
        self.colorspace_cmb.adjustSize()
        self.colorspace_cmb.blockSignals(False)

    @property
    def channel(self):
        channel = utils.ConfigChannel(
            attribute=self.attribute_cmb.currentText(),
            pattern=self.pattern_line.text(),
            colorspace=self.colorspace_cmb.currentText())
        return channel

    @channel.setter
    def channel(self, channel):
        self.attribute_cmb.setCurrentText(channel.attribute)
        self.pattern_line.setText(channel.pattern)
        self.colorspace_cmb.setCurrentText(channel.colorspace)


class ConfigWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, dcc=''):
        super(ConfigWidget, self).__init__(parent)

        self.dcc = dcc
        self.renderers = plugin_utils.render_plugins(self.dcc)
        self.importer = importer.Importer()

        self._load_ui()

    def _load_ui(self):
        gui_utils.load_ui(self, 'config_widget.ui')

        for renderer in self.renderers.keys():
            self.renderer_cmb.addItem(renderer.title(), renderer)

        self.list_wdg = ListWidget(widget=ChannelWidget)
        self.layout().addWidget(self.list_wdg)
        self.layout().addStretch(1)

        self.renderer_cmb.currentTextChanged.connect(self.renderer_changed)
        self.list_wdg.items_changed.connect(self.list_items_changed)

    def list_items_changed(self, item):
        if item is not None:
            item.widget.attribute_cmb.currentIndexChanged.connect(self.lock_channels)
            item.widget.attributes = self.importer.attributes
            item.widget.colorspaces = self.importer.colorspaces
        self.lock_channels()

    def renderer_changed(self, text=None):
        renderer = self.renderer_cmb.currentData()
        if renderer:
            logging.debug('renderer_changed')
            plugin = '{}_{}'.format(self.dcc, renderer)
            self.importer = importer.Importer.from_plugin(plugin)

            for item in self.list_wdg.items():
                item.widget.attributes = self.importer.attributes
                item.widget.colorspaces = self.importer.colorspaces

    def lock_channels(self):
        # find a better name for this. The function enables unused / disables used items.
        used_channels = []
        for item in self.list_wdg.items():
            attribute_cmb = item.widget.attribute_cmb
            if attribute_cmb.currentIndex() in used_channels:
                attribute_cmb.setCurrentIndex(-1)
            else:
                used_channels.append(attribute_cmb.currentIndex())

        for item in self.list_wdg.items():
            attribute_cmb = item.widget.attribute_cmb
            for i in range(attribute_cmb.count()):
                cmb_item = attribute_cmb.model().item(i)
                cmb_item.setEnabled(i not in used_channels)

    @property
    def config(self):
        logging.debug('get_config')

        config = utils.Config()
        config.renderer = self.renderer_cmb.currentData()
        config.channels = [item.widget.channel for item in self.list_wdg.items()]

        return config

    @config.setter
    def config(self, config):
        logging.debug(('set_config', config.name))

        self.reset_config()
        if config.renderer:
            self.renderer_cmb.setCurrentText(config.renderer.title())

        for channel in config.channels:
            item = self.list_wdg.add_item()
            item.widget.channel = channel

    def reset_config(self):
        # making sure to trigger renderer_changed
        self.renderer_cmb.setCurrentIndex(-1)
        self.list_wdg.clear()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    gui_utils.show(ImporterDialog)
