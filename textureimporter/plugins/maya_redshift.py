from __future__ import absolute_import

from maya import cmds
import logging
from . import maya


class Importer(maya.Importer):
    def __init__(self):
        self.display_name = 'Arnold'

    @property
    def attributes(self):
        '''
        material_node = cmds.shadingNode('ReshiftMaterial', asShader=True)
        attrs = cmds.listAttr(material_node, write=True, connectable=True)
        attrs = [attr for attr in attrs if attr[-1] not in ['R', 'G', 'B', 'X', 'Y', 'Z']]
        print(attrs)
        cmds.delete(material_node)
        '''

        attrs = [
            'diffuse_color',
            # 'diffuse_weight',
            # 'diffuse_roughness',
            'transl_color',
            # 'transl_weight',
            'refl_color',
            # 'refl_weight',
            'refl_roughness',
            # 'refl_samples',
            # 'refl_brdf',
            # 'refl_aniso',
            # 'refl_aniso_rotation',
            # 'refl_fresnel_mode',
            # 'refl_reflectivity',
            # 'refl_edge_tint',
            # 'refl_ior3',
            # 'refl_ior30',
            # 'refl_ior31',
            # 'refl_ior32',
            # 'refl_k3',
            # 'refl_k30',
            # 'refl_k31',
            # 'refl_k32',
            'refl_metalness',
            # 'refl_ior',
            'refr_color',
            # 'refr_weight',
            'refr_roughness',
            # 'refr_samples',
            # 'refr_ior',
            # 'refr_abbe',
            # 'refr_thin_walled',
            # 'ss_unitsMode',
            # 'refr_transmittance',
            # 'refr_absorption_scale',
            # 'ss_extinction_coeff',
            # 'ss_extinction_scale',
            # 'ss_scatter_coeff',
            # 'ss_amount',
            # 'ss_phase',
            # 'ss_samples',
            # 'ms_amount',
            # 'ms_radius_scale',
            # 'ms_mode',
            # 'ms_samples',
            # 'ms_include_mode',
            'ms_color0',
            'ms_weight0',
            'ms_radius0',
            'ms_color1',
            'ms_weight1',
            'ms_radius1',
            'ms_color2',
            'ms_weight2',
            'ms_radius2',
            'coat_color',
            # 'coat_weight',
            'coat_roughness',
            # 'coat_samples',
            # 'coat_brdf',
            # 'coat_fresnel_mode',
            # 'coat_reflectivity',
            # 'coat_ior3',
            # 'coat_ior30',
            # 'coat_ior31',
            # 'coat_ior32',
            # 'coat_ior',
            # 'coat_transmittance',
            # 'coat_thickness',
            # 'coat_bump_input',
            'overall_color',
            'opacity_color',
            'emission_color',
            # 'emission_weight',
            'bump_input',
            # 'depth_override',
            # 'refl_depth',
            # 'refl_enablecutoff',
            # 'refl_cutoff',
            # 'skip_inside_refl',
            # 'refl_endmode',
            # 'refr_depth',
            # 'refr_enablecutoff',
            # 'refr_cutoff',
            # 'combined_depth',
            # 'diffuse_direct',
            # 'diffuse_indirect',
            # 'refl_direct',
            # 'refl_indirect',
            # 'refl_isGlossiness',
            # 'coat_direct',
            # 'coat_indirect',
            # 'coat_isGlossiness',
            # 'refr_isGlossiness',
            # 'decoupleIORFromRoughness',
            # 'shadow_opacity',
            # 'affects_alpha',
            # 'block_volumes',
            # 'energyCompMode',
            # 'overallAffectsEmission',
            # 'anisotropy_orientation'
            ]

        return attrs

    def create_material(self, material_node_name, shadingengine_node_name):
        material_node = cmds.shadingNode('ReshiftMaterial', name=material_node_name, asShader=True)
        shadingengine_node = cmds.sets(name=shadingengine_node_name, empty=True, renderable=True, noSurfaceShader=True)
        cmds.connectAttr('{}.outColor'.format(material_node), '{}.surfaceShader'.format(shadingengine_node))

        return material_node, shadingengine_node

    def connect_file(self, file_node, material_node, material_attribute):
        if material_attribute == 'bump_input':
            material_name = material_node.replace(self.material_node_pattern, '') #this is some bad juju
            normal_node_name = self.normal_node_pattern.format(material_name)
            normal_node = cmds.shadingNode('RedshiftBumpMap', name=normal_node_name, asUtility=True)
            # cmds.setAttr('{}.space'.format(normal_node), 'TangentSpaceNormal', type='string')
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
