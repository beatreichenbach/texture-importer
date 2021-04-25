from __future__ import absolute_import
import sys
from PySide2 import QtWidgets
from textureimporter import importer_dialog
from maya import mel, cmds
from .. import importer
from .. import setup
import logging
import os


def run():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    main_window = next(w for w in app.topLevelWidgets() if w.objectName() == 'MayaWindow')
    dialog = importer_dialog.ImporterDialog(main_window, dcc='maya')
    dialog.show()
    return main_window


class Importer(importer.Importer):
    settings_group = 'maya'
    settings_defaults = {
        'material_node_pattern': '{}_mat',
        'shadingengine_node_pattern': '{}_sg',
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
        if not (cmds.pluginInfo(self.plugin_name, query=True, loaded=True)):
            cmds.loadPlugin(self.plugin_name)

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
        material_node = self.create_node('lambert', name=material_node_name, asShader=True)
        shadingengine_node = self.create_node(
            'shadingEngine',
            name=shadingengine_node_name,
            empty=True,
            renderable=True,
            noSurfaceShader=True)

        out_connection = '{}.outColor'.format(material_node)
        in_connection = '{}.surfaceShader'.format(shadingengine_node)
        cmds.connectAttr(out_connection, in_connection, force=True)

        return material_node, shadingengine_node

    def create_file(self, name, file_path, colorspace):
        file_node = self.create_node('file', name=name, asTexture=True, isColorManaged=True)
        cmds.setAttr('{}.fileTextureName'.format(file_node), file_path, type='string')
        if '<UDIM>' in file_path:
            cmds.setAttr('{}.uvTilingMode'.format(file_node), 3)

        cmds.setAttr('{}.colorSpace'.format(file_node), colorspace, type='string')

        return file_node

    def create_place(self, name):
        place_node = self.create_node('place2dTexture', name=name, asUtility=True)

        return place_node

    def connect_place(self, place_node, file_node):
        attributes = [
            ('outUV', 'uvCoord'),
            ('outUvFilterSize', 'uvFilterSize'),
            ('vertexCameraOne', 'vertexCameraOne'),
            ('vertexUvOne', 'vertexUvOne'),
            ('vertexUvThree', 'vertexUvThree'),
            ('vertexUvTwo', 'vertexUvTwo'),
            ('coverage', 'coverage'),
            ('mirrorU', 'mirrorU'),
            ('mirrorV', 'mirrorV'),
            ('noiseUV', 'noiseUV'),
            ('offset', 'offset'),
            ('repeatUV', 'repeatUV'),
            ('rotateFrame', 'rotateFrame'),
            ('rotateUV', 'rotateUV'),
            ('stagger', 'stagger'),
            ('translateFrame', 'translateFrame'),
            ('wrapU', 'wrapU'),
            ('wrapV', 'wrapV')]

        for place_attr, file_attribute in attributes:
            out_connection = '{}.{}'.format(place_node, place_attr)
            in_connection = '{}.{}'.format(file_node, file_attribute)
            cmds.connectAttr(out_connection, in_connection, force=True)

    def connect_file(self, file_node, material_node, material_attribute):
        if cmds.getAttr('{}.{}'.format(material_node, material_attribute), type=True) == 'float':
            cmds.setAttr('{}.alphaIsLuminance'.format(file_node), True)
            file_attribute = 'outAlpha'
        else:
            file_attribute = 'outColor'

        out_connection = '{}.{}'.format(file_node, file_attribute)
        in_connection = '{}.{}'.format(material_node, material_attribute)
        cmds.connectAttr(out_connection, in_connection, force=True)

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
        logging.debug('assign_material')
        selection = cmds.ls(selection=True)
        cmds.select(mesh, replace=True)
        logging.debug(mesh)
        if cmds.ls(selection=True):
            cmds.hyperShade(assign=material)
        cmds.select(selection, replace=True)


class Mesh(importer.Mesh):
    @property
    def name(self):
        name = str(self.mesh.rsplit('|')[-1])
        return name


class Installer(setup.Installer):
    # def __init__(self):
    #     super(Installer, self).__init__()

    def create_button(self):
        shelf_name = 'Plugins'
        label = 'textureimporter'
        image_path = 'textureEditor.png'
        command = (
            'from textureimporter.plugins.maya import run\n'
            'main_window = run()')

        top_level_shelf = mel.eval('$gShelfTopLevel = $gShelfTopLevel;')

        if cmds.shelfLayout(shelf_name, exists=True):
            buttons = cmds.shelfLayout(shelf_name, query=True, childArray=True) or []
            for button in buttons:
                if cmds.shelfButton(button, label=True, query=True) == label:
                    cmds.deleteUI(button)
        else:
            mel.eval('addNewShelfTab "{}";'.format(shelf_name))

        cmds.shelfButton(label=label, command=command, parent=shelf_name, image=image_path)
        logging.info('Created button "{}"" on shelf "{}".'.format(label, shelf_name))
        return cmds.saveAllShelves(top_level_shelf)

    def install_package(self):
        maya_app_path = os.path.normpath(os.getenv('MAYA_APP_DIR'))
        if maya_app_path is None:
            if sys.platform.startswith('win32'):
                maya_app_path = os.path.join(os.path.expanduser("~"), 'Documents', 'Maya')
            elif sys.platform.startswith('linux'):
                maya_app_path = os.path.join(os.path.expanduser("~"), 'Maya')
            elif sys.platform.startswith('darwin'):
                maya_app_path = os.path.join(os.path.expanduser("~"), 'Library', 'Preferences', 'Autodesk', 'Maya')

        if not maya_app_path:
            logging.error('Could not find maya scripts directory.')
            return False

        scripts_path = os.path.join(maya_app_path, 'scripts')
        if not os.path.isdir(scripts_path):
            os.makedirs(scripts_path)

        if not self.copy_package(scripts_path):
            return False

        try:
            self.create_button()
        except ModuleNotFoundError:
            logging.error(
                'Could not install maya script button. '
                'Make sure to run the setup from Maya.')
            return False

        logging.info('Installation successfull.')
        return True
