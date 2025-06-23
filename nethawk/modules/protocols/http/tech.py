# detectors/tech_detector.py

import logging
from textwrap import indent
from rich.console import Console
from rich.table import Table

from nethawk.cli import banner
from nethawk.core.models import TechnologyEntry
from nethawk.core.resolver import Resolver
from nethawk.extensions.network.service_scanner import ServiceScanner
from nethawk.extensions.detectors.tech import Detector
from nethawk.modules.protocols import Module

class TechProfiling(Module):
    name = "tech"
    description = "Technology Enumeration, Framework Analysis"
    authors = ['Ph.Hitachi']
    tags = ["http"]

    async def run(self, target, port=None, args=[]):
        # resolver = Resolver(target, port)
        # s_scanner = ServiceScanner()
        console = Console()
        detector = Detector()

        try:
            result = self.get_service()
            if not result:
                return
            
            resolver, db, service = result

            if not (resolver and db and service):
                return

            resolver, db, service = self.get_service() # type: ignore

            url = resolver.get_url()

            technologies = detector.get_technologies(url) or {}

            domain = db.get_vhost(resolver.get_hostname())

            for group, techs in technologies.items():
                console.print(f"\n[{group}]")

                table = Table(show_header=False, show_lines=False, box=None, pad_edge=False)
                table.add_column("Name", width=40, no_wrap=True)
                table.add_column("Details")

                for tech in techs:
                    details = []

                    if tech['categories'] != ['Unknown']:
                        details.append(f"Categories: [bold green]{', '.join(tech['categories'])}[/]")

                    if tech['confidence']:
                        details.append(f"Confidence: [bold cyan]{tech['confidence']}[/]")

                    if tech['version']:
                        details.append(f"Version: [bold red]{tech['version']}[/]")

                    table.add_row(f"    {tech['name']}", f"[{', '.join(details)}]")

                console.print(table)

            if not hasattr(domain, 'technologies'):
                logging.error(f'Unavailable to save technologies: {resolver.get_hostname()} are not added as virtual host.')
                return
            
            for group in technologies.values():
                for tech_data in group:
                    name, version = tech_data['name'], tech_data['version']
                    if not any(t.name == name and t.version == version for t in domain.technologies):  # type: ignore
                        if db.hostname and resolver.get_hostname():
                            domain.technologies.append(TechnologyEntry(**tech_data))

            db.commit()

        except Exception as e:
            logging.error(f"Unexpected Error: {e}")
            raise
