from __future__ import absolute_import

from maya import cmds
import logging
from . import maya


class Importer(maya.Importer):
    display_name = 'Arnold'

    def __init__(self):
        super(Importer, self).__init__()

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

    def create_material(self, material_node_name, shadingengine_node_name):
        material_node = cmds.shadingNode('aiStandardSurface', name=material_node_name, asShader=True)
        shadingengine_node = cmds.sets(name=shadingengine_node_name, empty=True, renderable=True, noSurfaceShader=True)
        cmds.connectAttr('{}.outColor'.format(material_node), '{}.surfaceShader'.format(shadingengine_node))

        return material_node, shadingengine_node

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
