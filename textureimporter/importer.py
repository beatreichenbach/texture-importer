import os
import glob
import re
import logging
import itertools
import json


from . import plugin_utils
from . import utils
from .utils import NotFoundException, NoSelectionException


class Importer(object):
    attributes = []
    colorspaces = []

    display_name = ''
    plugin_name = ''

    settings_group = ''
    settings_defaults = {
        'material_node_pattern': '{}_mat',
        'file_node_pattern': '{}_tex',
        'default_name': 'default',
        }

    def __init__(self):
        self.config = None
        self.path = ''
        self.settings = utils.Settings()
        self.init_settings()

    def init_settings(self):
        self.settings.beginGroup(self.settings_group)
        for setting, value in self.settings_defaults.items():
            if not self.settings.contains(setting):
                self.settings.setValue(setting, value)
        self.settings.endGroup()

    @classmethod
    def from_plugin(cls, plugin):
        cls = plugin_utils.plugin_class(cls, plugin)
        return cls()

    def load_plugin(self):
        pass

    def resolve_pattern(self, pattern, mesh='*', material='*', udim='[0-9][0-9][0-9][0-9]', mud='_u'):
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

    def resolve_name(self, pattern, *args):
        self.settings.beginGroup(self.settings_group)
        pattern_string = self.settings.value(pattern)
        self.settings.endGroup()

        try:
            name = pattern_string.format(*args)
        except Exception:
            logging.error('Failed to parse name from setting: {}'.format(pattern))
            name = '_'.join(args)

        return name

    def glob(self, pattern):
        if not pattern:
            return []

        if self.include_subfolders:
            # python 3.5>= only
            # files = glob.glob(os.path.join(self.path, '**', pattern), recursive=True)
            files = glob.glob(os.path.join(self.path, pattern))

        else:
            files = glob.glob(os.path.join(self.path, pattern))
        return files

    def exists(self, node_name):
        return False

    def get_meshes(self):
        return []

    def get_materials(self, mesh=None):
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
                # resolve_pattern returns a glob pattern. We need to escape .* to make it work for regex.
                regex_pattern = pattern.replace('.', r'\.').replace('*', r'\w+')
                match = re.search(regex_pattern, filepath)
                if match and match.group(1) not in materials:
                    material = match.group(1)
                    materials.append(material)
            break
        return materials

    def get_network(self, mesh=None, material=None):
        channels = self.config.channels

        network = Network()
        network.mesh = mesh
        network.material = material

        if mesh and material:
            material_name = '{}_{}'.format(mesh.name, material)
        elif mesh and not material:
            material_name = mesh.name
        elif not mesh and material:
            material_name = material
        else:
            material_name = self.settings.value('default_name', '')

        material_node_name = self.resolve_name('material_node_pattern', material_name)

        # remove pattern if the filename already contains the pattern
        self.settings.beginGroup(self.settings_group)
        pattern_string = self.settings.value('material_node_pattern')
        self.settings.endGroup()
        # py3.6 and before
        try:
            search_pattern = re.sub(r'{}', r'([\\w\-. ]+)', pattern_string)
        except KeyError:
            search_pattern = re.sub(r'{}', r'([\w\-. ]+)', pattern_string)

        match = re.search(search_pattern, material_name)
        if match:
            material_node_name = material_name
            material_name = match.group(1)

        mesh_name = mesh.name if mesh else None
        network.material_name = material_name
        network.material_node_name = material_node_name
        network.exists = self.exists(material_node_name)

        for channel in channels:
            patterns = self.resolve_pattern(channel.pattern, mesh=mesh_name, material=material)

            for pattern in patterns:
                files = self.glob(pattern)
                if files:
                    file_path = files[0]
                    if re.search(r'\$udim', channel.pattern):
                        # This will not work if file name contains other 4 digit strings but
                        # it's an easy way to create the file name that works in 99% of cases
                        file_name = os.path.basename(file_path)
                        file_name = re.sub(r'\d{4}', '<UDIM>', file_name)
                        file_path = os.path.join(os.path.dirname(file_path), file_name)
                    break
            else:
                file_path = ''

            material_atttribute = '{}_{}'.format(material_name, channel.attribute)
            file_node_name = self.resolve_name('file_node_pattern', material_atttribute)
            if not file_path:
                file_node_name = ''

            network_channel = NetworkChannel(network)
            network_channel.file_node_name = file_node_name
            network_channel.attribute_name = channel.attribute
            network_channel.colorspace = channel.colorspace
            network_channel.file_path = file_path
            network_channel.exists = self.exists(file_node_name)

        if not any([channel.file_path for channel in network.channels]):
            return

        return network

    def get_networks(self, path, config, include_subfolders):
        self.path = path
        self.config = config
        self.include_subfolders = include_subfolders

        networks = []

        meshes = self.get_meshes()
        if config.has_mesh and not meshes:
            raise NoSelectionException
        elif not config.has_mesh:
            # ignore mesh
            meshes = [None]

        for mesh in meshes:
            materials = self.get_materials(mesh)
            if config.has_material and not materials:
                raise NotFoundException
            elif not config.has_material:
                # ignore material
                materials = [None]

            for material in materials:
                network = self.get_network(mesh, material)
                if network:
                    networks.append(network)

        if not networks:
            raise NotFoundException

        return networks

    def create_network(self, network, **kwargs):
        pass


class Network(object):
    def __init__(self):
        self.mesh = None
        self.material = ''
        self.material_name = ''
        self.material_node_name = ''
        self.exists = False
        self.channels = []


class NetworkChannel(object):
    def __init__(self, network):
        if not isinstance(network, Network):
            raise TypeError

        self.network = network
        self.file_node_name = ''
        self.attribute_name = ''
        self.file_path = ''
        self.colorspace = ''
        self.exists = False

        network.channels.append(self)

    @property
    def file_name(self):
        return os.path.basename(self.file_path)


class Config(object):
    def __init__(self, name=''):
        self.name = name
        self.renderer = None
        self.channels = []

    @classmethod
    def from_json(cls, json_path):
        try:
            with open(json_path) as f:
                filename, extension = os.path.splitext(os.path.basename(json_path))
                data = json.load(f)
        except (ValueError, TypeError):
            logging.error('Could not import the config: {}'.format(json_path))
            return

        name = data.get('name', filename)
        config = cls(name)

        config.renderer = data.get('renderer')

        for item in data.get('channels', []):
            channel = ConfigChannel(
                attribute=item.get('attribute', ''),
                pattern=item.get('pattern', ''),
                colorspace=item.get('colorspace', ''))
            config.channels.append(channel)

        return config

    def to_json(self, json_path):
        json_data = utils.to_dict(self)
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=4)

    @property
    def has_mesh(self):
        for channel in self.channels:
            if re.search(r'\$mesh', channel.pattern):
                return True
        return False

    @property
    def has_material(self):
        for channel in self.channels:
            if re.search(r'\$material', channel.pattern):
                return True
        return False


class ConfigChannel(object):
    def __init__(self, attribute='', pattern='', colorspace=''):
        self.attribute = attribute
        self.pattern = pattern
        self.colorspace = colorspace


class Mesh(object):
    def __init__(self, mesh):
        self.mesh = mesh

    def __str__(self):
        return self.name

    @property
    def name(self):
        return str(self.mesh)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    importer = Importer.from_plugin('maya-arnold')
