import logging
import sys
from typing import List, Any, Dict
from nethawk.cli import banner
from nethawk.core.config import Config
from nethawk.core.exception import ModuleNotFound, ServiceNotFound
from nethawk.core.registry import module_registry, service_registry
from nethawk.extensions.dispatcher import BaseInitMixin

class ServiceHandler(BaseInitMixin):
    """
    Abstract base service class for dispatching protocol-specific listeners.
    Includes hooks for subclass customization and shared context handling.
    """
    name = "BaseService"
    listener_key = None
    description = "Service Handler"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = Config()
        self.context: Dict[str, Any] = {}
        self.listener_names = self._resolve_listener_names()
    
    def _resolve_listener_names(self) -> List[str]:
        """
        Subclasses override this to declare which listeners to load.
        """
        
        events = self.config.get(self.listener_key or self.name)
        
        logging.debug(f"HTTP Config: {self.config.get('http')}")

        return events.get('listener') or events.get('listeners') # type: ignore

    def _load_listeners(self) -> List:
        listeners = []

        logging.debug(f'Listeners found: {self.listener_names}')

        for module_name in self.listener_names:
            instance = self._get_module_instance(module_name)
            listeners.append(instance)

        return listeners
    
    def _get_service_instance(self):
        service = None
        
        try:
            service = service_registry.get_service(service_name=str(self.service or self.name))

        except ServiceNotFound:
            logging.warning(f"No service handler for '{str(self.service)}' found. Skipping scans...")
        return service
            
    def _create_module_instance(self, cls) -> Any:
        """
        Override if listener needs extra args (e.g., shared config, context).
        """
        ports = self.port
        service = self._get_service_instance()
    
        # Handle ports: if self.port is None, fallback to default_port
        if ports is None:
            if service and service.default_port is not None: # type: ignore
                ports = service.default_port # type: ignore
            else:
                logging.warning(f"No ports provided and no default port available for service '{self.service}'.")
                return

        return cls(target=self.target, port=ports, context=self.context)

    async def run_listeners(self) -> List[Any] | None:
        results = []
        
        logging.debug(f"Running 'run_listeners()' with port={self.port}, service={self.service}, modules={self.modules}")

        listeners = self._load_listeners()
        
        if not listeners:
            logging.warning(f"No listeners found on '{self.name}' service.")
            return

        for module in listeners:
            if not self.should_run_module(module):
                continue

            result = await self._execute_module(module)
            results.append(result)

        return results
    
    def _get_module_instance(self, module_name):
        try:
            module_cls = module_registry.get_module(module_name)
            module = self._create_module_instance(module_cls)
            return module
        
        except ModuleNotFound:
            logging.error(f"No module '{module_name}' found on '{self.service}' service. Skipping scans...")
            logging.debug(f'Registered modules: {module_registry.registered()}')
    
    async def run_modules(self) -> List[Any]:
        results = []
        
        logging.debug(f"Running 'run_modules()' with port={self.port}, service={self.service}, modules={self.modules}")

        if isinstance(self.modules, str):
            module = self._get_module_instance(module_name=self.modules)
            
            await self._execute_module(module)

        elif isinstance(self.modules, list):
            for module_name in self.modules:
                module = self._get_module_instance(module_name)
                
                if not self.should_run_module(module):
                    continue

                result = await self._execute_module(module)
                results.append(result)

        return results
    
    async def _execute_module(self, module):
        try:
            await self.before_run(module)
            logging.debug(f"Dispatching Module: {module.__class__.__name__}")
            
            if module.__class__.description:
                banner.task(module.__class__.description)
                
            result = await module
            
            await self.after_run(module, result)

        except Exception as e:
            logging.error(f"{module.__class__.__name__} failed: {e}")
            raise e
        
        return result

    async def before_run(self, module) -> None:
        """
        Optional hook before each module runs.
        Subclasses can use this for setup, shared state, logging, etc.
        """
        pass

    async def after_run(self, module, result: Any) -> None:
        """
        Optional hook after each module runs.
        Use for cleanup, DB logging tweaks, chaining, etc.
        """
        pass

    def should_run_module(self, module) -> bool:
        """
        Gatekeeper to filter which modules should run (e.g., profile-aware runs).
        """
        return True