import sys
from PySide2 import QtWidgets
import logging
import os
import re

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
        colorspaces = []

        return colorspaces

    def load_plugin(self):
        for renderer in rt.rendererClass.classes:
            if self.plugin_name in str(renderer):
                return
        else:
            raise RuntimeError

    def get_meshes(self):
        meshes = [Mesh(mesh) for mesh in rt.selection]
        return meshes

    def exists(self, node_name):
        material_names = [mat.name for mat in rt.sceneMaterials]
        return node_name in material_names

    def create_network(self, network, **kwargs):
        self.current_network = network
        self.current_kwargs = kwargs
        selection = rt.selection

        set_members = []
        if kwargs.get('assign_material') and self.exists(network.material_node_name):
            # store material assignments
            material = rt.getnodebyname(network.material_node_name)
            material_dependents = rt.refs.dependents(material) or []
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
        rt.setProperty(material_node, material_attribute, file_node)

    def create_node(self, node_type, **kwargs):
        name = kwargs.get('name', '')
        old_node = None
        for material in rt.sceneMaterials:
            if material.name == name:
                old_node = material
                break

        node_cls = getattr(rt, node_type)
        node = node_cls(**kwargs)

        on_conflict = self.current_kwargs.get('on_conflict')
        if on_conflict == 'rename':
            # prevent infinite loop
            for i in range(100):
                digit = 0
                old_name = name
                match = re.search(r'(.*?)(\d+)$', name)
                if match:
                    digit = int(match.group(2))
                    old_name = match.group(1)

                new_name = '{}{:03d}'.format(old_name, digit)
                if not self.exists(new_name):
                    node.name = new_name
                    break
        elif on_conflict == 'remove':
            pass
        elif on_conflict == 'replace':
            if old_node:
                # Find outgoing nodes
                parents = []
                for dependent in list(rt.refs.dependents(old_node)):
                    cls = rt.classOf(dependent)
                    super_cls = rt.superClassOf(dependent)
                    if (cls in [rt.Material_Editor] or
                            super_cls in [rt.GeometryClass, rt.RendererClass, rt.Material]):
                        parents.append(dependent)

                # Find outgoing connections
                for parent in parents:

                    attributes = list(rt.getPropNames(parent))
                    if rt.superClassOf(parent) == rt.GeometryClass:
                        attributes.append('material')
                    for attribute in attributes:
                        try:
                            attribute_name = str(attribute)
                            value = rt.getProperty(parent, rt.Name(attribute_name))
                            if rt.classOf(value) == rt.ArrayParameter:
                                for i, list_value in enumerate(value):
                                    if list_value == old_node:
                                        value[i] = node
                            elif value == old_node:
                                rt.setProperty(parent, attribute_name, node)
                        except Exception:
                            pass

        return node

    def assign_material(self, material, meshes):
        if not isinstance(meshes, list):
            meshes = [meshes]
        for mesh in meshes:
            mesh.material = material


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
            '        python.Execute "path = r\'' + scripts_path + '\'"'
            '        python.Execute "if path not in sys.path: sys.path.append(path)"'
            '        python.Execute "from textureimporter.plugins.max import run"\n'
            '        python.Execute "window = run()"\n'
            '    )\n'
            ')')
        rt.execute(macroscript)

    def install_package(self):
        scripts_path = rt.getDir(rt.Name('userScripts')) or ''
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
