from __future__ import absolute_import

from maya import cmds
import logging
from .. import importer


class Importer(importer.Importer):
    def __init__(self):
        self.display_name = 'Arnold'
        self.material_node_pattern = '{}_mat'
        self.shadingengine_node_pattern = '{}_sg'
        self.file_node_pattern = '{}_tex'
        self.place_node_pattern = '{}_place'
        self.normal_node_pattern = '{}_normal'
        self.default_name = 'default'

    @property
    def attributes(self):
        '''
        material_node = cmds.shadingNode('aiStandardSurface', asShader=True)
        attrs = cmds.listAttr(material_node, write=True, connectable=True)
        attrs = [attr for attr in attrs if attr[-1] not in ['R', 'G', 'B', 'X', 'Y', 'Z']]
        print(attrs)
        cmds.delete(material_node)
        '''

        attrs = [
            'normalCamera',
            # 'aiEnableMatte',
            # 'aiMatteColor',
            # 'aiMatteColorA',
            # 'base',
            'baseColor',
            # 'diffuseRoughness',
            # 'specular',
            'specularColor',
            'specularRoughness',
            # 'specularAnisotropy',
            # 'specularRotation',
            'metalness',
            # 'transmission',
            'transmissionColor',
            # 'transmissionDepth',
            # 'transmissionScatter',
            # 'transmissionScatterAnisotropy',
            # 'transmissionDispersion',
            # 'transmissionExtraRoughness',
            # 'transmitAovs',
            # 'subsurface',
            'subsurfaceColor',
            # 'subsurfaceRadius',
            # 'subsurfaceScale',
            # 'subsurfaceAnisotropy',
            # 'subsurfaceType',
            # 'sheen',
            # 'sheenColor',
            # 'sheenRoughness',
            # 'thinWalled',
            # 'tangent',
            # 'coat',
            # 'coatColor',
            # 'coatRoughness',
            # 'coatAnisotropy',
            # 'coatRotation',
            # 'coatNormal',
            # 'thinFilmThickness',
            # 'emission',
            'emissionColor',
            'opacity',
            # 'caustics',
            # 'internalReflections',
            # 'exitToBackground',
            # 'indirectDiffuse',
            # 'indirectSpecular',
            # 'aovId1',
            # 'id1',
            # 'aovId2',
            # 'id2',
            # 'aovId3',
            # 'id3',
            # 'aovId4',
            # 'id4',
            # 'aovId5',
            # 'id5',
            # 'aovId6',
            # 'id6',
            # 'aovId7',
            # 'id7',
            # 'aovId8',
            # 'id8'
            ]

        return attrs

    @property
    def colorspaces(self):
        colorspaces = [
            'linear',
            'sRGB',
            'Utility - linear - sRGB'
        ]

        return colorspaces

    def get_selection(self):
        meshes = cmds.ls(selection=True, long=True)
        meshes = [(mesh.rsplit('|')[-1], mesh) for mesh in meshes]
        logging.debug(meshes)
        return meshes

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
        material_node = cmds.shadingNode('aiStandardSurface', name=material_node_name, asShader=True)
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
        if material_attribute == 'normalCamera':
            material_name = material_node.replace(self.material_node_pattern, '') #this is some bad juju
            normal_node_name = self.normal_node_pattern.format(material_name)
            normal_node = cmds.shadingNode('aiNormalMap', name=normal_node_name, asUtility=True)
            cmds.connectAttr('{}.outColor'.format(file_node), '{}.input'.format(normal_node), force=True)
            cmds.connectAttr('{}.outValue'.format(normal_node), '{}.{}'.format(material_node, material_attribute), force=True)

        elif material_attribute == 'displacement':
            # catch error
            shadingengine_node = cmds.listConnections('{}.outColor', destination=True)[0]
            cmds.connectAttr('{}.outColor'.format(file_node), '{}.displacementShader'.format(shadingengine_node), force=True)

        else:
            if cmds.getAttr('{}.{}'.format(material_node, material_attribute), type=True) == 'float':
                cmds.setAttr('{}.alphaIsLuminance'.format(file_node), True)
                file_attribute = 'outAlpha'
            else:
                file_attribute = 'outColor'
            cmds.connectAttr('{}.{}'.format(file_node, file_attribute), '{}.{}'.format(material_node, material_attribute), force=True)

    def exists(self, node_name):
        return cmds.objExists(node_name)

    def assign_material(self, material, mesh):
        cmds.select(mesh, replace=True)
        if cmds.ls(selection=True):
            cmds.hyperShade(material, assign=True)
