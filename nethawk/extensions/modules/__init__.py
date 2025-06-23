# nethawk/modules/__init__.py

import sys
import argparse
import logging

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from nethawk.cli.options import Options
from nethawk.core.config import Config
from nethawk.core.resolver import Resolver
from nethawk.core.registry import module_registry

class Base(ABC):
    name = "base"
    config_key = None  # for config section

    def __init__(self, target:str | None = None, port:str | int | None = None, context: Dict[str, Any] | None = None):
        self.config = Config()  # full config
        self._options = Options()
        self.module_args = self._options.get_module_args()
        self.args = None
        self.target = target
        self.port = port
        self.context = context or {}

    def __init_subclass__(cls, **kwargs):
        """Register all modules that extends this base class"""
        super().__init_subclass__(**kwargs)
        module_registry.register()(cls)

    def __await__(self):
        self.parse_module_args()
        return self.run(target=self.target, port=self.port, args=self.args).__await__()

    def get_arg_parser(self):
        return argparse.ArgumentParser(add_help=True)

    def parse_module_args(self):
        # If `options` is implemented, call it, otherwise use default behavior
        parser = self.get_arg_parser()  # Start with a default parser

        if hasattr(self, 'options'):
            # If `options` is implemented, use it to modify the parser
            parser = self.options(parser, self.get_config())
            
        # Parse the arguments and store them
        self.args = self._parse_arguments(parser)
        
        logging.debug(f"Module Args: {self.args}")
        return self.args
    
    def get_config(self):
        if self.config_key:
            return self.config.get(self.config_key) or {}
        else: 
            return {}
    
    def _parse_arguments(self, parser):

        full_args = (self._options.argv or sys.argv)[1:]
        
        logging.debug(f"Full Args: {full_args}")

        # Combine global and unknown args
        global_parser = self._options.get_global_parser()
        _, unknown_args = global_parser.parse_known_args(full_args)
        combined_args = unknown_args + [
            f for f in full_args if f in sys.argv and f not in unknown_args
        ]
        
        logging.debug(f"Combined Args: {combined_args}")

        # Get all option strings defined in the module parser
        declared_flags = set()

        for action in parser._actions:
            declared_flags.update(action.option_strings)
        
        logging.debug(f"Actions: {parser._actions}")
        logging.debug(f"Declared Args: {declared_flags}")

        # Fix for combined short flags like -p80 → ['-p', '80']
        def expand_combined_short_options(args, declared_flags):
            expanded = []
            for arg in args:
                # Match -xVALUE where -x is in declared flags
                if len(arg) > 2 and arg.startswith('-') and not arg.startswith('--'):
                    flag = arg[:2]
                    if flag in declared_flags:
                        expanded.append(flag)
                        expanded.append(arg[2:])
                        continue
                expanded.append(arg)
            return expanded
        
        # After get combined_args and declared_flags
        combined_args = expand_combined_short_options(combined_args, declared_flags)

        # Filter args that match declared flags
        filtered = []
        skip = False
        for i, arg in enumerate(combined_args):
            if skip:
                skip = False
                continue

            # If this arg is one of the declared ones
            if arg in declared_flags:
                filtered.append(arg)
                # Peek next: if it’s not a flag, include it too
                if i + 1 < len(combined_args) and not combined_args[i + 1].startswith('-'):
                    filtered.append(combined_args[i + 1])
                    skip = True

            # If it's a --key=value pattern
            elif any(arg.startswith(f"{flag}=") for flag in declared_flags if flag.startswith('--')):
                filtered.append(arg)

        logging.debug(f"Filtered Args: {filtered}")
        
        self.args = parser.parse_args(filtered)
        return self.args
    
    def get_default_args(self, parser: argparse.ArgumentParser, config: dict) -> argparse.ArgumentParser:
        """Default implementation when subclass does not override `options`."""
        # You can provide a default parser or do nothing here.
        return parser  # Default: Just return the parser without adding arguments.
    
    # @abstractmethod
    def options(self, parser: argparse.ArgumentParser, config: dict) -> argparse.ArgumentParser:
        return parser

    @abstractmethod
    async def run(self, target: str | None, port: str | int | None, args):
        pass