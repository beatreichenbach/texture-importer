from __future__ import absolute_import

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

try:
    from textureimporter import plugin_utils
    from textureimporter import utils
except ImportError:
    from . import plugin_utils
    from . import utils


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
        result = installer.install_package()
        utils.unload_modules()
        return result

    @classmethod
    def update(cls, dcc=None):
        cls = plugin_utils.plugin_class(cls, dcc)
        installer = cls(dcc)
        logging.info('Updating {}...'.format(os.path.basename(installer.package_path)))
        result = installer.update_package()
        return result

    def install_package(self):
        # nothing to install when no dcc defined
        logging.info('Installation not completed. Please see log.')
        return False

    def update_package(self):
        # Pyhon 3.7 only:
        # tmp_dir = tempfile.TemporaryDirectory(prefix=self.package_name)
        # tmp_dir = tmpdir.name
        tmp_dir = tempfile.mkdtemp(prefix=self.package_name)
        try:
            logging.info('Downloading and unzipping file: {}'.format(self.url))
            tmp_file = tempfile.NamedTemporaryFile(prefix=self.package_name, suffix='.zip', delete=False)
            with closing(urllib.urlopen(self.url)) as url_file:
                with tmp_file as file:
                    file.write(url_file.read())
            with zipfile.ZipFile(tmp_file.name, 'r') as zip_file:
                zip_file.extractall(tmp_dir)
            os.remove(tmp_file.name)

            for root, dir_names, file_names in os.walk(tmp_dir):
                if self.package_name in dir_names:
                    installer_path = root
                    break
            else:
                logging.error('Could not find {} in {}'.format(self.package_name, tmp_dir))
                raise EnvironmentError

            sys.path.insert(1, installer_path)
            try:
                utils.unload_modules()
                logging.debug('Loading temp setup module.')
                from textureimporter import setup
                logging.debug('Installing from temp directory.')
                setup.Installer.install(self.dcc)
                logging.debug('Deleting setup module.')
                del setup
            except Exception as e:
                raise e
            finally:
                sys.path.remove(installer_path)

        except Exception as e:
            logging.error(e.format_exc())
            logging.error('Update failed. Please see log.')
            return False
        finally:
            # For python 2.7 only, see above.
            shutil.rmtree(tmp_dir)

        logging.info('Update successful.')
        return True

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
