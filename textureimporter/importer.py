import os
import glob
import re
import logging
import itertools
import importlib


class Importer(object):
    config = None
    path = ''
    material_node_pattern = '{}_mat'
    file_node_pattern = '{}_tex'
    default_name = 'default'
    attributes = []

    def __init__(self):
        return

    @classmethod
    def from_plugin(cls, dcc, renderer):
        try:
            plugin = '.{}_{}'.format(dcc, renderer)
            # using empty package for testing
            package = '{}.plugins'.format(__package__ or '')
            module = importlib.import_module(plugin, package=package)
            cls = getattr(module, cls.__name__)
        except ImportError as e:
            logging.error(e)
            logging.error(
                'Could not find plugin, using no plugin instead. '
                '(dcc: {}, renderer: {})'.format(dcc, renderer))
        return cls()

    def resolve_pattern(self, pattern, mesh='*', material='*', udim='[0-9][0-9][0-9][0-9]'):
        # turn parantheses into optional groups in regex style
        pattern = re.sub(r'\(([^\|]+?)\)', r'(\g<1>|)', pattern)

        # turn optional patterns into different options
        options = []
        matches = re.findall(r'\(.+?\)', pattern)
        for match in matches:
            x = [(match, part) for part in match[1:-1].split('|')]
            options.append(x)

        resolved_patterns = []
        for option in itertools.product(*options):
            resolved_pattern = pattern
            for (key, value) in option:
                resolved_pattern = re.sub(re.escape(key), value, resolved_pattern)

            if mesh:
                resolved_pattern = re.sub(r'\$mesh', mesh, resolved_pattern)
            if material:
                resolved_pattern = re.sub(r'\$material', material, resolved_pattern)
            if udim:
                resolved_pattern = re.sub(r'\$udim', udim, resolved_pattern)
            resolved_patterns.append(resolved_pattern)

        return resolved_patterns

    def glob(self, pattern):
        if self.include_subfolders:
            # python 3.5>= only
            # files = glob.glob(os.path.join(self.path, '**', pattern), recursive=True)
            files = glob.glob(os.path.join(self.path, pattern))

        else:
            files = glob.glob(os.path.join(self.path, pattern))

        return files

    def exists(self, node_name):
        return False

    def get_selection(self):
        return [(None, None)]

    def get_meshes(self):
        # loop through channels and find meshes
        for channel in self.config.channels:
            if re.findall(r'\$mesh', channel.pattern):
                # call getselection function and return
                return self.get_selection()

        return [(None, None)]

    def get_materials(self, mesh):
        channels = self.config.channels
        materials = []
        # per mesh loop through channel and find materials
        for channel in channels:
            # find all materials per mesh
            if not re.findall(r'\$material', channel.pattern):
                continue

            filepaths = []
            patterns = self.resolve_pattern(channel.pattern, mesh=mesh)
            for pattern in patterns:
                filepaths.extend(self.glob(pattern))

            # create one network per material
            patterns = self.resolve_pattern(channel.pattern, mesh=mesh, material=r'(\\w+?)')
            for (pattern, filepath) in itertools.product(patterns, filepaths):
                # if we found a material add it to the list and create a network
                match = re.search(pattern, filepath)
                if match and match.group(1) not in materials:
                    material = match.group(1)
                    materials.append(material)
            break
        else:
            # if no materials have been found create a default material
            materials = [None]

        return materials

    def get_network(self, mesh, material):
        channels = self.config.channels

        material_name = '_'.join(filter(None, [mesh, material])) or self.default_name
        material_node_name = self.material_node_pattern.format(material_name)

        network = Network()
        network.mesh_name = mesh
        network.material_name = material_name
        network.material_node_name = material_node_name
        network.exists = self.exists(material_node_name)

        for channel in channels:
            patterns = self.resolve_pattern(channel.pattern, mesh=mesh, material=material)

            for pattern in patterns:
                files = self.glob(pattern)
                if files:
                    # This will not work if file name contains other 4 digit strings but
                    # it's an easy way to create the file name that works in 99% of cases
                    file_name = re.sub(r'\d{4}', '<UDIM>', os.path.basename(files[0]))
                    break
            else:
                file_name = ''

            if not file_name:
                continue

            file_path = os.path.join(self.path, file_name)
            material_atttribute = '{}_{}'.format(material_name, channel.attribute)
            file_node_name = self.file_node_pattern.format(material_atttribute)

            network_channel = NetworkChannel(network)
            network_channel.attribute_name = channel.attribute
            network_channel.file_node_name = file_node_name
            network_channel.colorspace = channel.colorspace
            network_channel.file_path = file_path
            network_channel.exists = self.exists(file_node_name)

        if not network.channels:
            return

        return network

    def get_networks(self, path, config, include_subfolders):
        self.path = path
        self.config = config
        self.include_subfolders = include_subfolders

        networks = []
        for (mesh_name, mesh) in self.get_meshes():
            for material in self.get_materials(mesh_name):
                network = self.get_network(mesh_name, material)
                if network:
                    networks.append(network)

        return networks


class Network(object):
    def __init__(self):
        self.material_name = ''
        self.mesh_name = ''
        self.channels = []
        self.exists = False

    # @property
    # def material_node_name(self):
    #     return self.material_node_pattern.format(self.material_name)

    # @property
    # def exists(self):
    #     return False


class NetworkChannel(object):
    def __init__(self, network):
        self.network = network
        self.attribute_name = ''
        self.file_path = ''
        self.colorspace = ''
        self.file_node = ''
        self.exists = False

        network.channels.append(self)

    # @property
    # def file_node_name(self):
    #     material_atttribute = '{}_{}'.format(self.network.material_name, self.attribute_name)
    #     return self.file_node_pattern.format(material_atttribute)

    # @property
    # def exists(self):
    #     return False


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    importer = Importer.from_plugin('maya', 'arnold')
