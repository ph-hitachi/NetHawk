import logging

from rich.table import Table
from rich.console import Console

from mongoengine import DoesNotExist

from nethawk.cli import banner
from nethawk.core.models import ServiceInfo, TargetInfo
from nethawk.core.resolver import Resolver
from nethawk.extensions.resolver.resolver import resolve_host
from nethawk.helper.dns import add_dns_host
from nethawk.modules.discovery import Module
from nethawk.extensions.network.scanner import NetworkScanner

class PortScanner(Module):
    name = "nmap"
    description = "Performs Nmap initial scans & detailed scans"
    config_key = "nmap"
    _author = ['Ph.Hitachi']
    tags = ["network"]

    def options(self, parser, config):
        parser.add_argument('--profile', type=str)
        parser.add_argument('-p', '--port',  type=str)
        parser.add_argument('-v', '--verbose', action='store_true')
        return parser

    def display_rich_ports_table(self, n_scanner):
        console = Console()
        table = Table(show_header=True, show_edge=False, box=None)

        table.add_column("PORT", style="cyan", no_wrap=True)
        table.add_column("STATE", style="blue")
        table.add_column("SERVICE", style="orange_red1")
        table.add_column("REASON", style="dim")

        # Get ports from scanner
        ports = n_scanner.get_ports()

        def add_row(port_data):
            port = port_data["port"]
            proto = port_data["protocol"]
            service = port_data.get("service", "unknown")
            reason = port_data.get("reason", "unknown")
            ttl = port_data.get("reason_ttl", "unknown")
            state = port_data.get("state", "unknown")
            table.add_row(
                f"[bold cyan]{port}[/]/[bold dark_magenta]{proto}[/]",
                f"[bold green]{state}[/]",
                f"[bold orange_red1]{service}[/]",
                f"[bold yellow]{reason}[/] [bold blue1]{ttl}[/]"
            )
        
        if not ports:
            return logging.error('No ports found, Please try again.')
        
        # If get_ports() returns a dict (multiple hosts), flatten it
        if isinstance(ports, dict):
            for ip, port_list in ports.items():
                for port_data in port_list:
                    add_row(port_data)
        else:
            # Single host result
            for port_data in ports:
                add_row(port_data)

        console.print(table)
        print()

    def initial_scans(self, target, ports, type='initial'):
        n_scanner = NetworkScanner(
            host=str(target), # scanme.nmap.org, 
            config=self.get_config(), 
            scan_type=type
        )
        
        banner.task(f"Scanning ports {n_scanner.get_formatted_default_ports()} using [bold]TCP/SYN/UDP[/]")
        
        # Execute Nmap scan process
        n_scanner.scan(ports=ports, output=False)

        # Print summary of the scan
        self.display_rich_ports_table(n_scanner)

        return n_scanner.get_open_ports(formatted=True)
    
    def nse_scans(self, target, ports):
        # Run initial nmap scan to get active ports (open)
        active_ports = self.initial_scans(target, ports=ports)
            
        n_scanner = NetworkScanner(
            host=str(target), # 'scanme.nmap.org', 
            config=self.get_config(), 
            scan_type='full'
        )

        banner.task(f"Running OS Detection, Version Enumeration, Traceroute, Default NSE Scripts.")

        # Execute Full Nmap scan process with open ports only to improve perfomance
        n_scanner.scan(ports=str(active_ports), output=True)

        return n_scanner
    
    def profile_scans(self, target, ports, type):
        banner.task(f"Running Profile Scans with {str(type).upper()} Scan type")

        n_scanner = NetworkScanner(
            host=str(target),
            config=self.get_config(),
            scan_type=type
        )

        n_scanner.scan(ports=ports, output=True)

        return n_scanner

    async def run(self, target, port, args):

        resolver = resolve_host(target, port)

        if resolver.error and 'TCP connection' not in resolver.error:
            return logging.error(resolver.error)
        
        if args.profile:
            nmap_results = self.profile_scans(target=resolver.ip, ports=port, type=args.profile)
        else:
            nmap_results = self.nse_scans(target=resolver.ip, ports=port)

        vhost = nmap_results.get_vhost()

        # Clear previous data
        TargetInfo.objects(ip_address=resolver.ip).delete() # type: ignore[attr-defined]
        
        target_info = TargetInfo.get_or_create(
            ip_address=resolver.ip,
            hostname=vhost if vhost else resolver.hostname,
            operating_system=resolver.os_guess_from_ttl
        )

        if vhost:
            add_dns_host(ip=resolver.ip, hostname=vhost)

        for service in nmap_results.get_services():
            ServiceInfo.get_or_create(**service, target=target_info)

