# detectors/tech_detector.py

import logging
from textwrap import indent
from rich.console import Console
from rich.table import Table

from nethawk.cli import banner
from nethawk.core.context import Request
from nethawk.core.models import TechnologyEntry, TargetInfo, HostInfo
from nethawk.core.resolver import Resolver
from nethawk.extensions.network.service_scanner import ServiceScanner
from nethawk.extensions.detectors.tech import Detector
from nethawk.modules.protocols import Module

class TechProfiling(Module):
    name = "tech"
    description = "Technology Enumeration, Framework Analysis"
    authors = ['Ph.Hitachi']
    tags = ["http"]

    async def run(self, target, port):
        request = Request.from_target(target, port)
        console = Console()
        detector = Detector()

        if request.resolver.error:
            return logging.error(request.resolver.error)
        
        try:
            technologies = detector.get_technologies(request.resolver.resolved_url) or {}

            target_info = request.database

            host_info = HostInfo.get_or_create(domain=request.resolver.hostname, target=target_info)

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

                    # Use get_or_create for TechnologyEntry
                    TechnologyEntry.get_or_create(
                        name=tech['name'],
                        version=tech['version'],
                        host=host_info
                    )

                host_info.save()

                console.print(table)
                

        except Exception as e:
            logging.error(f"Unexpected Error: {e}")
            raise
