# nethawk/modules/http/dir.py

import logging
from textwrap import indent
from typing import Any
from nethawk.cli import banner
from nethawk.core.context import Request
from nethawk.core.models import HostInfo, PathEntry, ServiceLinks
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

    async def run(self, target, port):
        request = Request.from_target(target, port)

        if request.resolver.error:
            return logging.error(request.resolver.error)
        
        try:
            resolver = request.resolver
            db_info = request.database

            fuzz = Fuzzer(mode='dir', config=vars(self.args))
            
            logging.info(f"URL: {resolver.resolved_url}")
            logging.info(f"THREADS: {self.args.threads}")
            logging.info(f"RECURSION: {self.args.recursion}")
            logging.info(f"STATUS: {','.join(str(code) for code in self.args.match_code)}")
            logging.info(f"EXTENSIONS: [bold green]{', '.join(str(extensions) for extensions in self.args.extensions)}[/]")
            logging.info(f"WORDLIST: {self.args.wordlist}")
            print()

            await fuzz.start(url=resolver.resolved_url)
            
            host_info = HostInfo.get_or_create(
                domain=resolver.hostname,
                target=db_info,
                port=port
            )

            service_links = ServiceLinks.get_or_create(
                host=host_info
            )

            for result in fuzz.valid_results:
                path, status, size, words, line = result

                PathEntry.get_or_create(
                    path=path,
                    status=status,
                    size=size,
                    words=words,
                    line=line,
                    service_links=service_links
                )

        except Exception as e:
            logging.error(f"Unexpected Error: {e}")