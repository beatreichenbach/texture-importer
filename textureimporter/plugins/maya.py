from __future__ import absolute_import
import sys
from PySide2 import QtWidgets
from textureimporter import importer_dialog
from maya import cmds
from .. import importer
import logging


class Importer(importer.Importer):
    display_name = 'Maya Renderer'
    material_node_pattern = '{}_mat'
    shadingengine_node_pattern = '{}_sg'
    file_node_pattern = '{}_tex'
    place_node_pattern = '{}_place'
    normal_node_pattern = '{}_normal'
    default_name = 'default'

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

    def get_selection(self):
        meshes = cmds.ls(selection=True, long=True)
        meshes = [(mesh.rsplit('|')[-1], mesh) for mesh in meshes]
        logging.debug(meshes)
        return meshes

    def exists(self, node_name):
        return cmds.objExists(node_name)

    def create_network(self, network, kwargs):
        shadingengine_node_name = self.shadingengine_node_pattern.format(network.material_name)
        material_node, shadingengine_node = self.create_material(network.material_node_name, shadingengine_node_name)

        place_name = self.place_node_pattern.format(network.material_name)
        place_node = self.create_place(place_name)

        for channel in network.channels:
            # catch errors incase attribute doesn't exist ya know?
            attribute_name = channel.attribute_name

            file_node = self.create_file(channel.file_node_name, channel.file_path, channel.colorspace)
            self.connect_place(place_node, file_node)
            self.connect_file(file_node, material_node, attribute_name)

        # self.assign_material(material_node, network.mesh_name)

    def create_material(self, material_node_name, shadingengine_node_name):
        material_node = cmds.shadingNode('lambert', name=material_node_name, asShader=True)
        shadingengine_node = cmds.sets(name=shadingengine_node_name, empty=True, renderable=True, noSurfaceShader=True)
        cmds.connectAttr('{}.outColor'.format(material_node), '{}.surfaceShader'.format(shadingengine_node))

        return material_node, shadingengine_node

    def create_file(self, name, file_path, colorspace):
        file_node = cmds.shadingNode('file', name=name, asTexture=True, isColorManaged=True)
        cmds.setAttr('{}.fileTextureName'.format(file_node), file_path, type='string')
        if '<UDIM>' in file_path:
            cmds.setAttr('{}.uvTilingMode'.format(file_node), 3)

        cmds.setAttr('{}.colorSpace'.format(file_node), colorspace, type='string')

        return file_node

    def create_place(self, name):
        place_node = cmds.shadingNode('place2dTexture', name=name, asUtility=True)

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
            cmds.connectAttr('{}.{}'.format(place_node, place_attr), '{}.{}'.format(file_node, file_attribute))

    def connect_file(self, file_node, material_node, material_attribute):
        if cmds.getAttr('{}.{}'.format(material_node, material_attribute), type=True) == 'float':
            cmds.setAttr('{}.alphaIsLuminance'.format(file_node), True)
            file_attribute = 'outAlpha'
        else:
            file_attribute = 'outColor'
        cmds.connectAttr('{}.{}'.format(file_node, file_attribute), '{}.{}'.format(material_node, material_attribute), force=True)

    def assign_material(self, material, mesh):
        cmds.select(mesh, replace=True)
        if cmds.ls(selection=True):
            cmds.hyperShade(material, assign=True)


def run():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    main_window = next(w for w in app.topLevelWidgets() if w.objectName() == 'MayaWindow')
    dialog = importer_dialog.ImporterDialog(main_window, dcc='maya')
    dialog.show()
    return main_window
