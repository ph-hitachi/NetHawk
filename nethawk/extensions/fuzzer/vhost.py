from typing import override
import re
import aiohttp
import asyncio
import logging
import random

from pathlib import Path
from urllib.parse import urljoin, urlparse

from nethawk.core.resolver import Resolver
from nethawk.helper.dns import add_dns_host

from .utils import get_content_hash
from .utils import is_probably_directory
from .utils import generate_random_string
from . import Handler

class Vhost(Handler):
    def __init__(self, *, config: dict):
        self.config = config
        self.baseline_hash = None
        self.match_codes =  config.get("match_code", [200, 301, 302, 307, 401])
        self.headers = config.get("headers", {})
        self.recursive_enabled = config.get("recursive", False)
        self.recurse_mode = config.get("recurse_mode", "sequential")
        self.max_depth = config.get("max_depth", 3)
        self.visited_paths = set()

        super().__init__(config=config)

    @staticmethod
    def sanitize_subdomain(name: str) -> str:
        # Keep only letters, numbers, and hyphens
        return re.sub(r'[^a-zA-Z0-9-]', '', name.lower().strip())
    
    # from pathlib import Path
    # import logging

    def generate_entries(self, base_url) -> list[str]:  # type: ignore
        """
        Generate subdomain-based hostnames for vhost fuzzing.
        """
        logging.debug(f'wordlist: {self.config.get("wordlist")}')
        
        wordlist = Path(str(self.config.get("wordlist")))

        if not wordlist.exists():
            raise ValueError(f'Wordlist not found: \'{wordlist}\'')
        
        try:

            hostname = self.domain
            entries = []

            # Add calibration entries
            calibration_sub = generate_random_string()
            test_entries = [calibration_sub]

            for entry in test_entries:
                entries.append(f"{entry}.{hostname}")
                with wordlist.open() as f:
                    for line in f:
                        line = self.sanitize_subdomain(line)
                        if not line or line.startswith("#"):
                            continue
                        entries.append(f"{line}.{hostname}")

        except IsADirectoryError:
            raise IsADirectoryError(f"Provided wordlist path is a directory, not a file: {wordlist}")
        
        except Exception as e:
            logging.exception(f"Unexpected error reading wordlist file: {e}")
            return []

        logging.debug(f'Wordlist Entries: {len(entries)}')
        return entries

    
    def extract_metadata(self, url, response, content, text):
        path = urlparse(url).path
        size = len(content)
        code = response.status
        location = response.headers.get("location", "")
        words = len(text.split())
        lines = len(text.splitlines())

        return {
            "url": url,
            "path": path,
            "code": code,
            "size": size,
            "location": location,
            "words": words,
            "lines": lines,
            "hash": get_content_hash(content),
            "result": (path, code, size, words, lines),
            "headers": response.headers,
        }
    
    async def fetch(self, session, url):
        headers = dict(self.headers)
        headers["Host"] = url

        async with session.get(self.target, headers=headers, timeout=5, allow_redirects=False) as response:
            content = await response.read()
            try:
                text = await response.text()
            except UnicodeDecodeError:
                text = ''
            return response, content, text
        
    def should_recurse(self, metadata: dict, response_text: str) -> bool:
        """
        Determines whether a URL should be recursed into based on various conditions.
        """

        # Recurse must be enabled in configuration
        if not self.recursive_enabled:
            return False

        # Maximum depth should not be exceeded
        if metadata.get("depth", 0) >= self.max_depth:
            return False

        # Status code must be 200 (OK) — required to avoid recursing into soft errors or redirects
        if metadata["code"] not in self.config.get("match_code"):
            return False

        return True

    async def process(self, session: aiohttp.ClientSession, url: str, depth: int = 0):
        if url in self.visited_paths:
            return
        
        self.visited_paths.add(url)

        # print(url)
        async with self.semaphore:
            try:
                for attempt in range(self.config.get("max_tries", 3)):
                    try:
                        response, content, text = await self.fetch(session, url)
                        metadata = self.extract_metadata(url, response, content, text)
                        
                        if self.baseline_hash is None:
                            self.baseline_hash = metadata.get('hash')
                            return  # Baseline set, nothing more to do on first pass

                        if metadata.get('hash') == self.baseline_hash:
                            return

                        if metadata.get('code') not in self.match_codes:
                            return

                        self.valid_results.add(metadata.get('result'))

                        if self.should_recurse(metadata, text):
                            resovler = Resolver(url)
                            add_dns_host(ip=resovler.get_ip(), hostname=metadata.get('path'), auto=True)
                            await self.recursion(url, depth + 1)

                        return  # Success case, exit after first good result

                    except Exception as e:
                        await asyncio.sleep(0.2 * attempt + random.uniform(0, 0.1))
                        raise e
            finally:
                self.update_statistics()


    async def recursion(self, base_url: str, depth: int):
        await asyncio.create_task(
            self.start_tasks(base_url, depth=depth)
        )

