import importlib
import pkgutil
import sys
import logging
import re
from PySide2 import QtWidgets

import plugins


def dcc_plugins():
    _plugins = all_plugins()
    dcc_plugins = {key: value for key, value in _plugins.items() if '_' not in key}
    return dcc_plugins


def all_plugins():
    _plugins = {
        name.split('.')[-1]: name # importlib.import_module(name)
        for finder, name, ispkg in iter_namespace(plugins)
    }
    return _plugins


def render_plugins(dcc):
    _plugins = all_plugins()
    pattern = re.compile('{}_'.format(re.escape(dcc)))
    render_plugins = {}
    for key, value in _plugins.items():
        if pattern.match(key):
            name = pattern.sub('', key)
            render_plugins[name] = value
    return render_plugins

def render_plugin(dcc, renderer):
    name = '{}_{}'.format(dcc, renderer)
    return all_plugins().get(name)

def iter_namespace(ns_pkg):
    # Specifying the second argument (prefix) to iter_modules makes the
    # returned name an absolute name instead of a relative one. This allows
    # import_module to work without having to do additional modification to
    # the name.
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + '.')


if __name__ == '__main__':
    logging.error(plugins.__path__)
