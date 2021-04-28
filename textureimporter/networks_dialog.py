import logging
import os

from PySide2 import QtWidgets, QtCore, QtGui
import gui_utils
import utils


class NetworksWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(NetworksWidget, self).__init__(parent)

        self.networks = []
        self.settings = utils.Settings()

        self.init_ui()

    def init_ui(self):
        gui_utils.load_ui(self, 'networks_widget.ui')

        self.resize(800, 600)

        placeholder = self.networks_tree
        self.networks_tree = NetworksTreeWidget(self.networks_tree)
        self.networks_tree.setHeaderLabels(('Material', 'Node Name', 'Status', 'File Name'))
        self.networks_tree.setSortingEnabled(True)
        self.networks_tree.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.networks_tree.setSelectionMode(self.networks_tree.ExtendedSelection)
        self.networks_tree.setAlternatingRowColors(True)
        self.layout().insertWidget(self.layout().indexOf(placeholder), self.networks_tree)
        self.layout().removeWidget(placeholder)
        placeholder.setParent(None)
        placeholder.deleteLater()

        conflict_options = {
            'remove': 'Remove Existing Nodes',
            'replace': 'Replace Existing Nodes with Connections',
            'rename': 'Rename Nodes',
        }
        for name, label in conflict_options.items():
            self.conflict_cmb.addItem(label, name)

        self.check_all_btn.clicked.connect(lambda: self.networks_tree.check_all_items(QtCore.Qt.Checked))
        self.check_none_btn.clicked.connect(lambda: self.networks_tree.check_all_items(QtCore.Qt.Unchecked))
        self.check_selected_btn.clicked.connect(lambda: self.networks_tree.check_selected_items(QtCore.Qt.Checked))

        self.load_settings()

    def save_settings(self):
        pass

    def load_settings(self):
        pass

    def accept(self):
        self.save_settings()
        super(NetworksWidget, self).accept()

    def reject(self):
        self.save_settings()
        super(NetworksWidget, self).reject()

    def closeEvent(self, event):
        self.save_settings()

    def selected_networks(self):
        self.save_settings()

        self.networks = []
        for i in range(self.networks_tree.topLevelItemCount()):
            item = self.networks_tree.topLevelItem(i)
            network = item.data(0, QtCore.Qt.UserRole)
            if not item.checkState(0):
                continue

            network.channels = []
            for j in range(item.childCount()):
                child = item.child(j)
                channel = child.data(0, QtCore.Qt.UserRole)
                if child.checkState(0):
                    network.channels.append(channel)

            self.networks.append(network)
        return self.networks


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


class NetworksTreeWidget(QtWidgets.QTreeWidget):
    def __init__(self, *args):
        super(NetworksTreeWidget, self).__init__(*args)

        self.networks = []

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        self.setStyleSheet('QTreeWidget::item {padding: 5px 20px 5px 0;}')

    def check_all_items(self, checkstate):
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            item.setCheckState(0, checkstate)

    def check_selected_items(self, checkstate):
        for item in self.selectedItems():
            item.setCheckState(0, checkstate)

    def context_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        action = menu.addAction('Check')
        action.triggered.connect(lambda: self.check_selected_items(QtCore.Qt.Checked))
        action = menu.addAction('Uncheck')
        action.triggered.connect(lambda: self.check_selected_items(QtCore.Qt.Unchecked))
        menu.exec_(self.viewport().mapToGlobal(pos))

    def add_networks(self, networks):
        for network in networks:
            self.add_network(network)

    def add_network(self, network):
        self.networks.append(network)

        item = SortTreeWidgetItem([network.material_name, network.material_node_name])
        item.setFlags(item.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
        item.setData(0, QtCore.Qt.UserRole, network)
        item.setSortData(0, network.material_name)

        if network.exists:
            icon = self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
            item.setText(2, 'Node exists')
            item.setCheckState(0, QtCore.Qt.Unchecked)
        else:
            icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)
            item.setCheckState(0, QtCore.Qt.Checked)
        item.setSortData(2, network.exists)
        item.setIcon(2, icon)

        children = []
        for i, channel in enumerate(network.channels):
            file_name = os.path.basename(channel.file_path)
            child = SortTreeWidgetItem([channel.attribute_name, channel.file_node_name, None, file_name])
            child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
            child.setData(0, QtCore.Qt.UserRole, channel)
            child.setSortData(0, i)
            child.setCheckState(0, item.checkState(0))

            if not channel.file_path:
                icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton)
                child.setText(2, 'Not Found')
            elif channel.exists:
                icon = self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
                child.setText(2, 'Node exists')
            else:
                icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)

            child.setSortData(2, channel.exists)
            child.setIcon(2, icon)

            children.append(child)

        item.addChildren(children)
        self.addTopLevelItem(item)

        self.expandAll()
        for i in range(self.header().count()):
            self.resizeColumnToContents(i)
        self.collapseAll()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import importer

    network = importer.Network()
    network.mesh_name = None
    network.material_name = 'Default'
    network.material_node_name = 'Default_mat'

    for i in range(3):
        network_channel = importer.NetworkChannel(network)
        network_channel.attribute_name = 'baseColor'
        network_channel.file_node_name = 'Default_baseColor_tex'
        network_channel.file_path = 'C:/Users/Beat/Desktop/textures/Default_baseColor.<UDIM>.png'

    import sys
    app = QtWidgets.QApplication(sys.argv)
    dialog = NetworksWidget()
    dialog.networks_tree.add_network(network)
    dialog.networks_tree.add_network(network)
    dialog.show()
    sys.exit(app.exec_())

    # show(NetworksWidget)
