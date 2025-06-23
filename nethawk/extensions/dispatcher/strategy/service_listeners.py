import logging
import sys

from nethawk.extensions.dispatcher import DispatchHandler
from nethawk.core.exception import ServiceNotFound
from nethawk.core.registry import service_registry

class ServiceListeners(DispatchHandler):

    async def _execute_service(self):
        """Dispatch all handler based on found services"""
        _service_handler = None
        
        try:
            if self.service:
                _service_handler = service_registry.get_service(self.service)

        except ServiceNotFound as e:
            logging.warning(f'No service handler found for {self.service} on port {service_port}. Skipping scans...') # type: ignore
            sys.exit(0)
        
        if _service_handler:
            service_class_instance = _service_handler(target=self.target, port=self.port)
            # service_class_instance.port = service_port

            await service_class_instance.run_listeners() # type:ignore

    async def run(self):
        logging.debug(f'Running ServiceListeners(DispatchHandler): target={self.target}, port={self.port}')
        
        if self.service:
            await self._execute_service()
