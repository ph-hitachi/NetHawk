import os
from pathlib import Path
import yaml
import shutil
import logging
import importlib.resources as pkg_resources

from box import Box
from nethawk.core.logger import setup_logging
from resources import config as config_resources  # Updated import

class QuotedStringDumper(yaml.SafeDumper):
    def represent_str(self, data):
        return self.represent_scalar('tag:yaml.org,2002:str', data, style='"')

QuotedStringDumper.add_representer(str, QuotedStringDumper.represent_str)

class Config:
    DEFAULT_CONFIG_NAME = "config.yaml"

    def __init__(self, default_key=None):
        # logging = logging.getLogger(self.__class__.__name__)
        # logging.setLevel(logging.INFO)

        self._custom_config_path = None

        # Determine actual user's home directory, even under sudo
        home_dir = os.path.expanduser(f"~{os.getenv('SUDO_USER') or os.getenv('USER')}")
        self._default_dest_dir = os.path.join(home_dir, ".nethawk")
        self._default_config_path = os.path.join(self._default_dest_dir, self.DEFAULT_CONFIG_NAME)
        self.default_key = default_key
        self._box = Box(self._load_config(), default_box=True)


    def __getattr__(self, attr):
        return getattr(self._box, attr)

    def publish(self):
        """Ensure default config file exists by copying from package if needed."""
        os.makedirs(self._default_dest_dir, exist_ok=True)

        if not os.path.exists(self._default_config_path):
            try:
                with pkg_resources.files(config_resources).joinpath(self.DEFAULT_CONFIG_NAME).open("rb") as src, \
                     open(self._default_config_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                logging.info(f"Published default config to {self._default_config_path}")
            except Exception as e:
                logging.warning(f"Failed to publish config: {e}")
        else:
            logging.debug(f"Config already exists at {self._default_config_path}")

    def republish(self):
        """Merge updated template config into user's existing config without overwriting user values."""
        try:
            current_config = self._load_config() or {}

            with pkg_resources.files(config_resources).joinpath(self.DEFAULT_CONFIG_NAME).open("r") as f:
                template_config = yaml.safe_load(f.read()) or {}

            merged_config = self._deep_merge(template_config, current_config)

            with open(self.path, "w") as f:
                yaml.dump(merged_config, f, default_flow_style=False, sort_keys=False, Dumper=QuotedStringDumper)

            logging.info(f"Republished updated config template merged to {self.path}")
            self._box = Box(merged_config, default_box=True)

        except Exception as e:
            logging.error(f"Failed to republish config: {e}")

    def use(self, config_path: str):
        if not os.path.isfile(config_path):
            raise FileNotFoundError(f"Custom config file not found: {config_path}")

        try:
            with open(config_path, "r") as f:
                content = yaml.safe_load(os.path.expandvars(f.read()))

                if not isinstance(content, dict):
                    raise ValueError("Config file must contain a YAML mapping (dictionary) at the root.")

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file {config_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error reading config file {config_path}: {e}")

        self._custom_config_path = config_path
        self._box = Box(content, default_box=True)
        logging.info(f"Using custom config file: {config_path}")

    def update(self, key: str, value):
        keys = key.split('.')
        d = self._box
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        self.save()

    def save(self):
        path = self.path
        try:
            with open(path, "w") as f:
                yaml.dump(self._box.to_dict(), f)
            logging.info(f"Saved config to {path}")
        except Exception as e:
            logging.error(f"Failed to save config: {e}")

    def get(self, key, default=None):
        keys = key.split('.')
        d = self._box
        for k in keys:
            if isinstance(d, dict) or isinstance(d, Box):
                if k in d:
                    d = d[k]
                else:
                    logging.warning(f"Config key '{key}' not found at '{k}'")
                    return default
            else:
                logging.warning(f"Config key '{key}' path broken at '{k}', encountered non-dict: {type(d).__name__}")
                return default
        return d

    def show_config_path(self):
        path = self.path
        logging.info(f"Using config file: {path}")
        return path

    def _load_config(self):
        path = self.path
        
        if not Path(path).exists():
            self.publish()
            
        try:
            with open(path, "r") as f:
                return yaml.safe_load(os.path.expandvars(f.read())) or {}
        except Exception as e:
            logging.error(f"Failed to load config from {path}: {e}")
            return {}

    @staticmethod
    def _deep_merge(source: dict, override: dict) -> dict:
        result = source.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @property
    def path(self):
        return self._custom_config_path or self._default_config_path
