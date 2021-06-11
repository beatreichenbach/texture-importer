setup_dir = getFilenamePath(getSourceFileName())
setup_dir = trimright setup_dir "\\/"
cwd = getFilenamePath(setup_dir)
cwd = trimright cwd "\\/"
code = "import sys; cwd = r'" + cwd + "'; sys.path.insert(1, cwd); from textureimporter import setup; setup.Installer.install('max'); del setup; sys.path.remove(cwd)"
python.Execute code
