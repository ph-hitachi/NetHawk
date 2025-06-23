# nethawk/modules/http/dir.py

import logging
from textwrap import indent
from typing import Any
from nethawk.cli import banner
# from nethawk.core.models import ServiceLinks
from nethawk.core.models import HostInfo
from nethawk.core.resolver import Resolver
from nethawk.extensions.network.service_scanner import ServiceScanner
from nethawk.extensions.fuzzer import Fuzzer
from nethawk.helper.dns import add_dns_host
from nethawk.helper.types import AttrDict
from nethawk.modules.protocols import Module

class VhostEnumeration(Module):
    name = "vhost"
    description = "Virtual Host Enumeration..."
    config_key = "http.vhost"
    authors = ['Ph.Hitachi']
    tags = ["http"]
    
    def options(self, parser, config):
        parser.add_argument('--wordlist', type=str, default=config.get('wordlist'), help='Path to the wordlist file for virtual host enumeration')
        parser.add_argument('--recursion', action='store_true', default=config.get('recursion', False), help='Enable recursive enumeration of virtual hosts')
        parser.add_argument('--recursion-depth', type=int, default=config.get('recursion-depth'), help='Maximum depth for recursive virtual host enumeration')
        parser.add_argument('--threads', type=int, default=config.get('threads'), help='Number of concurrent threads for enumeration')
        parser.add_argument('--timeout', type=float, default=config.get('timeout'), help='Timeout in seconds for network requests')
        parser.add_argument('--match-code', type=lambda s: list(map(int, s.split(','))), default=config.get('match_code'), help='Comma-separated list of HTTP status codes to consider as valid matches')
        return parser

    async def run(self, target, port, args): 
        resolver = Resolver(target, port)
        scanner = ServiceScanner()

        try:
            if resolver.get_error():
                return
            
            db, service = scanner.scan(
                target=resolver.get_ip(), 
                port=str(resolver.get_port())
            )

            if not db or not service:
                return
            
            fuzz = Fuzzer(mode='vhost', config=vars(args))
            
            logging.info(f"URL: {resolver.get_url()}")
            logging.info(f"THREADS: {args.threads}")
            logging.info(f"RECURSION: {args.recursion}")
            logging.info(f"STATUS: {', '.join(str(code) for code in args.match_code)}")
            logging.info(f"EXTENSIONS: [bold green]{','.join(str(extensions) for extensions in args.extensions)}[/]")
            logging.info(f"WORDLIST: {args.wordlist}")
            print()

            await fuzz.start(url=resolver.get_url())
            
            for result in fuzz.valid_results:
                vhost, status, size, words, line = result
                
                # automatically add vhost to /etc/hosts
                add_dns_host(ip=resolver.get_ip(), hostname=vhost, auto=True)

                entry = HostInfo(
                    domain=vhost, 
                    port=port,
                )
                
                db.virtual_hosts.append(entry) 

            db.commit()
            
            # print(db.to_json(indent=4))
            # print(db.get_vhost('grafana.planning.htb').to_dict())

        except Exception as e:
            raise e