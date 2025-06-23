# nethawk/core/registry.py

from types import ModuleType
from typing import Callable, List, Optional, Dict, Tuple, Type
from nethawk.core.exception import ModuleNotFound, ServiceNotFound
class ServiceRegistry:
    def __init__(self):
        self._registry = {}

    def register(self, name: Optional[str] = None) -> Callable[[Type], Type]:
        def decorator(cls):
            key = name or cls.__name__
            self._registry[key] = cls
            return cls
        return decorator

    def find_service(self, service_name: str):
        for cls in self.registered().values():
            if service_name == getattr(cls, 'name', None):
                return cls
            if service_name in getattr(cls, 'alias', []):
                return cls
        raise ServiceNotFound(f"No registered service handler found for service: '{service_name}'")

    def get_service(self, service_name: str): 
        try:
            return self.find_service(service_name)
        except ValueError:
            return None

    def all_services(self):
        services = set()
        for cls in self.registered().values():
            name = getattr(cls, 'name', None)
            aliases = getattr(cls, 'alias', [])
            if name:
                services.add(name)
            services.update(aliases)
        return sorted(services)

    def registered(self):
        return self._registry
    
class ModuleRegistry:
    def __init__(self):
        self._registry: Dict[str, Type] = {}  # Key = full dotted path
        self._by_meta: List[Dict[str, str]] = []  # Optional, for quick lookup/display

    def register(self) -> Callable[[Type], Type]:
        def decorator(cls: Type) -> Type:
            name = getattr(cls, "name", None)
            group = getattr(cls, "group", None)
            category = getattr(cls, "category", None)

            if not name or not group:
                raise ValueError(
                    f"[ModuleRegistry] Missing 'name' or 'group' in: {cls.__module__}.{cls.__name__}"
                )

            key = cls.__module__  # full import path
            # if key in self._registry:
            #     raise ValueError(
            #         f"[ModuleRegistry] Duplicate module key '{key}' (already registered)"
            #     )

            self._registry[key] = cls
            self._by_meta.append({
                "path": key,
                "name": name,
                "group": group,
                "service": category or "",
                "class": cls.__name__
            })
            return cls
        return decorator

    def get_by_path(self, module_path: str) -> Optional[Type]:
        return self._registry.get(module_path)

    def get_by_meta(self, name: str, group: str, service: Optional[str] = None) -> Optional[Type]:
        for path, cls in self._registry.items():
            if (
                getattr(cls, "name", None) == name and
                getattr(cls, "group", None) == group and
                getattr(cls, "service", None) == service
            ):
                return cls
        return None

    def list(self) -> Dict[str, Type]:
        return dict(self._registry)

    def describe(self) -> List[Dict[str, str]]:
        return self._by_meta
    
    def find_module(self, module_name: str) -> Type:
        for key, cls in self.registered().items():
            if module_name == key:
                return cls
            if module_name == getattr(cls, 'name', None):
                return cls
            if module_name in getattr(cls, 'alias', []):
                return cls
        raise ModuleNotFound(f"No registered class found for module: '{module_name}'")

    def get_module(self, module_name: str) -> Optional[Type]:
        try:
            return self.find_module(module_name)
        except ValueError:
            return None

    def all_modules(self):
        modules = set()
        for key, cls in self.registered().items():
            modules.add(key)
            # name = getattr(cls, 'name', None)
            # aliases = getattr(cls, 'alias', [])
            # if name:
            #     modules.add(name)
            # modules.update(aliases)
        return sorted(modules)
    
    def all_modules_name(self):
        modules = set()
        for key, cls in self._registry.items():
            # modules.add(key)
            name = getattr(cls, 'name', None)
            aliases = getattr(cls, 'alias', [])
            if name:
                modules.add(name)
            modules.update(aliases)
        return sorted(modules)

    def registered(self):
        return self._registry
    
service_registry = ServiceRegistry()
register_service = service_registry.register

module_registry = ModuleRegistry()
register_module = module_registry.register