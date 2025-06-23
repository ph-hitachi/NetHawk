import pathlib

from nethawk.core.utils import import_all_submodules

# Automatically import all modules in this package when imported
import_all_submodules(__name__, pathlib.Path(__file__).parent)