import logging
from typing import Any, Dict

from nethawk.cli.options import Options
from nethawk.core.config import Config
# from nethawk.core.database_service import DatabaseService
from nethawk.core.models import TargetInfo
from nethawk.extensions.network.service_scanner import ServiceScanner
from nethawk.extensions.resolver.resolver import resolve_host

class Request:
    def __init__(self, resolver, config, service, database):
        self.resolver = resolver
        self.config = config
        self.service = service
        self.database = database

    @classmethod
    def from_target(cls, target: str, port: int):
        try:
            logging.debug(f'Attempting to create Request from target: {target}, port: {port}')
            config = Config()
            s_scanner = ServiceScanner()

            logging.debug('Resolving host...')
            resolver = resolve_host(target, port)
            
            logging.debug(f'Host resolved: {resolver}')

            logging.debug('Scanning service...')

            if not port:
                port = resolver.port

            service = s_scanner.scan(target=resolver.ip, port=int(port))

            logging.debug(f'Service scanned: {service.to_dict()}')

            logging.debug('Getting or creating TargetInfo...')

            database = TargetInfo.get_or_create(
                ip_address=resolver.ip,
                hostname=resolver.hostname,
                operating_system=resolver.os_guess_from_ttl
            )
            
            logging.debug(f'TargetInfo: {database.to_dict()}')

            return cls(resolver, config, service, database)
        
        except Exception as e:
            # logging.error(f"Error creating Request from target {target}, port {port}: {e}", exc_info=True)
            raise e

# args = options.main_args()
# request = Request.from_target(args.target, args.ports)
