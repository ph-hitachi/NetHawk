# detectors/tech_detector.py

import logging
from textwrap import indent
from rich.console import Console
from rich.table import Table

from nethawk.cli import banner
from nethawk.core.context import Request
from nethawk.core.resolver import Resolver
from nethawk.extensions.network.service_scanner import ServiceScanner
from nethawk.extensions.detectors.tech import Detector
from nethawk.extensions.exploit.cve_suggester import CVESuggester
from nethawk.core.models import HostInfo, TechnologyEntry
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
    
    async def run(self, target, port):
        request = Request.from_target(target, port)
        detector = Detector()
        suggester = CVESuggester(config=vars(self.args))

        if request.resolver.error:
            return logging.error(request.resolver.error)
        
        try:
            target_info = request.database
            host_info = HostInfo.get_or_create(domain=request.resolver.hostname, target=target_info)

            # tech_list = []
            # if host_info.technologies:
            tech_list = TechnologyEntry.objects(host=host_info).first()
            logging.debug(f'Technology list: {tech_list}')

            # Auto-detect technologies
            if not tech_list:
                for group in detector.get_technologies(request.resolver.resolved_url).values():  # type: ignore
                    for tech_data in group:
                        TechnologyEntry.get_or_create(
                            name=tech_data['name'],
                            version=tech_data['version'],
                            host=host_info,
                            categories=tech_data.get('categories', []),
                            confidence=tech_data.get('confidence', ''),
                            group=tech_data.get('group', ''),
                            detected_by=tech_data.get('detected_by', '')
                        )

            detected_tech=[tech.to_dict() for tech in TechnologyEntry.objects(host=host_info)] # type: ignore
            filtered_results = suggester.filtered_technologies(detected_tech)
            
            logging.debug(f"Filtered Technologies: {filtered_results}")
            
            if not filtered_results:
                logging.info(f"No Technologies related to: {', '.join(self.args.categories)}")

            for tech in filtered_results:
                suggester.search(tech.get('name'), self.args.provider)
            
            # If search is manually provided
            if self.args.search:
                suggester.search(self.args.search, self.args.provider)

        except Exception as e:
            logging.error(f"Unexpected Error: {e}")
            raise

