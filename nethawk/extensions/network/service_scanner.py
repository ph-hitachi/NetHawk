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
        # delete_database_info_by_ip(resolver.get_ip())

        try:
            db = TargetInfo.objects(ip_address=ip).first() # type: ignore

            # Create new TargetInfo document if it doesn't exist
            if not db:
                db = TargetInfo(
                    ip_address=resolver.get_ip(),
                    hostname=resolver.get_hostname(),
                    operating_system=resolver.get_os_guess_from_ttl(),
                    services=[]
                )
                

            # Ensure `services` attribute exists
            if not hasattr(db, 'services'):
                raise AttributeError("Database object does not have a 'services' attribute.")

            # Convert the input port to an integer (if it's not already)
            target_port = int(port)

            # Look for a service in db.services that matches the target port
            service = None

            for s in db.services: # type: ignore
                if int(s.port) == target_port:
                    service = s
                    break

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
                        db.hostname = v_host
                        add_dns_host(ip=resolver.get_ip(), hostname=v_host)

                    for service_data in found_services:
                        # Skip if service with this port already exists (avoid duplication)
                        if any(int(s.port) == int(service_data["port"]) for s in db.services): # type: ignore
                            continue

                        logging.info(f"Discovered new service '{service_data.get('name', 'Unknown')}' on port {service_data['port']}")
                        
                        logging.info(f"Possible Virtual Host: '{n_scanner.get_results()}'")

                        new_service = ServiceInfo(**service_data)
                        db.services.append(new_service) # type: ignore

                        # If this is the service we're looking for, assign it
                        if int(service_data["port"]) == int(port):
                            service = new_service
                    
                except Exception as e:
                    logging.error(f"Service scan failed: {e}")
            
            logging.debug(f'Resolve URL: {resolver.get_url()} Hostname from db: {db.hostname}')
            
            
            # Ensure `services` attribute exists
            if not hasattr(db, 'virtual_hosts'):
                raise AttributeError("Database object does not have a 'virtual_hosts' attribute.")
            
            if db.hostname: 
                entry = HostInfo(
                    domain=db.hostname, 
                    port=port,
                )
                db.virtual_hosts.append(entry) # type: ignore

            if service:
                logging.debug(f"Service info: {service.to_dict()}")
            
            db.commit()

            return db, service
        
        except Exception as e:
            raise e
