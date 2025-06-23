import re
import sys
import json
from textwrap import indent
import scrapy
import logging

from rich.console import Console
from urllib.parse import urlparse, urljoin
from rich.table import Table

from twisted.internet.error import TimeoutError, DNSLookupError
from scrapy.spidermiddlewares.httperror import HttpError

from nethawk.core.models import FormFieldEntry, ServiceLinks
from nethawk.core.resolver import Resolver
from nethawk.extensions.network.service_scanner import ServiceScanner

console = Console()

class WebSpider(scrapy.Spider):
    name = 'WebSpider'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.allowed_domains = None
        self.base_domain = None
        self.base_scheme = None
        self.target = None
        self.visited_urls = set()
        self.status_map = {}
        self.results = self._initialize_results()
        self.scanner = ServiceScanner()

        self.page_content_types = {
            "text/html",
            "application/javascript",
            "application/x-httpd-php",
        }

        self.external_files_types = {
            "text/xml",
            "text/plain",
            "application/pdf",
            "application/msword",
            "application/vnd",
            "application/octet-stream",
            "application/json",
            "application/zip",
        }

    def _initialize_results(self):
        return {
            'emails': set(),
            'links': set(),
            'static_files': set(),
            'js_files': set(),
            'external_files': set(),
            'form_fields': [],
            'images': set(),
            'videos': set(),
            'audio': set(),
            'comments': set(),
            'pages': set(),
            'pages_with_parameters': set(),
            'subdomain_links': set(),
            'other_links': set(),
        }

    def parse(self, response):
        start_url = response.url
        parsed_start = urlparse(start_url)
        domain = parsed_start.netloc.split(':')[0]

        if not self.target:
            self.target = start_url
        # # else
        self.start_urls = [start_url]
        self.allowed_domains = [domain]
        self.base_domain = domain
        self.base_scheme = parsed_start.scheme

        logging.debug(f'Parsing URL: {start_url}')

        content_type = self._get_content_type(response)
        
        self._track_visit(response)

        # Discover links only if it's a text-based page
        if self._is_text_response(response):
            yield from self._extract_and_schedule_links(response)

        # Analyze and categorize
        if self._is_page(content_type):
            self._categorize_page(response)
        
        if self._is_external_file(content_type):
            self._categorize_external_file(response)

    def _is_text_response(self, response):
        content_type = self._get_content_type(response)
        return content_type.startswith("text/") or content_type in self.page_content_types

    def _extract_and_schedule_links(self, response):
        if not self._is_text_response(response):
            return

        selectors = [
            'a::attr(href)', 'script::attr(src)', 'link::attr(href)',
            'img::attr(src)', 'video::attr(src)', 'audio::attr(src)',
            'source::attr(src)', 'iframe::attr(src)', 'form::attr(action)',
        ]

        hrefs = set()
        for sel in selectors:
            hrefs.update(response.css(sel).getall())

        for href in hrefs:
            if not href or href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                continue

            full_url = urljoin(response.url, href)
            parsed = urlparse(full_url)

            if not parsed.scheme.startswith(('http', 'https')) or not parsed.netloc:
                continue

            normalized = full_url.split('#')[0]
            domain = parsed.netloc

            if domain == self.base_domain:
                if normalized not in self.visited_urls:
                    self.results['links'].add(normalized)
                    self.visited_urls.add(normalized)
                    yield response.follow(normalized, callback=self.parse)

            elif domain.endswith(f".{self.base_domain}"):
                self.results['subdomain_links'].add(full_url)

            else:
                self.results['other_links'].add(full_url)


    def _categorize_page(self, response):
        url = response.url
        parsed = urlparse(url)

        if parsed.query:
            self.results['pages_with_parameters'].add(url)
        else:
            self.results['pages'].add(parsed.path)
            
        self._extract_emails(response)
        self._extract_static_files(response)
        self._extract_js_files(response)
        self._extract_form_fields(response)
        self._extract_media(response)
        self._extract_comments(response)

    def _categorize_external_file(self, response):
        url = response.url
        if (
            url not in self.results['pages']
            and url not in self.results['pages_with_parameters']
            and url not in self.results['js_files']
            and url not in self.results['images']
            and url not in self.results['videos']
            and url not in self.results['audio']
        ):
            self.results['external_files'].add(url)

    def _track_visit(self, response):
        self.visited_urls.add(response.url)
        self.status_map[response.url] = response.status

    def _get_content_type(self, response):
        return response.headers.get('Content-Type', b'').decode('utf-8').split(';')[0].strip()

    def _is_page(self, content_type):
        return any(content_type.startswith(t) for t in self.page_content_types)

    def _is_external_file(self, content_type):
        return any(content_type.startswith(t) for t in self.external_files_types)

    def _extract_emails(self, response):
        found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', response.text)
        self.results['emails'].update(found)

    def _extract_static_files(self, response):
        hrefs = response.css('link::attr(href), a::attr(href)').getall()
        for href in hrefs:
            full_url = urljoin(response.url, href.split('?')[0].split('#')[0])

            # Only include if it ends with a known static file extension
            if re.search(r'\.(css|svg|ico|eot|ttf|woff2?|webmanifest|json)$', full_url, re.IGNORECASE):
                self.results['static_files'].add(full_url)


    def _extract_js_files(self, response):
        js_sources = response.css('script::attr(src)').getall()
        self.results['js_files'].update(urljoin(response.url, js) for js in js_sources)

    def _extract_form_fields(self, response):
        for form in response.css('form'):
            action = urljoin(response.url, form.attrib.get('action', response.url))
            method = form.attrib.get('method', 'GET').upper()
            fields = list({f for f in form.css('input::attr(name), textarea::attr(name), select::attr(name)').getall() if f})

            existing = next((f for f in self.results['form_fields']
                             if f['action'] == action and f['method'] == method and set(f['fields']) == set(fields)), None)

            if existing:
                if response.url not in existing['can_found_at']:
                    existing['can_found_at'].append(response.url)
            else:
                self.results['form_fields'].append({
                    'action': action,
                    'can_found_at': [response.url],
                    'method': method,
                    'fields': fields
                })

    def _extract_media(self, response):
        self.results['images'].update(urljoin(response.url, src) for src in response.css('img::attr(src)').getall())
        self.results['videos'].update(urljoin(response.url, src) for src in response.css('video::attr(src), source::attr(src)').getall())
        self.results['audio'].update(urljoin(response.url, src) for src in response.css('audio::attr(src), source::attr(src)').getall())

    def _extract_comments(self, response):
        self.results['comments'].update(response.xpath('//comment()').getall())


    def closed(self, reason):
        # Convert sets to lists for serialization and DB storage
        for key in self.results:
            if isinstance(self.results[key], set):
                self.results[key] = list(self.results[key])

        # Save to results.json (for local inspection/debugging)
        # with open('results.json', 'w') as f:
        #     json.dump(self.results, f, indent=4)

        # Resolve target and find service
        resolver = Resolver(self.target)

        db, service = self.scanner.scan(
            target=resolver.get_ip(), 
            port=str(resolver.get_port())
        )

        # print summary to terminal
        self.print_summary()

        # print(db, service, not (db and service))
        if not (db and service):
            logging.warning("Database or service resolution failed.")
            return
        
        domain = db.get_vhost(resolver.get_hostname())

        try:
            data = ServiceLinks(
                urls=self.results.get("links", []),
                emails=self.results.get("emails", []),
                images=self.results.get("images", []),
                videos=self.results.get("videos", []),
                audio=self.results.get("audio", []),
                comments=self.results.get("comments", []),
                pages=self.results.get("pages", []),
                parameters=self.results.get("pages_with_parameters", []),
                subdomain_links=self.results.get("subdomain_links", []),
                static_files=self.results.get("static_files", []),
                javascript_files=self.results.get("js_files", []),
                external_files=self.results.get("external_files", []),
                other_links=self.results.get("other_links", []),
                form_fields=[
                    FormFieldEntry(
                        action=form.get("action"),
                        can_found_at=form.get("can_found_at", []),
                        method=form.get("method", "GET"),
                        fields=form.get("fields", [])
                    ) for form in self.results.get("form_fields", [])
                ]
            )

            if domain.links:
                domain.links = domain.links.update(data)
            else:
                domain.links = data

            # Save to DB
            db.commit()

        except Exception as e:
            raise e
        
    def print_summary(self):
        def build_status_rows(urls):
            rows = []
            for url in sorted(urls):
                full_url = url if url.startswith('http') else f"http://{self.base_domain}{url}"
                parsed = urlparse(full_url)
                path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
                status = self.status_map.get(full_url)
                if status:
                    if 200 <= status < 300:
                        status_txt = f"[green]{status}[/]"
                    elif 300 <= status < 400:
                        status_txt = f"[blue]{status}[/]"
                    elif 400 <= status < 500:
                        status_txt = f"[magenta]{status}[/]"
                    else:
                        status_txt = f"[red]{status}[/]"
                else:
                    status_txt = "[yellow]Unknown[/]"
                rows.append([f"    {path}", status_txt])
            return rows

        def print_section(title, rows):
            if not rows:
                return
            console.print(f"[bold][[green]{title}[/]][/bold]")
            table = Table.grid(padding=(0, 4))
            table.add_column("Path", width=60, no_wrap=True)
            table.add_column("Status")
            for row in rows:
                table.add_row(*row)
            console.print(table)
            console.print()

        # Emails
        email_rows = []
        for email in sorted(self.results['emails']):
            domain = email.split('@')[-1]
            email_rows.append([f"    {email}", f"[Domain: {domain}]"])
        print_section("Emails", email_rows)

        # Forms
        form_rows = []
        for form in self.results['form_fields']:
            action_parsed = urlparse(form['action'])
            action_path = action_parsed.path + (f"?{action_parsed.query}" if action_parsed.query else "")
            method = form['method']
            fields = ', '.join(form['fields'])
            found_at = form['can_found_at'][0]
            more = f" ({len(form['can_found_at']) - 1} more)" if len(form['can_found_at']) > 1 else ""
            label = f"    {urlparse(found_at).path or '/'}{more}"
            
            # Color the method based on type
            if method == "GET":
                method_colored = f"[green]{method}[/]"
            elif method == "POST":
                method_colored = f"[red]{method}[/]"
            else:
                method_colored = f"[blue]{method}[/]"

            # Color the Action URL in cyan
            action_colored = f"[cyan]{action_path}[/]"

            # Color the Fields in yellow
            fields_colored = f"[yellow]{fields}[/]"

            info = f"[Method: {method_colored}, Action: {action_colored}, Fields: {fields_colored}]"
            form_rows.append([label, info])
        print_section("Forms", form_rows)

        # Parameters
        parameter_rows = build_status_rows(self.results['pages_with_parameters'])
        print_section("Parameters", parameter_rows)

        # Pages
        page_rows = build_status_rows(self.results['pages'])
        print_section("Pages", page_rows)

        # External Files
        external_files = build_status_rows(self.results['external_files'])
        print_section("External Files", external_files)

        # External Files
        js_files = build_status_rows(self.results['js_files'])
        print_section("Javascript Files", js_files)

        # External Files
        static_files = build_status_rows(self.results['static_files'])
        print_section("Static Files", static_files)

        static_files = build_status_rows(self.results['subdomain_links'])
        print_section("Subdomains", static_files)

        # Comments
        comment_rows = [[f"    {c.strip().replace('\n', ' ')}"] for c in self.results['comments'] if c.strip()]
        if comment_rows:
            console.print("[bold][[green]Comments[/]][/bold]")
            comment_table = Table.grid(padding=(0, 4))
            for row in comment_rows:
                comment_table.add_row(*row)
            console.print(comment_table)
            console.print()
