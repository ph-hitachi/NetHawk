# nethawk/libs/network/utils.py

def parse_nmap_services(scan_result: dict, target: str) -> list[dict]:
    """
    Extracts and normalizes service data from a raw Nmap scan result.
    
    Args:
        scan_result (dict): Output from nmap.PortScanner().
        target (str): IP or hostname scanned.

    Returns:
        list[dict]: List of services with protocol, port, and service name.
    """
    services = []
    
    if target not in scan_result:
        return services

    host_data = scan_result[target]
    tcp_ports = host_data.get('tcp', {})

    for port, port_data in tcp_ports.items():
        if port_data.get('state') != 'open':
            continue

        service = port_data.get('name', 'unknown')
        product = port_data.get('product', '')
        version = port_data.get('version', '')
        extrainfo = port_data.get('extrainfo', '')
        

        services.append({
            'ip': target,
            'port': port,
            'protocol': 'tcp',
            'service': service.lower(),
            'product': product,
            'version': version,
            'extrainfo': extrainfo
        })

    return services
