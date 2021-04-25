from __future__ import absolute_import

from maya import cmds
import logging
from . import maya


class Importer(maya.Importer):
    display_name = 'Redshift'
    plugin_name = 'redshift4maya.mll'

    def __init__(self):
        super(Importer, self).__init__()

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

        # extra attributes:
        attrs.extend([
            'normal_input',
            'displacement'
            ])

        return attrs

    def create_material(self, material_node_name, shadingengine_node_name):
        material_node = self.create_node('RedshiftMaterial', name=material_node_name, asShader=True)
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
        if material_attribute == 'normal_input':
            normal_node_name = self.resolve_name('normal_node_pattern', self.current_network.material_name)
            normal_node = cmds.shadingNode('RedshiftBumpMap', name=normal_node_name, asUtility=True)

            out_connection = '{}.outColor'.format(file_node)
            in_connection = '{}.input'.format(normal_node)
            cmds.connectAttr(out_connection, in_connection, force=True)

            out_connection = '{}.outValue'.format(normal_node)
            in_connection = '{}.bump_input'.format(material_node)
            cmds.connectAttr(out_connection, in_connection, force=True)
        elif material_attribute == 'bump_input':
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
