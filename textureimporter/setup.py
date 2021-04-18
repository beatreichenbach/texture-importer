import os
import sys
import logging
import shutil
import tempfile
import glob
import zipfile
try:
    import urllib.request as urllib
except ImportError:
    import urllib2 as urllib
from contextlib import closing

import plugin_utils
import utils


class Installer(object):
    def __init__(self, dcc=None):
        self.package_path = os.path.normpath(os.path.dirname(__file__))
        self.package_name = os.path.basename(self.package_path)
        self.dcc = dcc
        self.url = 'https://github.com/beatreichenbach/texture-importer/archive/refs/heads/main.zip'

    @classmethod
    def install(cls, dcc=None):
        cls = plugin_utils.plugin_class(cls, dcc)
        installer = cls(dcc)
        logging.info('Installing {}...'.format(os.path.basename(installer.package_path)))
        installer.install_package()
        utils.unload_modules()

    @classmethod
    def update(cls, dcc=None):
        cls = plugin_utils.plugin_class(cls, dcc)
        installer = cls(dcc)
        logging.info('Updating {}...'.format(os.path.basename(installer.package_path)))
        installer.update_package()
        utils.unload_modules()

    def install_package(self):
        # nothing to install when no dcc defined
        logging.info('Installation not completed. Please see log.')

    def update_package(self):
        # Pyhon 3.7 only:
        # tmp_dir = tempfile.TemporaryDirectory(prefix=self.package_name)
        # tmp_dir = tmpdir.name
        tmp_dir = tempfile.mkdtemp(prefix=self.package_name)

        tmp_file = tempfile.NamedTemporaryFile(prefix=self.package_name, suffix='.zip', delete=False)
        with closing(urllib.urlopen(self.url)) as url_file:
            with tmp_file as file:
                file.write(url_file.read())

        with zipfile.ZipFile(tmp_file.name, 'r') as zip_file:
            zip_file.extractall(tmp_dir)

        os.remove(tmp_file.name)

        installer_path = None
        for root, dir_names, file_names in os.walk(tmp_dir):
            if self.package_name in dir_names:
                installer_path = root
                break
        else:
            logging.error('Could not find {} in {}'.format(self.package_name, tmp_dir))

        if installer_path is not None:
            sys.path.insert(1, installer_path)
            from textureimporter import setup
            setup.Installer.install(self.dcc)
            del setup
            sys.path.remove(installer_path)

        # For python 2.7 only, see above.
        shutil.rmtree(tmp_dir)

    def copy_package(self, path):
        destination_path = os.path.join(path, self.package_name)
        if os.path.isdir(destination_path):
            # Pyhon 3.7 only:
            # tmp_dir = tempfile.TemporaryDirectory(prefix=self.package_name)
            # tmp_dir = tmpdir.name
            tmp_dir = tempfile.mkdtemp(prefix=self.package_name)
            tmp_path = os.path.join(tmp_dir, self.package_name)
            shutil.copytree(self.package_path, tmp_path)

            # preserving user data
            user_files = []
            user_files.extend(glob.glob(os.path.join(destination_path, 'configs', '*.json')))
            user_files.extend(glob.glob(os.path.join(destination_path, '*.ini')))
            for user_file in user_files:
                tmp_user_path = os.path.join(tmp_path, os.path.relpath(user_file, destination_path))
                shutil.copy(user_file, tmp_user_path)

            logging.info('Updating existing installation...')
            self.package_path = tmp_path
            shutil.rmtree(destination_path)

        try:
            shutil.copytree(self.package_path, destination_path)
            logging.info(
                'Package has been successfully installed: {}'.format(destination_path))
            return True
        except OSError:
            logging.error(
                'Failed to install package. \n'
                'Source path: {}\n'
                'Destination path: {}'.format(self.package_path, destination_path))
            return False
        finally:
            # For python 2.7 only, see above.
            if 'tmp_dir' in locals():
                shutil.rmtree(tmp_dir)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    installer_ = Installer()
    installer_.install_package(r'D:\files\settings\maya\scripts')
