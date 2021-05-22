import sys
from PySide2 import QtWidgets
import logging
import os

from textureimporter import importer_dialog
from .. import importer
from .. import setup

import pymxs
rt = pymxs.runtime


def run():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    main_window = next(w for w in app.topLevelWidgets() if w.objectName() == 'MayaWindow')
    dialog = importer_dialog.ImporterDialog(main_window, dcc='maya')
    dialog.show()
    return main_window


class Importer(importer.Importer):
    display_name = ''
    plugin_name = ''
    settings_group = 'max'
    settings_defaults = {
        'material_node_pattern': '{}_mat',
        'file_node_pattern': '{}_tex',
        'place_node_pattern': '{}_place',
        'normal_node_pattern': '{}_normal',
        'default_name': 'default',
        }

    def __init__(self):
        super(Importer, self).__init__()

    @property
    def attributes(self):
        '''
        material_node = cmds.shadingNode('lambert', asShader=True)
        attrs = cmds.listAttr(material_node, write=True, connectable=True)
        attrs = [attr for attr in attrs if attr[-1] not in ['R', 'G', 'B', 'X', 'Y', 'Z']]
        print(attrs)
        cmds.delete(material_node)
        '''

        return []

    @property
    def colorspaces(self):
        colorspaces = [
            'Raw',
            'sRGB',
            'Utility - Raw',
            'Utility - sRGB - Texture',
            'Utility - Linear - sRGB ',
            'Output - sRGB ',
            'ACES - ACEScg ',
        ]

        return colorspaces

    def load_plugin(self):
        for renderer in rt.rendererClass.classes:
            if 'V_RAY' in renderer:
                return
        else:
            raise RuntimeError

    def get_meshes(self):
        meshes = cmds.ls(selection=True, long=True)
        meshes = [Mesh(mesh) for mesh in meshes]
        return meshes

    def exists(self, node_name):
        return cmds.objExists(node_name)

    def create_network(self, network, **kwargs):
        self.current_network = network
        self.current_kwargs = kwargs
        selection = cmds.ls(selection=True)

        set_members = []
        if kwargs.get('assign_material') and self.exists(network.material_node_name):
            # store material assignments

            outputs = cmds.listConnections(
                network.material_node_name, destination=True, source=False, type='shadingEngine')
            if outputs:
                shadingengine_node = outputs[0]
                set_members = cmds.listConnections(
                    '{}.dagSetMembers'.format(shadingengine_node), destination=False, source=True)

        shadingengine_node_name = self.resolve_name('shadingengine_node_pattern', network.material_name)
        material_node, shadingengine_node = self.create_material(network.material_node_name, shadingengine_node_name)

        place_name = self.resolve_name('place_node_pattern', network.material_name)
        place_node = self.create_place(place_name)

        for channel in network.channels:
            if not channel.file_node_name:
                continue

            file_node = self.create_file(channel.file_node_name, channel.file_path, channel.colorspace)
            self.connect_place(place_node, file_node)

            attribute_name = channel.attribute_name
            try:
                self.connect_file(file_node, material_node, attribute_name)
            except RuntimeError:
                logging.error(
                    'Could not connect material attribute: '
                    '{}.{}'.format(material_node, attribute_name))

        cmds.select(selection, replace=True)
        if kwargs.get('assign_material'):
            if set_members:
                for set_member in set_members:
                    self.assign_material(material_node, set_member)
            elif network.mesh:
                self.assign_material(material_node, network.mesh)
            else:
                self.assign_material(material_node, [mesh.mesh for mesh in self.get_meshes()])

        cmds.select(selection, replace=True)
        self.current_network = None
        self.current_kwargs = None

    def create_material(self, material_node_name, shadingengine_node_name):
        material = MaxPlus.Factory.CreateDefaultStdMat()
        return material

    def create_file(self, name, file_path, colorspace):
        file_node = MaxPlus.Factory.CreateDefaultBitmapTex()
        file_node.SetMapName(file_path)
        file_node.ReloadBitmapAndUpdate()

        return file_node

    def create_place(self, name):
        place_node = self.create_node('place2dTexture', name=name, asUtility=True)

        return place_node

    def connect_place(self, place_node, file_node):
        pass

    def connect_file(self, file_node, material_node, material_attribute):
        materialSubMaps = MaxPlus.ISubMap._CastFrom(material_node)
        materialSubMaps.SetSubTexmap(1, file_node)
        material_node.SetEnableMap(1, True)

    def create_node(self, node_type, **kwargs):
        if node_type == 'shadingEngine':
            node = cmds.sets(**kwargs)
        else:
            node = cmds.shadingNode(node_type, **kwargs)

        on_conflict = self.current_kwargs.get('on_conflict')
        if on_conflict in ('replace', 'remove'):
            name = kwargs.get('name')
            if node != name:
                old_node = name
                out_connections = cmds.listConnections(
                    old_node, destination=True, source=False, connections=True, plugs=True)
                cmds.delete(old_node)
                node = cmds.rename(node, name)

                if on_conflict == 'remove':
                    return node

                for i in range(0, len(out_connections), 2):
                    source = out_connections[i]
                    destination = out_connections[i + 1]

                    try:
                        # only connect if the attribute is valid and not already connected
                        valid_attr = source.split('.')[-1] not in ('message', 'partition')
                        not_connected = not cmds.isConnected(source, destination)
                        if valid_attr and not_connected:
                            cmds.connectAttr(source, destination, force=True)
                    except (RuntimeError, ValueError):
                        pass
        return node

    def assign_material(self, material, mesh):
        mesh.Material = material


class Mesh(importer.Mesh):
    @property
    def name(self):
        name = self.mesh.Name
        return name
