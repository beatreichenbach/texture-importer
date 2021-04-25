from __future__ import absolute_import

from maya import cmds
import logging
from . import maya


class Importer(maya.Importer):
    display_name = 'Arnold'
    plugin_name = 'mtoa.mll'

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

        # extra attributes:
        attrs.extend([
            'bump',
            'displacement'
            ])

        return attrs

    def create_material(self, material_node_name, shadingengine_node_name):
        material_node = self.create_node('aiStandardSurface', name=material_node_name, asShader=True)
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

    def connect_file(self, file_node, material_node, material_attribute):
        if material_attribute == 'normalCamera':
            normal_node_name = self.resolve_name('normal_node_pattern', self.current_network.material_name)
            normal_node = self.create_node('aiNormalMap', name=normal_node_name, asUtility=True)

            out_connection = '{}.outColor'.format(file_node)
            in_connection = '{}.input'.format(normal_node)
            cmds.connectAttr(out_connection, in_connection, force=True)

            out_connection = '{}.outValue'.format(normal_node)
            in_connection = '{}.{}'.format(material_node, material_attribute)
            cmds.connectAttr(out_connection, in_connection, force=True)
        elif material_attribute == 'bump':
            bump_node = self.create_node('bump2d', asUtility=True)

            out_connection = '{}.outAlpha'.format(file_node)
            in_connection = '{}.bumpValue'.format(bump_node)
            cmds.connectAttr(out_connection, in_connection, force=True)

            out_connection = '{}.outNormal'.format(bump_node)
            in_connection = '{}.{}'.format(material_node, material_attribute)
            cmds.connectAttr(out_connection, in_connection, force=True)
        elif material_attribute == 'displacement':
            # catch error
            shadingengine_node = cmds.listConnections('{}.outColor', destination=True)[0]

            out_connection = '{}.outColor'.format(file_node)
            in_connection = '{}.displacementShader'.format(shadingengine_node)
            cmds.connectAttr(out_connection, in_connection, force=True)

        else:
            if cmds.getAttr('{}.{}'.format(material_node, material_attribute), type=True) == 'float':
                cmds.setAttr('{}.alphaIsLuminance'.format(file_node), True)
                file_attribute = 'outAlpha'
            else:
                file_attribute = 'outColor'

            out_connection = '{}.{}'.format(file_node, file_attribute)
            in_connection = '{}.{}'.format(material_node, material_attribute)
            cmds.connectAttr(out_connection, in_connection, force=True)
