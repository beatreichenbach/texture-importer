from __future__ import absolute_import

from maya import cmds
import logging
from . import maya


class Importer(maya.Importer):
    def __init__(self):
        self.display_name = 'VRay'

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

        return attrs

    def create_material(self, material_node_name, shadingengine_node_name):
        material_node = cmds.shadingNode('VRayMtl', name=material_node_name, asShader=True)
        shadingengine_node = cmds.sets(name=shadingengine_node_name, empty=True, renderable=True, noSurfaceShader=True)
        cmds.connectAttr('{}.outColor'.format(material_node), '{}.surfaceShader'.format(shadingengine_node))

        return material_node, shadingengine_node

    def connect_file(self, file_node, material_node, material_attribute):
        if material_attribute == 'bumpMap':
            cmds.connectAttr('{}.outColor'.format(file_node), '{}.{}'.format(material_node, material_attribute), force=True)
            cmds.setAttr('{}.bumpMapType'.format(material_node), 1)

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
