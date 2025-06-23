import logging
from types import SimpleNamespace
from nethawk.extensions.resolver.resolver import resolve_host

class Resolver:
    def __init__(self, target, port=None):
        try:
            resolved_host = resolve_host(target, port)
            self.target = vars(resolved_host)

        except Exception as e:
            logging.error(e)

    def get_url(self):
        return self.target.get('resolved_url')

    def get_ip(self):
        return self.target.get('ip')

    def get_port(self):
        return self.target.get('port')

    def get_hostname(self):
        return self.target.get('hostname')

    def get_icmp_reachable(self):
        return self.target.get('icmp_reachable')

    def get_icmp_latency(self):
        return self.target.get('icmp_latency_ms')

    def get_icmp_latency_category(self):
        return self.target.get('icmp_latency_category')

    def get_os_guess_from_ttl(self):
        return self.target.get('os_guess_from_ttl')

    def get_tcp_port_open(self):
        return self.target.get('tcp_port_open')

    def get_error(self):
        if self.target.get('error'):
            logging.error(self.target.get('error'))
            
        return self.target.get('error')

    # Override the __str__ method to return only the resolved URL
    def __str__(self):
        return self.get_url() if self.get_url() else self.get_hostname() or self.get_ip() or self.target.original
