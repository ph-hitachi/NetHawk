import logging
from nethawk.core.models import TargetInfo

def get_database_info_by_ip(ip: str):
    return TargetInfo.objects.get(ip_address=ip)  # type: ignore

def delete_database_info_by_ip(ip: str):
    TargetInfo.objects(ip_address=ip).delete()  # type: ignore

def find_service_on_database(db, port):
    """
    Search for a service in the database by its port number.

    Args:
        db (Database): The database object containing a list of services.
        port (int): The target port to match.

    Returns:
        Service | None: The matching service object if found, otherwise None.
    """
    if not hasattr(db, 'services'):
        raise AttributeError("Database object does not have a 'services' attribute.")

    # Iterate over all services to find a match
    for service in db.services:
        logging.info(service.port)
        logging.info(port)
        logging.info(service.port == port)
        if service.port == port:
            return service  # Return the first match
    
    # No matching service found
    return None

