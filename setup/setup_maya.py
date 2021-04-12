import os
import sys
import logging
import shutil


def create_button():
    from maya import mel, cmds

    shelf_name = 'Plugins'

    label = 'textureimporter'
    image_path = 'textureEditor.png'
    command = (
        'from textureimporter.plugins.maya import run\n'
        'main_window = run()')

    top_level_shelf = mel.eval('$gShelfTopLevel = $gShelfTopLevel;')

    if cmds.shelfLayout(shelf_name, exists=True):
        buttons = cmds.shelfLayout(shelf_name, query=True, childArray=True) or []
        for button in buttons:
            if cmds.shelfButton(button, label=True, query=True) == label:
                cmds.deleteUI(button)
    else:
        mel.eval('addNewShelfTab "{}";'.format(shelf_name))

    cmds.shelfButton(label=label, command=command, parent=shelf_name, image=image_path)
    logging.info('Created button "{}"" on shelf "{}".'.format(label, shelf_name))
    return cmds.saveAllShelves(top_level_shelf)


def install():
    logging.info('Installing textureimporter...')

    maya_app_dir = os.path.normpath(os.getenv('MAYA_APP_DIR'))
    if maya_app_dir is None:
        if sys.platform.startswith('win32'):
            maya_app_dir = os.path.join(os.path.expanduser("~"), 'Documents', 'Maya')
        elif sys.platform.startswith('linux'):
            maya_app_dir = os.path.join(os.path.expanduser("~"), 'Maya')
        elif sys.platform.startswith('darwin'):
            maya_app_dir = os.path.join(os.path.expanduser("~"), 'Library', 'Preferences', 'Autodesk', 'Maya')

    if not maya_app_dir:
        logging.error('Could not find maya scripts directory.')
        return False

    scripts_dir = os.path.join(maya_app_dir, 'scripts')
    if not os.path.isdir(scripts_dir):
        os.makedirs(scripts_dir)

    source_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'textureimporter'))
    destination_path = os.path.join(scripts_dir, 'textureimporter')
    if os.path.exists(destination_path):
        logging.error(
            'Path already exists in the maya scripts directory: '
            '{}'.format(destination_path))
        return False

    try:
        shutil.copytree(source_path, destination_path)
        logging.info(
            'Package has been successfully copied to the maya scripts directory: '
            '{}'.format(scripts_dir))
    except OSError:
        logging.error(
            'Failed to copy package to the maya scripts directory. \nPackage path: {}\n'
            'Maya script path: {}'.format(source_path, destination_path))
        return False

    try:
        create_button()
    except ModuleNotFoundError:
        logging.error(
            'Could not install maya script button. '
            'Make sure to run the setup from Maya.')
        return False

    logging.info('Installation successfull.')
    return True


if __name__ == '__main__':
    logging.basicConfig(format='textureimporter: %(message)s', level=logging.INFO)
    install()
