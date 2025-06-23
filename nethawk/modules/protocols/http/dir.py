# nethawk/modules/http/dir.py

import logging
from textwrap import indent
from typing import Any
from nethawk.cli import banner
from nethawk.core.models import PathEntry, ServiceLinks
from nethawk.core.resolver import Resolver
from nethawk.extensions.network.service_scanner import ServiceScanner
from nethawk.extensions.fuzzer import Fuzzer
from nethawk.helper.types import AttrDict
from nethawk.modules.protocols import Module

class ContentDiscovery(Module):
    name = "dir"
    description = "Content Discovery Enumeration..."
    config_key = "http.dictionary"
    authors = ['Ph.Hitachi']
    tags = ["http"]
    scanner = ServiceScanner()
    
    def options(self, parser, config):
        parser.add_argument('--wordlist', type=str, default=config.get('wordlist'), help='Path to the wordlist file for directory enumeration')
        parser.add_argument('--recursion', action='store_true', default=config.get('recursion', False), help='Enable recursive directory enumeration')
        parser.add_argument('--recursion-depth', type=int, default=config.get('recursion-depth'), help='Maximum depth for recursive directory enumeration')
        parser.add_argument('--threads', type=int, default=config.get('threads'), help='Number of concurrent threads for enumeration')
        parser.add_argument('--timeout', type=float, default=config.get('timeout'), help='Timeout in seconds for network requests')
        parser.add_argument('--extensions', type=lambda s: list(map(str, s.split(','))), default=config.get('extensions'), help='Comma-separated list of file extensions to include in the search')
        parser.add_argument('--match-code', type=lambda s: list(map(int, s.split(','))), default=config.get('match_code'), help='Comma-separated list of HTTP status codes to consider as valid matches')
        return parser

    async def run(self, target, port, args): 
        resolver = Resolver(target, port)

        try:
            # check if port are open
            if resolver.get_error():
                return
            
            db, service = self.scanner.scan(
                target=resolver.get_ip(), 
                port=str(resolver.get_port())
            )

            if not (db or service):
                return

            fuzz = Fuzzer(mode='dir', config=vars(args))
            
            logging.info(f"URL: {resolver.get_url()}")
            logging.info(f"THREADS: {args.threads}")
            logging.info(f"RECURSION: {args.recursion}")
            logging.info(f"STATUS: {','.join(str(code) for code in args.match_code)}")
            logging.info(f"EXTENSIONS: [bold green]{','.join(str(extensions) for extensions in args.extensions)}[/]")
            logging.info(f"WORDLIST: {args.wordlist}")
            print()

            await fuzz.start(url=resolver.get_url())
            
            # Create a list of PathEntry objects from the fuzzing results
            directory_entries = []

            for result in fuzz.valid_results:
                path, status, size, words, line = result

                entry = PathEntry(
                    path=path,       # The discovered path, e.g., "/admin/index.php"
                    status=status,   # HTTP status code, e.g., 200
                    size=size,       # Size of the response in bytes
                    words=words,     # Word count in the response body
                    line=line        # Line count in the response body
                )

                directory_entries.append(entry)

            data = ServiceLinks(
                directories=directory_entries
            )
            
            domain = db.get_vhost(resolver.get_hostname())

            if domain.links:
                domain.links = domain.links.update(data)
            else:
                domain.links = data
            
            db.commit()

        except Exception as e:
            logging.error(f"Unexpected Error: {e}")