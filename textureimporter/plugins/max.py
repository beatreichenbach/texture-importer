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
    top_level_windows = QtWidgets.QApplication.topLevelWidgets()

    no_parent_windows = list()
    for widget in top_level_windows:
        if (isinstance(widget, QtWidgets.QWidget) and widget.parentWidget() is None):
            no_parent_windows.append(widget)
    main_window = no_parent_windows[0]
    # main_window = rt.GetQMaxWindow()
    dialog = importer_dialog.ImporterDialog(main_window, dcc='max')
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
        import pymxs
        rt = pymxs.runtime
        mat = rt.PhysicalMaterial()
        for prop in rt.getPropNames(mat):
            print(prop)
        '''

        return []

    @property
    def colorspaces(self):
        colorspaces = [
            'auto',
            'linear',
            'sRGB',
            'Rec709',
        ]

        return colorspaces

    def load_plugin(self):
        for renderer in rt.rendererClass.classes:
            if str(renderer) == self.plugin_name:
                return
        else:
            raise RuntimeError

    def get_meshes(self):
        meshes = [Mesh(mesh) for mesh in rt.selection]
        return meshes

    def exists(self, node_name):
        return node_name in rt.scenematerials

    def create_network(self, network, **kwargs):
        self.current_network = network
        self.current_kwargs = kwargs
        selection = rt.selection

        set_members = []
        if kwargs.get('assign_material') and self.exists(network.material_node_name):
            # store material assignments
            material = rt.getnodebyname(network.material_node_name)
            material_dependents = rt.refs.dependents(material)
            set_members = [i for i in material_dependents if rt.superClassOf(i) == rt.GeometryClass]

        material_node = self.create_material(network.material_node_name)

        for channel in network.channels:
            if not channel.file_node_name:
                continue

            file_node = self.create_file(channel.file_node_name, channel.file_path, channel.colorspace)

            attribute_name = channel.attribute_name
            try:
                self.connect_file(file_node, material_node, attribute_name)
            except RuntimeError:
                logging.error(
                    'Could not connect material attribute: '
                    '{}.{}'.format(material_node, attribute_name))

        rt.select(selection)
        if kwargs.get('assign_material'):
            if set_members:
                self.assign_material(material_node, set_members)
            elif network.mesh:
                self.assign_material(material_node, network.mesh)
            else:
                self.assign_material(material_node, [mesh.mesh for mesh in self.get_meshes()])

        rt.meditmaterials[kwargs['index']] = material_node

        rt.select(selection)
        self.current_network = None
        self.current_kwargs = None

    def create_material(self, material_node_name):
        material = self.create_node('PhysicalMaterial', name=material_node_name)

        return material

    def create_file(self, name, file_path, colorspace):
        file_node = rt.Bitmaptexture(name=name)
        file_node.filename = file_path
        return file_node

    def connect_file(self, file_node, material_node, material_attribute):
        setattr(material_node, material_attribute, file_node)

    def create_node(self, node_type, **kwargs):
        name = kwargs.get('name', '')
        old_node = rt.getnodebyname(name)

        node_cls = getattr(rt, node_type)
        node = node_cls(**kwargs)

        on_conflict = self.current_kwargs.get('on_conflict')
        if on_conflict in ('replace', 'remove'):
            if old_node:

                # out_connections = cmds.listConnections(
                #     old_node, destination=True, source=False, connections=True, plugs=True)
                # cmds.delete(old_node)

                if on_conflict == 'remove':
                    return node

                # for i in range(0, len(out_connections), 2):
                #     source = out_connections[i]
                #     destination = out_connections[i + 1]

                #     try:
                #         # only connect if the attribute is valid and not already connected
                #         valid_attr = source.split('.')[-1] not in ('message', 'partition')
                #         not_connected = not cmds.isConnected(source, destination)
                #         if valid_attr and not_connected:
                #             cmds.connectAttr(source, destination, force=True)
                #     except (RuntimeError, ValueError):
                #         pass
        return node

    def assign_material(self, material, meshes):
        if not isinstance(meshes, list):
            meshes = [meshes]
        for mesh in meshes:
            mesh.mat = material


class Mesh(importer.Mesh):
    @property
    def name(self):
        name = self.mesh.Name
        return name


class Installer(setup.Installer):
    def create_macro_script(self, scripts_path):
        macroscript = (
            'macroScript TextureImporter '
            'category:"Plugins" '
            'tooltip:"Texture Importer" '
            'buttonText:"TextureImporter" '
            'Icon:#("UVWUnwrapOption", 6) (\n'
            '    on execute do (\n'
            '        python.Execute "import sys"\n'
            '        python.Execute "sys.path.append(r\'' + scripts_path + '\')"\n'
            '        python.Execute "from textureimporter.plugins.max import run"\n'
            '        python.Execute "window = run()"\n'
            '    )\n'
            ')')
        rt.execute(macroscript)

    def install_package(self):
        scripts_path = rt.getDir(pymxs.runtime.Name('userScripts')) or ''
        scripts_path = os.path.normpath(scripts_path)

        if not scripts_path:
            logging.error('Could not find maya scripts directory.')
            return False

        if not self.copy_package(scripts_path):
            return False

        try:
            self.create_macro_script(scripts_path=scripts_path)
        except RuntimeError as e:
            logging.error('Could not install MacroScript.')
            logging.error(e)
            return False

        logging.info('Installation successfull.')
        return True
