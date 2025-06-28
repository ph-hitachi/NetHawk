# nethawk/_internal/dispatcher/strategy/service_discovery.py
from ipaddress import ip_address
import logging

from mongoengine import DoesNotExist

# from nethawk.extensions.dispatcher.engine import Dispatcher

from nethawk.core.context import Request
from nethawk.core.resolver import Resolver
from nethawk.core.exception import ServiceNotFound
from nethawk.core.models import ServiceInfo, TargetInfo
from nethawk.extensions.resolver.resolver import resolve_host
from nethawk.helper.db import get_database_info_by_ip
# from nethawk.services.handler.protocols import ServiceHandler
from nethawk.extensions.dispatcher import DispatchHandler
from nethawk.core.registry import module_registry
from nethawk.core.registry import service_registry

class ServiceDiscovery(DispatchHandler):
    
    def _load_service_handler(self):
        service_handlers = []
        resolver = resolve_host(self.target, self.port)

        if resolver.error and 'TCP connection' not in resolver.error:
            return logging.error(resolver.error)

        db_info = TargetInfo.get_or_create(
            ip_address=resolver.ip,
            hostname=resolver.hostname,
            operating_system=resolver.os_guess_from_ttl
        )

        for service_data in ServiceInfo.objects(target=db_info): # type: ignore
            try:
                handler = service_registry.get_service(service_data.name)

                # Append both handler and port as a tuple
                service_handlers.append((handler, service_data.port))
                logging.debug(f'Service Handler Found: {handler}')

            except ServiceNotFound as e:
                logging.warning(f"No service handler found for '{service_data.name}' on port {service_data.port}. Skipping scans...")

        return service_handlers
    
    async def _execute_services(self):
        """Dispatch all handler based on found services"""
        
        services = self._load_service_handler()

        if services:
            for _service_handler, service_port in services:
                logging.debug(f'Running {_service_handler.__name__}({_service_handler.__bases__[0].__name__ or ''}): target={self.target}, ports={service_port}')
                await _service_handler(target=self.target, port=service_port).run_listeners() # type:ignore

    async def _execute_nmap(self):
        port_scanner = module_registry.get_module('nmap')
        
        # Run Nmap module for initial service enumeration/discovery
        await port_scanner(target=self.target, port=self.port) # type:ignore

    async def run(self):
        logging.debug(f'Running ServiceDiscovery(DispatchHandler): target={self.target}, ports={self.port}')
        resolver = resolve_host(self.target, self.port)

        if resolver.error and 'TCP connection' not in resolver.error:
            return logging.error(resolver.error)

        await self._execute_nmap()
        logging.info(f'Dispatching all modules based on discovered services/ports.') 
        await self._execute_services() 