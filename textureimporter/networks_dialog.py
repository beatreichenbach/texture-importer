import logging
import os

from PySide2 import QtWidgets, QtCore, QtGui
from gui_utils import load_ui, show
import utils


class NetworksDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(NetworksDialog, self).__init__(parent)

        self.networks = []
        self.settings = utils.Settings()

        self.init_ui()

    def init_ui(self):
        load_ui(self, 'networks_dialog.ui')

        self.materials_tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.materials_tree.customContextMenuRequested.connect(self.context_menu)

        self.main_prgbar.setVisible(False)

        self.main_btnbox.accepted.connect(self.accept)
        self.main_btnbox.rejected.connect(self.reject)

        self.load_settings()

    def populate(self, networks):
        self.networks = networks
        for network in networks:
            item = SortTreeWidgetItem([network.material_name, network.material_node_name])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
            item.setData(0, QtCore.Qt.UserRole, network)

            if network.exists:
                icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)
                item.setCheckState(0, QtCore.Qt.Unchecked)
            else:
                icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton)
                item.setCheckState(0, QtCore.Qt.Checked)
            item.setSortData(2, network.exists)
            item.setIcon(2, icon)

            icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton)
            item.setSortData(2, False)

            item.setIcon(2, icon)

            children = []
            for channel in network.channels:
                file_name = os.path.basename(channel.file_path)
                child = SortTreeWidgetItem([channel.attribute_name, channel.file_node_name, None, file_name])
                child.setData(0, QtCore.Qt.UserRole, channel)
                if channel.exists:
                    icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)
                    child.setCheckState(0, QtCore.Qt.Unchecked)
                else:
                    icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton)
                    child.setCheckState(0, QtCore.Qt.Checked)
                child.setSortData(2, channel.exists)
                child.setIcon(2, icon)

                child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
                children.append(child)

            item.addChildren(children)
            self.materials_tree.addTopLevelItem(item)

        self.materials_tree.expandAll()
        for i in range(self.materials_tree.header().count()):
            self.materials_tree.resizeColumnToContents(i)
        self.materials_tree.collapseAll()

    def context_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        action = menu.addAction('Check')
        action.triggered.connect(lambda: self.check_selected_items(QtCore.Qt.Checked))
        action = menu.addAction('Uncheck')
        action.triggered.connect(lambda: self.check_selected_items(QtCore.Qt.Unchecked))
        menu.exec_(self.materials_tree.viewport().mapToGlobal(pos))

    def check_selected_items(self, checkstate):
        for item in self.materials_tree.selectedItems():
            item.setCheckState(0, checkstate)

    def save_settings(self):
        self.settings.setValue('networks_dialog/pos', self.pos())
        self.settings.setValue('networks_dialog/size', self.size())
        self.settings.setValue('importer/on_conflict', self.conflict_cmb.currentText())
        self.settings.setValue('importer/assign_materials', self.assign_chk.isChecked())

    def load_settings(self):
        if self.settings.value('assign_materials/pos'):
            self.move(self.settings.value('networks_dialog/pos'))
        if self.settings.value('networks_dialog/size'):
            self.resize(self.settings.value('networks_dialog/size'))

        current_index = self.conflict_cmb.findText(self.settings.value('importer/on_conflict', ''))
        current_index = max(0, current_index)
        self.conflict_cmb.setCurrentIndex(current_index)

        self.assign_chk.setChecked(self.settings.bool('importer/assign_materials'))

    def accept(self):
        self.save_settings()
        from plugins.maya_arnold import Importer
        importer = Importer()
        for i in range(self.materials_tree.topLevelItemCount()):
            item = self.materials_tree.topLevelItem(i)
            network = item.data(0, QtCore.Qt.UserRole)
            if not item.checkState(0):
                continue

            attributes = []
            for j in range(item.childCount()):
                child = item.child(j)
                attribute = child.data(0, QtCore.Qt.UserRole)
                if child.checkState(0):
                    attributes.append(attribute)
            network.channels = attributes

            kwargs = {
                'assign_material': self.assign_chk.isChecked()
            }
            importer.create_network(network, kwargs)

        super(NetworksDialog, self).accept()

    def reject(self):
        self.save_settings()
        super(NetworksDialog, self).reject()

    def closeEvent(self, event):
        self.save_settings()


class SortTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, *args):
        super(SortTreeWidgetItem, self).__init__(*args)
        self._sortData = {}

    def __lt__(self, other):
        if not isinstance(other, SortTreeWidgetItem):
            return super(SortTreeWidgetItem, self).__lt__(other)

        tree = self.treeWidget()
        column = tree.sortColumn() if tree else 0

        return self.sortData(column) < other.sortData(column)

    def sortData(self, column):
        return self._sortData.get(column, self.text(column))

    def setSortData(self, column, data):
        self._sortData[column] = data


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    show(NetworksDialog)
