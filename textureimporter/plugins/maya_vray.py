from __future__ import absolute_import

from maya import cmds
import logging
from . import maya


class Importer(maya.Importer):
    display_name = 'VRay'
    plugin_name = 'vrayformaya.mll'

    def __init__(self):
        super(Importer, self).__init__()

    @property
    def attributes(self):
        '''
        material_node = cmds.shadingNode('VRayMtl', asShader=True)
        attrs = cmds.listAttr(material_node, write=True, connectable=True)
        attrs = [attr for attr in attrs if attr[-1] not in ['R', 'G', 'B', 'X', 'Y', 'Z']]
        print(attrs)
        cmds.delete(material_node)
        '''

        attrs = [
            # 'outApiType',
            # 'outApiClassification',
            # 'reflectionsMaxDepth',
            # 'refractionsMaxDepth',
            # 'swatchAutoUpdate',
            # 'swatchAlwaysRender',
            # 'swatchExplicitUpdate',
            # 'swatchMaxRes',
            'color',
            # 'diffuseColorAmount',
            # 'roughnessAmount',
            # 'illumColor',
            # 'illumGI',
            # 'compensateExposure',
            'reflectionColor',
            # 'reflectionColorAmount',
            # 'reflectionExitColor',
            # 'hilightGlossinessLock',
            # 'hilightGlossiness',
            'reflectionGlossiness',
            # 'reflectionSubdivs',
            # 'reflectionAffectAlpha',
            # 'reflInterpolation',
            # 'reflMapMinRate',
            # 'reflMapMaxRate',
            # 'reflMapColorThreshold',
            # 'reflMapNormalThreshold',
            # 'reflMapSamples',
            # 'useFresnel',
            # 'reflectOnBackSide',
            # 'softenEdge',
            # 'fixDarkEdges',
            # 'glossyFresnel',
            # 'ggxTailFalloff',
            # 'ggxOldTailFalloff',
            'metalness',
            # 'useRoughness',
            # 'anisotropy',
            # 'anisotropyUVWGen',
            'anisotropyRotation',
            # 'anisotropyDerivation',
            # 'anisotropyAxis',
            'refractionColor',
            # 'refractionColorAmount',
            'refractionExitColor',
            # 'refractionExitColorOn',
            'refractionGlossiness',
            # 'refractionSubdivs',
            # 'refrDispersionOn',
            # 'refrDispersionAbbe',
            # 'refrInterpolation',
            # 'refrMapMinRate',
            # 'refrMapMaxRate',
            # 'refrMapColorThreshold',
            # 'refrMapNormalThreshold',
            # 'refrMapSamples',
            'fogColor',
            # 'fogMult',
            # 'fogBias',
            # 'affectShadows',
            # 'affectAlpha',
            # 'traceReflections',
            # 'traceRefractions',
            # 'cutoffThreshold',
            # 'brdfType',
            # 'bumpMapType',
            'bumpMap',
            # 'bumpMult',
            # 'bumpShadows',
            # 'bumpDeltaScale',
            # 'sssOn',
            'translucencyColor',
            'thickness',
            # 'scatterCoeff',
            # 'scatterDir',
            # 'scatterLevels',
            # 'scatterSubdivs',
            # 'sssEnvironment',
            'opacityMap',
            # 'opacityMode',
            # 'doubleSided',
            # 'useIrradianceMap',
            # 'reflectionDimDistanceOn',
            # 'reflectionDimDistance',
            # 'reflectionDimFallOff',
            # 'sheenColorAmount',
            'sheenColor',
            'sheenGlossiness',
            # 'coatColorAmount',
            'coatColor',
            'coatGlossiness',
            # 'coatBumpMapType',
            # 'coatBumpMap',
            # 'coatBumpMult',
            # 'coatBumpLock',
            # 'attributeAliasList'
            ]

        # extra attributes:
        attrs.extend([
            'normalMap',
            'displacement',
            'fresnelIOR',
            'refractionIOR',
            'reflectionRoughness',
            'illumColor'
            ])

        return attrs

    def create_material(self, material_node_name, shadingengine_node_name):
        material_node = self.create_node('VRayMtl', name=material_node_name, asShader=True)
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
        if material_attribute == 'bumpMap':
            out_connection = '{}.outAlpha'.format(file_node)
            in_connection = '{}.{}'.format(material_node, material_attribute)
            cmds.connectAttr(out_connection, in_connection, force=True)
        elif material_attribute == 'normalMap':
            out_connection = '{}.outColor'.format(file_node)
            in_connection = '{}.bumpMap'.format(material_node)
            cmds.connectAttr(out_connection, in_connection, force=True)
            cmds.setAttr('{}.bumpMapType'.format(material_node), 1)
        elif material_attribute == 'displacement':
            # instead of getting the shadingengine, this should actually use the
            # shadingengine from the create_material function
            outputs = cmds.listConnections(
                '{}.outColor'.format(material_node), destination=True, source=False, type='shadingEngine')
            if outputs:
                shadingengine_node = outputs[-1]

                out_connection = '{}.outColor'.format(file_node)
                in_connection = '{}.displacementShader'.format(shadingengine_node)
                cmds.connectAttr(out_connection, in_connection, force=True)
        else:
            if material_attribute == 'reflectionRoughness':
                material_attribute = 'reflectionGlossiness'
                cmds.setAttr('{}.useRoughness'.format(material_node), True)
                cmds.setAttr('{}.reflectionColor'.format(file_node), 1, 1, 1)

            if material_attribute == 'reflectionGlossiness':
                cmds.setAttr('{}.lockFresnelIORToRefractionIOR'.format(material_node), False)

            if cmds.getAttr('{}.{}'.format(material_node, material_attribute), type=True) == 'float':
                cmds.setAttr('{}.alphaIsLuminance'.format(file_node), True)
                file_attribute = 'outAlpha'
            else:
                file_attribute = 'outColor'

            out_connection = '{}.{}'.format(file_node, file_attribute)
            in_connection = '{}.{}'.format(material_node, material_attribute)
            cmds.connectAttr(out_connection, in_connection, force=True)
