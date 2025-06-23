# detectors/tech_detector.py

import logging
from textwrap import indent
from rich.console import Console
from rich.table import Table

from nethawk.cli import banner
from nethawk.core.resolver import Resolver
from nethawk.extensions.network.service_scanner import ServiceScanner
from nethawk.extensions.detectors.tech import Detector
from nethawk.extensions.exploit.cve_suggester import CVESuggester
from nethawk.core.models import TechnologyEntry
from nethawk.modules.protocols import Module

class CVESearch(Module):
    name = "cve"
    description = "Exploit Suggester, CVE Hunting & CVE Analysis."
    config_key = "http"
    authors = ['Ph.Hitachi']
    tags = ["http"]
    
    def options(self, parser, config):
        parser.add_argument('--search', type=str, help='Keyword, Vendor to search for CVEs')
        parser.add_argument('--provider', help='CVE search provider (Google, Metasploit, Searchsploit)', default=set(config.get('cve', {}).get('provider', ['google'])))
        parser.add_argument('--categories', help='Categories of technologies to filter for (e.g., Web Application)', default=set(config.get('cve', {}).get('categories', ['Web Application'])))
        parser.add_argument('--key', type=str, help='GEMINI_API_KEY for AI-powered insights', default=config.get('api_keys', {}).get('GEMINI_API_KEY'))
        parser.add_argument('--limit', type=int, help='Number of links to fetch for Google Dork searches', default=5)
        # parser.add_argument('--extensions', type=str, help='Default extensions that considered as script PoC', default=config.get('cve', {}).get('extensions', ['py', 'sh', 'rb', 'pl', 'java', 'md']))

        return parser
    
    async def run(self, target, port, args):
        s_scanner = ServiceScanner()
        detector = Detector()
        suggester = CVESuggester(config=vars(args))

        url = None
        resolver = None

        if target:
            resolver = Resolver(target, port)
        
        try:
            if resolver and resolver.get_error():
                return
            
            if resolver and target:
                url = resolver.get_url()

                db, service = s_scanner.scan(
                    target=resolver.get_ip(), 
                    port=str(resolver.get_port())
                )

                if not db or not service:
                    return
                
                tech_list = []
                domain = db.get_vhost(resolver.get_hostname())

                if db.hostname and resolver.get_hostname():
                    tech_list = domain.technologies

                # Auto-detect technologies
                if not tech_list:
                    for group in detector.get_technologies(url).values():  # type: ignore
                        for tech_data in group:
                            name, version = tech_data['name'], tech_data['version']
                            if not any(t.name == name and t.version == version for t in domain.technologies):  # type: ignore
                                if db.hostname and resolver.get_hostname():
                                    domain.technologies.append(TechnologyEntry(**tech_data))


                    db.commit()

                detected_tech=[tech.to_dict() for tech in domain.technologies] # type: ignore
                filtered_results = suggester.filtered_technologies(detected_tech)
                
                logging.debug(f"Detected Technologies: {filtered_results}")

                for tech in filtered_results:
                    suggester.search(tech.get('name'), args.provider)
                
                print(db.to_json(indent=4))
                return
            
            # If search is manually provided
            if args.search:
                suggester.search(args.search, args.provider)

        except Exception as e:
            logging.error(f"Unexpected Error: {e}")
            raise

