# nethawk/_internal/dispatcher/strategy/service_discovery.py
import logging

from mongoengine import DoesNotExist

# from nethawk.extensions.dispatcher.engine import Dispatcher

from nethawk.core.resolver import Resolver
from nethawk.core.exception import ServiceNotFound
from nethawk.core.models import TargetInfo
from nethawk.helper.db import get_database_info_by_ip
# from nethawk.services.handler.protocols import ServiceHandler
from nethawk.extensions.dispatcher import DispatchHandler
from nethawk.core.registry import module_registry
from nethawk.core.registry import service_registry

class ServiceDiscovery(DispatchHandler):
    def __init__(self,  **kwargs):
        self.services = []
        super().__init__(**kwargs)
    
    def _load_service_handler(self):
        service_handlers = []
        resolved_target = Resolver(self.target, self.port)

        if resolved_target.get_error():
            return

        try:
            db_info = get_database_info_by_ip(ip=resolved_target.get_ip())

            for service_data in db_info.services:
                service_port = service_data['port']
                try:
                    handler = service_registry.get_service(service_data['name'])
                    
                    # if issubclass(handler, ServiceHandler): # type: ignore
                    # Append both handler and port as a tuple
                    logging.debug(f'Service Handler Found: {handler}')
                    service_handlers.append((handler, service_port))

                except ServiceNotFound as e:
                    logging.warning(f'No service handler found for {service_data['name']} on port {service_port}. Skipping scans...') # type: ignore
            
            # set handler based on found services
            self.services = service_handlers

        except DoesNotExist:
            logging.error(f"No Services Data found on database.")

        return self.services
    
    async def _execute_services(self):
        """Dispatch all handler based on found services"""
        
        if self._load_service_handler():
            for _service_handler, service_port in self.services:
                logging.debug(f'Running {_service_handler.__name__}({_service_handler.__bases__[0].__name__ or ''}): target={self.target}, ports={service_port}')
                await _service_handler(target=self.target, port=service_port).run_listeners() # type:ignore

    async def _execute_nmap(self):
        port_scanner = module_registry.get_module('nmap')
        
        # Run Nmap module for initial service enumeration/discovery
        await port_scanner(target=self.target, port=self.port) # type:ignore

    async def run(self):
        logging.debug(f'Running ServiceDiscovery(DispatchHandler): target={self.target}, ports={self.port}')
        resolved_target = Resolver(self.target, self.port)

        if not resolved_target.get_error():
            await self._execute_nmap()
            await self._execute_services() 