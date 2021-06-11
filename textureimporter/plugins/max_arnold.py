from __future__ import absolute_import

from . import max

import pymxs
rt = pymxs.runtime


class Importer(max.Importer):
    display_name = 'Arnold'
    plugin_name = 'Arnold'

    def __init__(self):
        super(Importer, self).__init__()

    @property
    def attributes(self):
        '''
        import pymxs
        rt = pymxs.runtime
        mat = rt.ai_standard_surface()
        for prop in rt.getPropNames(mat):
            if '_shader' in str(prop):
                print(prop.replace('_shader', ''))
        '''

        attrs = [
            # 'base',
            'base_color',
            'diffuse_roughness',
            # 'specular',
            'specular_color',
            'specular_roughness',
            'specular_IOR',
            # 'specular_anisotropy',
            # 'specular_rotation',
            'metalness',
            # 'transmission',
            'transmission_color',
            # 'transmission_depth',
            # 'transmission_scatter',
            # 'transmission_scatter_anisotropy',
            # 'transmission_dispersion',
            # 'transmission_extra_roughness',
            'subsurface',
            'subsurface_color',
            'subsurface_radius',
            # 'subsurface_scale',
            # 'subsurface_anisotropy',
            # 'sheen',
            'sheen_color',
            'sheen_roughness',
            'normal',
            # 'tangent',
            # 'coat',
            'coat_color',
            'coat_roughness',
            # 'coat_IOR',
            # 'coat_anisotropy',
            # 'coat_rotation',
            # 'coat_normal',
            # 'coat_affect_color',
            # 'coat_affect_roughness',
            # 'thin_film_thickness',
            # 'thin_film_IOR',
            # 'emission',
            'emission_color',
            'opacity',
            # 'id1',
            # 'id2',
            # 'id3',
            # 'id4',
            # 'id5',
            # 'id6',
            # 'id7',
            # 'id8',
            ]

        # extra attributes:
        attrs.extend([
            'bump',
            'displacement'
            ])

        return attrs

    def create_material(self, material_node_name):
        material_node = self.create_node('ai_standard_surface', name=material_node_name)
        return material_node

    def create_file(self, name, file_path, colorspace):
        file_node = rt.ai_image(name=name)
        file_node.filename = file_path
        file_node.color_space = self.colorspaces.index(colorspace)
        return file_node

    def connect_file(self, file_node, material_node, material_attribute):
        if material_attribute == 'normal':
            normal_node_name = self.resolve_name('normal_node_pattern', self.current_network.material_name)
            normal_node = self.create_node('ai_normal_map', name=normal_node_name)

            normal_node.input_shader = file_node
            material_node.normal_shader = normal_node
        elif material_attribute == 'bump':
            bump_node = self.create_node('ai_bumo2d')

            bump_node.bump_map_shader = file_node
            material_node.normal_shader = bump_node
        elif material_attribute == 'displacement':
            # just appending it to id8 instead of assigning to mesh
            material_node.id8_shader = file_node
            material_node.id8_connected = False
        else:
            material_attribute += '_shader'
            setattr(material_node, material_attribute, file_node)
