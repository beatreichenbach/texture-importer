import os
import logging
import json
from PySide2 import QtWidgets, QtCore, QtGui


def sorted_dict(dict):
    return sorted(dict, key=lambda i: i[0].replace(' ', '').lower())


def to_dict(obj):
    return json.loads(
        json.dumps(obj, default=lambda o: getattr(o, '__dict__', str(o)))
    )


class Settings(QtCore.QSettings):
    def __init__(self):
        self.settings_path = os.path.dirname(__file__)
        self.configs_path = os.path.join(self.settings_path, 'configs')

        try:
            if not os.access(self.settings_path, os.W_OK):
                raise PermissionError
        except PermissionError:
            self.settings_path = os.path.join(os.path.expanduser("~"), '.textureimporter')

        settings_file_path = os.path.join(self.settings_path, 'settings.ini')
        super(Settings, self).__init__(settings_file_path, QtCore.QSettings.IniFormat)

        self.init_defaults()

        custom_configs_path = self.value('user/configs_path', '')
        if custom_configs_path:
            self.configs_path = custom_configs_path

    def init_defaults(self):
        self.beginGroup('user')
        default_values = {
            'num_recent_paths': 10,
            'configs_path': ''
        }
        for key, value in default_values.items():
            if key not in self.childKeys():
                self.setValue(key, value)
        self.endGroup()

    def bool(self, key):
        value = self.value(key, False)
        if isinstance(value, bool):
            return value
        else:
            if isinstance(value, str):
                return value.lower() == 'true'
            else:
                return bool(value)

    def list(self, key):
        value = self.value(key, [])
        # py2.7
        try:
            if isinstance(value, basestring):
                value = [value, ]
        except NameError:
            if isinstance(value, str):
                value = [value, ]
        return value

    def clear(self):
        super(Settings, self).clear()
        self.init_defaults()


class Config(object):
    def __init__(self, name=''):
        self.name = name
        self.renderer = None
        self.channels = []

    @classmethod
    def from_json(cls, json_path):
        with open(json_path) as f:
            name, extension = os.path.splitext(os.path.basename(json_path))
            data = json.load(f)

        config = cls(name)

        config.renderer = data.get('renderer', '')

        for item in data.get('channels', []):
            channel = ConfigChannel(
                attribute=item.get('attribute', ''),
                pattern=item.get('pattern', ''),
                colorspace=item.get('colorspace', ''))
            config.channels.append(channel)

        return config

    def to_json(self, json_path):
        json_data = to_dict(self)
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=4)


class ConfigChannel(object):
    def __init__(self, attribute='', pattern='', colorspace=''):
        self.attribute = attribute
        self.pattern = pattern
        self.colorspace = colorspace


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    settings = Settings()
