# nethawk/cli/options.py

import sys
import yaml
import logging
import argparse

from typing import Tuple
from rich.console import Console
from rich.table import Table
from rich import box

from nethawk.core.utils import print_help_from_yaml
from nethawk.core.registry import register_service, service_registry, module_registry
from nethawk.core.config import Config

import resources

from importlib.resources import files
# import importlib.resources as pkg_resources

class Options:
    DEFAULT_HELP_NAME = "help.yaml"

    def __init__(self, argv=None):
        # Accept argv to allow easier testing or override, default to sys.argv
        self.argv = argv if argv is not None else sys.argv
        self.console = Console()
        self._global_args = None
        self._module_args = None
        self.services = service_registry.all_services()
        

    def print_help(self):
        try:
            with files(resources).joinpath(self.DEFAULT_HELP_NAME).open("r") as f:
                help_data = yaml.safe_load(f)
            print_help_from_yaml(help_data)

        except FileNotFoundError:
            logging.error(f"{self.DEFAULT_HELP_NAME} not found in resources.")

        except Exception as e:
            logging.error(f"Failed to load {self.DEFAULT_HELP_NAME}: {e}")

        sys.exit(0)
    
    def get_global_parser(self):
        parser = argparse.ArgumentParser(add_help=False)

        # Positional
        parser.add_argument('service', nargs='?', help='Service (e.g. http, smb, ftp, ssh)')
        parser.add_argument('target', nargs='?', help='Target IP or domain')

        # General
        parser.add_argument('-p', '--ports', type=str)
        parser.add_argument('-M', '--module', type=str)
        parser.add_argument('-c', '--config', type=str)
        parser.add_argument('--publish', action='store_true')
        parser.add_argument('--nmap', action='store_true')

        # Debugging & monitoring
        parser.add_argument('-v', '--verbose', action='store_true')
        parser.add_argument('--debug', action='store_true')

        # Modules
        parser.add_argument('--list-modules', action='store_true')
        parser.add_argument('--show-module', type=str)

        # Help flag
        parser.add_argument('-h', '--help', action='store_true')

        return parser

    def parse_args(self):
        parser = self.get_global_parser()
        args, unknown = parser.parse_known_args(self.argv[1:])  # safer than using raw sys.argv

        self._global_args = args
        self._module_args = unknown
        
        return args, unknown

    def _display_modules_for_service(self, service_name):
        table = Table(box=box.SIMPLE_HEAD)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="magenta")
        table.add_column("Category", style="green")
        table.add_column("Group", style="yellow")
        table.add_column("Authors", style="yellow")

        modules_data = module_registry.describe()
        found_modules = False

        for module_meta in modules_data:
            if module_meta.get('service') == service_name:
                module_cls = module_registry.get_by_path(module_meta['path'])
                if module_cls and getattr(module_cls, 'name', 'N/A') != 'base':
                    name = getattr(module_cls, 'name', 'N/A')
                    description = getattr(module_cls, 'description', 'N/A')
                    category = getattr(module_cls, 'category', 'N/A')
                    group = getattr(module_cls, 'group', 'N/A')
                    authors = ', '.join(getattr(module_cls, 'authors', ['N/A']))
                    table.add_row(name, description, category, group, authors)
                    found_modules = True
        
        if not found_modules:
            self.console.print(f"[bold red]No modules found for service: '{service_name}'[/]")
        else:
            self.console.print(table)

    def _display_module_options(self, module_name):
        module_cls = module_registry.get_module(module_name)
        if not module_cls:
            self.console.print(f"[bold red]Module '{module_name}' not found.[/]")
            sys.exit(1)

        table = Table(box=box.SIMPLE_HEAD)
        table.add_column("Argument", style="cyan", no_wrap=True)
        table.add_column("Description", style="magenta")
        table.add_column("Default", style="green")

        # Create a temporary parser to get module-specific arguments
        temp_parser = argparse.ArgumentParser(add_help=False)
        try:
            # Instantiate the module class to call its options method
            # This assumes the module's options method can be called without full initialization
            # and that it returns a parser or modifies the one passed.
            # If the module requires specific args for instantiation, this might need adjustment.
            module_instance = module_cls()
            config_instance = Config()
            module_config = config_instance.get(module_instance.config_key) if module_instance.config_key else {}
            module_instance.options(temp_parser, module_config) # Pass an empty config for now

            for action in temp_parser._actions:
                if action.dest != 'help': # Skip default help argument
                    arg_name = ', '.join(action.option_strings)
                    description = action.help if action.help else 'N/A'
                    default_value = str(action.default) if action.default is not argparse.SUPPRESS else 'N/A'
                    table.add_row(arg_name, description, default_value)
        except Exception as e:
            self.console.print(f"[bold red]Error retrieving options for module '{module_name}': {e}[/]")
            sys.exit(1)

        self.console.print(table)

    def get_global_args(self):
        if self._global_args is None:
            self.parse_args()
        return self._global_args

    def get_module_args(self):
        _, _module_args = self.parse_args()
        return _module_args

    def main_args(self):
        args, _ = self.parse_args()

        if '--help' in self.argv or '-h' in self.argv or len(sys.argv) == 1:
            self.print_help()
            
        # Resolve logic
        if args.service is not None and args.service not in self.services:
            args.target = args.service
            args.service = None

        if not args.service and args.module:
            self.console.print(f'[bold red]Missing arguments:[/] No Service specified but module are set.')
            self.print_help()

        if args.service and not (args.target or args.module) and not (args.list_modules or args.show_module):
            # Validate if target or flags required when using service without target
            if '--list-modules' not in self.argv or '--show-module' not in self.argv:
                self.console.print(f'[bold red]Missing arguments:[/] need at least a target or [-M|--module|--list-modules|--show-module] flags when using \'{str(args.service).upper()}\' service.')
                self.print_help()

        if args.list_modules:
            if args.service:
                self._display_modules_for_service(args.service)
            else:
                self.console.print(f'[bold red]Missing arguments:[/] The [--list-modules] needs [bold green]<service>[/] flags (options).')
                self.print_help()
            sys.exit(0)

        if args.show_module:
            self._display_module_options(args.show_module)
            sys.exit(0)
        
        return args

