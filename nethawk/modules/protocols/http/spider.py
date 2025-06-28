import logging
from urllib.parse import urlparse

from scrapy.crawler import AsyncCrawlerRunner

from nethawk.cli import banner
from nethawk.core.context import Request
from nethawk.core.models import FormFieldEntry, HostInfo, ServiceLinks, TargetInfo
from nethawk.core.resolver import Resolver
from nethawk.extensions.crawler.crawler import WebSpider
from nethawk.extensions.network.service_scanner import ServiceScanner
from nethawk.extensions.resolver.resolver import resolve_host
from nethawk.modules.protocols import Module

class Spider(Module):
    name = "spider"
    description = "Web Spider (e.g, Forms (POST), Parameters, External/JS files, Comments, etc...)"
    authors = ['Ph.Hitachi']
    tags = ["http"]
    settings = {
        'DOWNLOADER_MIDDLEWARES': {
            'nethawk.extensions.crawler.middlewares.CrawlerOffsiteMiddleware': 500,
        },
        'LOG_LEVEL': 'CRITICAL',
    }

    @staticmethod
    def save(start_url, results, reason):
        try:
            url = urlparse(start_url)
            target_host = (url.hostname or url.netloc.split(':')[0])
            request = Request.from_target(target_host, url.port)

            host_info = HostInfo.get_or_create(
                domain=request.resolver.hostname, 
                target=request.database, 
                port=url.port
            )

            service_links = ServiceLinks.get_or_create(host=host_info)

            service_links.urls = results.get("links", [])
            service_links.emails = results.get("emails", [])
            service_links.images = results.get("images", [])
            service_links.videos = results.get("videos", [])
            service_links.audio = results.get("audio", [])
            service_links.comments = results.get("comments", [])
            service_links.pages = results.get("pages", [])
            service_links.parameters = results.get("pages_with_parameters", [])
            service_links.subdomain_links = results.get("subdomain_links", [])
            service_links.static_files = results.get("static_files", [])
            service_links.javascript_files = results.get("js_files", [])
            service_links.external_files = results.get("external_files", [])
            service_links.other_links = results.get("other_links", [])

            # Handle form_fields separately as they are ReferenceFields
            form_field_entries = []
            for form_data in results.get("form_fields", []):
                form_field_entry = FormFieldEntry(
                    action=form_data.get("action"),
                    can_found_at=form_data.get("can_found_at", []),
                    method=form_data.get("method", "GET"),
                    fields=form_data.get("fields", []),
                    service_links=service_links
                )
                form_field_entry.save()
                form_field_entries.append(form_field_entry)
                
            service_links.form_fields = form_field_entries

            service_links.save()

            logging.debug(service_links.to_dict())

        except Exception as e:
            raise e
        
    async def run(self, target, port):
        request = Request.from_target(target, port)

        if request.resolver.error:
            return logging.error(request.resolver.error)

        try:
            resolver = request.resolver
            db_info = request.database
            start_url = resolver.resolved_url

            if not db_info:
                return
            
            host_info = HostInfo.get_or_create(
                domain=resolver.hostname,
                target=db_info,
                port=port
            )

            logging.info(f"Starting the crawler with URL: [bold green]{start_url}[/]")

            runner = AsyncCrawlerRunner(settings=self.settings)

            await runner.crawl(WebSpider, start_urls=[start_url])
        
        except Exception as e:
            raise e
