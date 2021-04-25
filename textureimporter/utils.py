import os
import logging
import json
from PySide2 import QtWidgets, QtCore, QtGui
import sys


def join_url(url, *urls):
    urls = list(urls)
    urls.insert(0, url)
    return '/'.join([s.strip('/') for s in urls])


def sorted_dict(dict):
    return sorted(dict, key=lambda i: i[0].replace(' ', '').lower())


def to_dict(obj):
    return json.loads(
        json.dumps(obj, default=lambda o: getattr(o, '__dict__', str(o)))
    )


def unload_modules():
    for module in sys.modules.values():
        if module and module.__name__.startswith(__package__):
            logging.debug('Unloading module: {}'.format(module.__name__))
            del sys.modules[module.__name__]


class Settings(QtCore.QSettings):
    def __init__(self):
        self.settings_path = os.path.dirname(__file__)
        self.configs_path = os.path.join(self.settings_path, 'configs')

        if not os.access(self.settings_path, os.W_OK):
            home_path = os.path.join(os.path.expanduser("~"), '.{}'.format(__package__))
            self.settings_path = home_path

        settings_file_path = os.path.join(self.settings_path, 'settings.ini')
        super(Settings, self).__init__(settings_file_path, QtCore.QSettings.IniFormat)

        self.init_defaults()

        custom_configs_path = self.value('general/configs_path', '')
        if custom_configs_path:
            self.configs_path = custom_configs_path

    def init_defaults(self):
        self.beginGroup('general')
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


class NoSelectionException(Exception):
    message = 'Nothing selected.'


class NotFoundException(Exception):
    message = 'Not found.'


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    settings = Settings()
