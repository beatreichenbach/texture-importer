from __future__ import absolute_import

from . import max

import pymxs
rt = pymxs.runtime


class Importer(max.Importer):
    display_name = 'VRay'
    plugin_name = 'V_Ray'

    def __init__(self):
        super(Importer, self).__init__()

    @property
    def attributes(self):
        '''
        import pymxs
        rt = pymxs.runtime
        mat = rt.VRayMtl()
        for prop in rt.getPropNames(mat):
            prop = str(prop)
            if 'texmap_' in prop:
                print(prop.replace('texmap_', ''))
        '''

        attrs = [
            'diffuse',
            # 'diffuse_on',
            # 'diffuse_multiplier',
            'reflection',
            # 'reflection_on',
            # 'reflection_multiplier',
            'refraction',
            # 'refraction_on',
            # 'refraction_multiplier',
            'bump',
            # 'bump_on',
            # 'bump_multiplier',
            'reflectionGlossiness',
            # 'reflectionGlossiness_on',
            # 'reflectionGlossiness_multiplier',
            'refractionGlossiness',
            # 'refractionGlossiness_on',
            # 'refractionGlossiness_multiplier',
            'refractionIOR',
            # 'refractionIOR_on',
            # 'refractionIOR_multiplier',
            'displacement',
            # 'displacement_on',
            # 'displacement_multiplier',
            'translucent',
            # 'translucent_on',
            # 'translucent_multiplier',
            # 'environment',
            # 'environment_on',
            # 'hilightGlossiness',
            # 'hilightGlossiness_on',
            # 'hilightGlossiness_multiplier',
            'reflectionIOR',
            # 'reflectionIOR_on',
            # 'reflectionIOR_multiplier',
            'opacity',
            # 'opacity_on',
            # 'opacity_multiplier',
            'roughness',
            # 'roughness_on',
            # 'roughness_multiplier',
            # 'anisotropy',
            # 'anisotropy_on',
            # 'anisotropy_multiplier',
            # 'anisotropy_rotation',
            # 'anisotropy_rotation_on',
            # 'anisotropy_rotation_multiplier',
            # 'refraction_fog',
            # 'refraction_fog_on',
            # 'refraction_fog_multiplier',
            'self_illumination',
            # 'self_illumination_on',
            # 'self_illumination_multiplier',
            # 'gtr_tail_falloff',
            # 'gtr_tail_falloff_on',
            # 'gtr_tail_falloff_multiplier',
            'metalness',
            # 'metalness_on',
            # 'metalness_multiplier',
            'sheen',
            # 'sheen_on',
            # 'sheen_multiplier',
            'sheen_glossiness',
            # 'sheen_glossiness_on',
            # 'sheen_glossiness_multiplier',
            'coat_color',
            # 'coat_color_on',
            # 'coat_color_multiplier',
            # 'coat_amount',
            # 'coat_amount_on',
            # 'coat_amount_multiplier',
            'coat_glossiness',
            # 'coat_glossiness_on',
            # 'coat_glossiness_multiplier',
            # 'coat_ior',
            # 'coat_ior_on',
            # 'coat_ior_multiplier',
            # 'coat_bump',
            # 'coat_bump_on',
            # 'coat_bump_multiplier',
            ]

        # extra attributes:
        attrs.extend([
            'normal',
            'reflectionRoughness',
            ])

        return attrs

    @property
    def colorspaces(self):
        colorspaces = [
            'Default',
            'sRGB',
            'ACEScg',
            'Raw'
        ]

        return colorspaces

    def create_material(self, material_node_name):
        material_node = self.create_node('VrayMtl', name=material_node_name)
        return material_node

    def create_file(self, name, file_path, colorspace):
        file_node = rt.VRayBitmap(name=name)
        file_node.HDRIMapName = file_path
        file_node.color_space = self.colorspaces.index(colorspace)
        return file_node

    def connect_file(self, file_node, material_node, material_attribute):
        if material_attribute == 'normal':
            normal_node_name = self.resolve_name('normal_node_pattern', self.current_network.material_name)
            normal_node = self.create_node('VRayNormalMap', name=normal_node_name)

            normal_node.normal_map = file_node
            normal_node.flip_green = True
            material_node.texmap_bump = normal_node
        elif material_attribute == 'reflectionRoughness':
            material_attribute = 'texmap_reflectionGlossiness'
            material_node.brdf_useRoughness = True
            setattr(material_node, material_attribute, file_node)
        else:
            material_attribute = 'texmap_' + material_attribute
            setattr(material_node, material_attribute, file_node)
