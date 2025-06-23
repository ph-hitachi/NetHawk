import logging

from scrapy.crawler import AsyncCrawlerRunner

from nethawk.cli import banner
from nethawk.core.resolver import Resolver
from nethawk.extensions.crawler.crawler import WebSpider
from nethawk.extensions.network.service_scanner import ServiceScanner
from nethawk.modules.discovery import Module

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

    async def run(self, target, port, args):
        resolver = Resolver(target, port)
        s_scanner = ServiceScanner()
        start_url = resolver.get_url()

        try:
            if resolver.get_error():
                return

            db, service = s_scanner.scan(
                target=resolver.get_ip(), 
                port=str(resolver.get_port())
            )

            if not (db or service):
                return
            
            logging.info(f"Starting the crawler with URL: [bold green]{start_url}[/]")

            runner = AsyncCrawlerRunner(settings=self.settings)
        
            await runner.crawl(WebSpider, start_urls=[start_url])
        except Exception as e:
            raise e
