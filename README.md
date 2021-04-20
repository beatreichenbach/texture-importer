# texture-importer
A texture importer tool that creates material networks

## Installation for Maya

1. Click on the code button above and download the package as a .zip file.
2. Unpack the zip archive.
3. Drag the setup_maya.mel file into the viewport of maya.
4. This creates a button on the shelf that can be used to launch the tool.

If you prefer to install the package manually, just make sure that the textureimporter directory can be loaded as a python package by maya and call the tool with the following code:
```
from textureimporter.plugins.maya import run
main_window = run()
```

## Configs

Configs are presets that store different patterns for texture names.
