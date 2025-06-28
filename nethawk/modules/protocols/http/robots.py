import re
from textwrap import indent

import aiohttp
import logging
import asyncio
import requests

from urllib.parse import urljoin
from rich.console import Console
from rich.table import Table

from nethawk.cli import banner
from nethawk.core.context import Request
from nethawk.core.resolver import Resolver
from nethawk.core.models import HostInfo, ServiceLinks, RobotsTxtEntry
from nethawk.modules.protocols import Module
from nethawk.extensions.network.service_scanner import ServiceScanner


class RobotsAnalyzer(Module):
    name = "robots"
    description = "Robots.txt Analysis (e.g, Allowed, Disallowed, Sitemap)"
    authors = ['Ph.Hitachi']
    tags = ["http"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.robots_entries = []

    def fetch_robots_txt(self, url):
        robots_url = urljoin(url, "/robots.txt")
        logging.info(f"Checking {robots_url}")

        try:
            response = requests.get(robots_url, timeout=5.0, allow_redirects=True)
            if response.status_code in (301, 302, 303, 307, 308):
                logging.warning(f"Redirected to {response.headers.get('Location')}")
            elif response.status_code == 404:
                logging.info("robots.txt not found")
            elif response.status_code == 200:
                return response.text
            else:
                logging.error(f"Unhandled robots.txt status ({response.status_code})")
        except Exception as e:
            logging.error(f"Failed to fetch robots.txt: {e}")
        return None

    def parse_robots(self, robots_txt):
        allowed, disallowed, sitemaps = set(), set(), set()
        for line in robots_txt.splitlines():
            line = line.strip()
            
            if not line or line.startswith("#"):
                continue

            if line.lower().startswith("allow:"):
                allowed.add(line.split(":", 1)[1].strip())

            elif line.lower().startswith("disallow:"):
                disallowed.add(line.split(":", 1)[1].strip())

            elif line.lower().startswith("sitemap:"):
                sitemaps.add(line.split(":", 1)[1].strip())

        return sorted(allowed), sorted(disallowed), sorted(sitemaps)

    async def get_status(self, client, url):
        try:
            response = await client.get(url, timeout=5)
            return url, response.status_code
        except Exception:
            return url, None

    async def print_group(self, title, base_url, paths, session):
        if not paths:
            return

        # If it's a Sitemap group, fetch the sitemap URLs first
        if title.lower() == "sitemap":
            all_urls = []
            for sitemap_url in paths:
                try:
                    async with session.get(sitemap_url, timeout=5, ssl=False) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            links = re.findall(r"<loc>(.*?)</loc>", text)
                            all_urls.extend(links)
                except Exception as e:
                    logging.error(f"Failed to fetch sitemap {sitemap_url}: {e}")
            paths = all_urls

        # paths = [p.strip() for p in paths if p.strip() and p.strip() != "/"] # skipped root directory
        paths = [p.strip() for p in paths if p.strip()]

        if not paths:
            return

        table = Table(show_header=False, show_lines=False, box=None, pad_edge=False)
        table.add_column("Path", width=60, no_wrap=True)
        table.add_column("Status")

        async def get_status_with_retries(url, retries=3):
            for attempt in range(retries):
                try:
                    async with session.get(url, timeout=5, ssl=False) as response:
                        return url, response.status
                except Exception as e:
                    logging.debug(f"Attempt {attempt+1} failed for {url}: {e}")
                    await asyncio.sleep(2 ** attempt)
            return url, None

        tasks = []

        for path in paths:
            if not path.startswith("http"):
                url = urljoin(base_url, path)
                tasks.append(get_status_with_retries(url))
            else:
                tasks.append(get_status_with_retries(path))

        results = await asyncio.gather(*tasks)

        for url, status in results:
            path = url.replace(base_url, "") if url.startswith(base_url) else url
            status_txt = "[bold red][Error][/]" if status is None else f"[{status}]"

            if status:
                if 200 <= status < 300:
                    status_txt = f"[green]{status_txt}[/]"
                elif 300 <= status < 400:
                    status_txt = f"[blue1]{status_txt}[/]"
                elif 400 <= status < 500:
                    status_txt = f"[magenta]{status_txt}[/]"
                else:
                    status_txt = f"[red]{status_txt}[/]"

            table.add_row(f"    {path}", status_txt)

            entry_type = title.lower()

            if entry_type in ("allowed", "disallowed", "sitemap"):
                self.robots_entries.append((path, entry_type, status))
        
        console = Console()

        console.print(f"\n[{title}]")
        console.print(table)
        console.print()


    async def run(self, target, port):
        request = Request.from_target(target, port)
        resolver = request.resolver
        target_info = request.database
        url = resolver.resolved_url

        if request.resolver.error:
            return logging.error(request.resolver.error)
        
        try:

            robots_txt = self.fetch_robots_txt(url)
            if not robots_txt:
                return

            allowed, disallowed, sitemaps = self.parse_robots(robots_txt)

            async with aiohttp.ClientSession() as session:
                await self.print_group("Allowed", url, allowed, session)
                await self.print_group("Disallowed", url, disallowed, session)
                await self.print_group("Sitemap", url, sitemaps, session)

            host_info = HostInfo.get_or_create(
                domain=resolver.hostname, target=target_info, port=port
            )
            
            service_links = ServiceLinks.get_or_create(host=host_info)
            
            for robots in self.robots_entries:
                path, entry_type, status = robots
                RobotsTxtEntry.get_or_create(
                    path=path, type=entry_type, status=str(status), service_links=service_links
                )
            
            logging.debug(service_links.to_dict())

        except Exception as e:
            logging.exception(e)