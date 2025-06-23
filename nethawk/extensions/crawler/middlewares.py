from urllib.parse import urlparse
from scrapy.downloadermiddlewares.offsite import OffsiteMiddleware

class CrawlerOffsiteMiddleware(OffsiteMiddleware):
    def should_follow(self, request, spider):
        if not self.host_regex:
            return True
        host = urlparse(request.url).netloc.split(':')[0]
        return bool(self.host_regex.search(host))