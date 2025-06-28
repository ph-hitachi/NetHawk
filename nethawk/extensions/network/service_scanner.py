# detectors/service_scanner.py
import logging
from textwrap import indent
from mongoengine import DoesNotExist
from nethawk.core.models import HostInfo, TargetInfo, ServiceInfo
from nethawk.core.config import Config
from nethawk.core.resolver import Resolver
from nethawk.extensions.network.scanner import NetworkScanner
from nethawk.helper.db import delete_database_info_by_ip, find_service_on_database, get_database_info_by_ip
from nethawk.helper.dns import add_dns_host

class ServiceScanner:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)

    def scan(self, target, port):
        resolver = Resolver(target, port)
        ip = resolver.get_ip()

        if not port:
            port = resolver.get_port()

        # TargetInfo.objects(ip_address=ip).delete()

        try:
            target = TargetInfo.get_or_create(
                ip_address=ip,
                hostname=resolver.get_hostname(),
                operating_system=resolver.get_os_guess_from_ttl()
            )

            service = ServiceInfo.objects(target=target, port=int(port)).first()

            # If service not found, perform a scan and update
            if not service:
                try:
                    n_scanner = NetworkScanner(
                        host=str(resolver.get_ip()),
                        scan_type='initial',
                        version=True
                    )

                    n_scanner.scan(ports=str(port), output=False)
                    v_host = n_scanner.get_vhost()
                    found_services = n_scanner.get_services()

                    if v_host:
                        logging.info(f"Possible Virtual Host: '{v_host}'")
                        target.hostname = v_host
                        add_dns_host(ip=resolver.get_ip(), hostname=v_host)
                    
                    for service_data in found_services:
                        # Use get_or_create for ServiceInfo
                        service_data["target"] = target
                        new_service = ServiceInfo.get_or_create(**service_data)

                        logging.info(f"Discovered new service '{new_service.name}' on port {new_service.port}")

                        # If this is the service we're looking for, assign it
                        if int(new_service.port) == int(port): # type: ignore
                            service = new_service

                except Exception as e:
                    logging.error(f"Service scan failed: {e}")

            # logging.debug(f'Resolve URL: {resolver.get_url()} Hostname from db: {target.hostname}')

            # Ensure `virtual_hosts` attribute exists

            if target.hostname:
                # Use get_or_create for HostInfo
                HostInfo.get_or_create(
                    domain=target.hostname,
                    target=target,
                    port=port
                )

            if service:
                logging.debug(f"Service info: {service.to_dict()}")

            return service

        except Exception as e:
            raise e
