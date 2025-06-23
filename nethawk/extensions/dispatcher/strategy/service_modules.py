import sys
import logging
from nethawk.extensions.dispatcher import DispatchHandler
from nethawk.core.exception import ServiceNotFound

from nethawk.core.registry import service_registry

class ServiceModules(DispatchHandler):
    """
    Dispatcher for executing service-related modules based on detected services and ports.
    """

    async def _execute_service(self):
        """Dispatch all handler based on found services"""
        _service_handler = None
        
        try:
            if self.service:
                _service_handler = service_registry.get_service(self.service)

        except ServiceNotFound as e:
            logging.warning(f'No service handler found for {self.service} on port {self.port}. Skipping scans...')
            sys.exit(0)
        
        if _service_handler:

            service_class_instance = _service_handler(
                target=self.target, 
                service=self.service, 
                port=self.port,
                modules=self.modules
            )
            
            await service_class_instance.run_modules()

    async def run(self):
        logging.debug(f'Running ServiceModules(DispatchHandler): target={self.target}, ports={self.port}')

        if self.service:
            await self._execute_service()

