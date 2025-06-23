import importlib
import logging
import pkgutil
import pathlib

from pathlib import Path

def get_nethawk_dir():
    """Get or create the .nethawk directory in user's home folder."""
    home = Path.home()
    nethawk_dir = home / ".nethawk"
    nethawk_dir.mkdir(exist_ok=True)
    return nethawk_dir

def print_help_section(title, entries, formatter):
    print(f"[ {title} ]")
    for entry in entries:
        print(f"    {formatter(entry)}")
    print()

def print_help_from_yaml(data):
    # Section configuration: key -> (Title, 
    #  function)
    section_map = {
        "usage": ("Usage", lambda x: x),
        "positional": ("Positional", lambda x: f"{x['name']:25} {x['description']}"),
        "services": ("Services", lambda x: f"{x['name']:25} {x['description']}"),
        "general_flags": ("General", lambda x: f"{', '.join(x['flags']):25} {x['description']}"),
        "modules": ("Modules", lambda x: f"{', '.join(x['flags']):25} {x['description']}"),
        "debugging": ("Debugging", lambda x: f"{', '.join(x['flags']):25} {x['description']}"),
        "examples": ("Examples", lambda x: x),
    }

    for key, (title, formatter) in section_map.items():
        entries = data.get(key)
        if entries:
            print_help_section(title, entries, formatter)

def import_all_submodules(package_name: str, package_path: pathlib.Path) -> None:
    """
    Recursively import all submodules in a package, including nested packages.
    Skips modules that start with '_'.
    """
    if not package_path.exists():
        raise FileNotFoundError(f"Package path '{package_path}' does not exist.")

    for module_info in pkgutil.walk_packages(
        [str(package_path)],
        prefix=package_name + ".",
        onerror=lambda x: None
    ):
        name = module_info.name
        if not name.split(".")[-1].startswith("_"):
            try:
                logging.debug(f'Importing {name}')
                importlib.import_module(name)
            except Exception as e:
                raise e