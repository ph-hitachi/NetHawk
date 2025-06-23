import aiohttp
import asyncio
import logging
import random

from pathlib import Path
from urllib.parse import urljoin, urlparse

from nethawk.extensions.fuzzer.utils import get_content_hash
from nethawk.extensions.fuzzer.utils import is_probably_directory
from nethawk.extensions.fuzzer.utils import generate_random_string
from nethawk.extensions.fuzzer import Handler

class Directory(Handler):
    def __init__(self, *, config: dict):
        self.config = config
        self.baseline_hash = None
        self.wordlist =  config.get("wordlist")
        self.match_codes =  config.get("status", [200, 301, 302, 307, 401])
        self.extensions = config.get("extensions", [])
        self.recursive_enabled = config.get("recursion", False)
        self.max_depth = config.get("max_depth", 3)
        self.visited_paths = set()

        super().__init__(config=config)

    def add_extensions(self, base_entry: str) -> list[str]:
        """
        Given a base URL entry, return a list of that entry with applicable extensions added.
        """
        results = []
        for ext in self.extensions:
            ext = f".{ext.lstrip('.')}"
            if not base_entry.endswith(ext):
                results.append(f"{base_entry}{ext}")
        return results
    
    def generate_entries(self, base_url: str) -> list[str]:
        """
        Generate a list of test and wordlist-based URLs from a base URL.
        """
        wordlist_path = str(self.config.get("wordlist"))
        path = Path(wordlist_path)

        if not path.exists():
            logging.error(f"Wordlist not found: {path}")
            return []
        
        if not path.is_file():
            raise ValueError(f"Wordlist path is not a file: {path}")
        
        entries = []

        # Add test/calibration entries
        calibration_path = generate_random_string()
        test_entries = [calibration_path]
        base_url = base_url.rstrip("/") + "/"

        for entry in test_entries:
            full_url = urljoin(base_url, entry.lstrip("/"))
            entries.append(full_url)
            entries.extend(self.add_extensions(full_url))
            

        # Read wordlist and generate full URLs + extension variants
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                base_entry = urljoin(base_url, line.lstrip("/"))
                entries.append(base_entry)
                entries.extend(self.add_extensions(base_entry))

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
        async with session.get(url, timeout=5, allow_redirects=False) as response:
            content = await response.read()
            try:
                text = await response.text()
            except UnicodeDecodeError:
                text = ''
            return response, content, text
        
    def is_directory(self, metadata: dict, response_text: str) -> bool:
        # Attempt to detect whether the path is likely a directory
        return is_probably_directory(
            path=metadata["path"],
            code=metadata["code"],
            location=metadata["location"],
            text=response_text
        )

    async def process(self, session: aiohttp.ClientSession, url: str, depth: int = 0):
        if url in self.visited_paths:
            return
        
        self.visited_paths.add(url)

        async with self.semaphore:
            try:
                for attempt in range(self.config.get("max_tries", 3)):
                    try:
                        response, content, text = await self.fetch(session, url)
                        metadata = self.extract_metadata(url, response, content, text)

                        if self.baseline_hash is None:
                            self.baseline_hash = metadata.get('hash')
                            return

                        if metadata.get('hash') == self.baseline_hash:
                            return

                        if metadata.get('code') not in self.match_codes:
                            return

                        self.valid_results.add(metadata.get('result'))

                        if self.is_directory(metadata, text):
                            await self.recursion(url, depth + 1)

                        return  # Success case, exit after first good result

                    except Exception:
                        self.errors += 1
                        await asyncio.sleep(0.2 * attempt + random.uniform(0, 0.1))
            finally:
                self.update_statistics()


    async def recursion(self, base_url: str, depth: int):
        # Recurse must be enabled in configuration
        if not self.recursive_enabled:
            return False

        # Maximum depth should not be exceeded
        if depth >= self.max_depth:
            return False
        
        await self.create_tasks_queue(base_url, depth)

