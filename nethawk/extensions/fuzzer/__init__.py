import threading
import time
import asyncio
import aiohttp

from rich.table import Table
from rich.text import Text
from collections import deque

from nethawk.extensions.fuzzer.utils import colored_status
from nethawk.extensions.resolver.resolver import resolve_host

class Handler:
    def __init__(self, *, config: dict):
        self.start_time = time.time()
        self.completed = 0
        self.errors = 0
        self.lock = threading.Lock()
        self.workers = []
        self.task_queue = asyncio.Queue()
        self.rate_window = deque(maxlen=10)
        self.valid_results = set()
        
        self.target = None
        self.domain = None
        self.target_ip = None
        self.target_port = None
        
        self.config = config
        self.entries = None
        self.total_entries = 0

        self.semaphore = asyncio.Semaphore(config['threads'])
        
    def update_statistics(self):
        with self.lock:
            self.completed += 1
            self.rate_window.append(time.time())

    def calculate_rps(self):
        now = time.time()
        if len(self.rate_window) < 2:
            return 0.0
        time_span = now - self.rate_window[0]
        return len(self.rate_window) / time_span if time_span > 0 else 0.0
        
    def resolve_network_identity(self, base_url: str):
        resolver = resolve_host(base_url)

        self.target = resolver.resolved_url
        self.domain = resolver.hostname
        self.target_ip = resolver.ip
        self.target_port = resolver.port
    
    async def worker(self, session: aiohttp.ClientSession):
        try:
            while True:
                url, depth = await self.task_queue.get()  # Pull task from the queue
                
                try:
                    await self.process(session, url, depth)  # Process the URL
                finally:
                    self.task_queue.task_done()  # Mark the task as done

        except asyncio.CancelledError:
            pass


    async def start_workers(self, session: aiohttp.ClientSession):
        logging.debug(f'Starting workiers with session: {session}')
        for _ in range(self.config.get("threads", 100)): # Number of workers
            worker_task = asyncio.create_task(self.worker(session), name=f"worker-{_}") # Start the worker coroutines
            self.workers.append(worker_task)

    async def start_tasks(self, base_url: str, depth: int = 0):
        self.resolve_network_identity(base_url)
        try:
            connector = aiohttp.TCPConnector(
                limit=self.config['threads'],
                ttl_dns_cache=300
            )

            async with aiohttp.ClientSession(connector=connector) as session:
                try:
                    await self.start_workers(session)
                    await self.create_tasks_queue(base_url, depth)
                    await self.task_queue.join()  # Wait for queue to empty

                finally:
                    for worker in self.workers:
                        worker.cancel()
        except Exception as e:
            raise e
        
    def update_total_requests(self, entries: int):
        if self.total_entries > 0:
            self.total_entries += entries
        else:
            self.total_entries = entries

    async def create_tasks_queue(self, base_url: str, depth: int):
        logging.debug(f'Starting tasks queue for: {base_url} with depth: {depth}')
        self.entries = self.generate_entries(base_url)
        self.update_total_requests(len(self.entries))
        for url in self.entries:
            await self.task_queue.put((url, depth))  # Queue tasks for workers
     
    def generate_entries(self, base_url: str):
        raise NotImplementedError("Subclasses must implement generate_entries(url)")
     
    async def process(self, session: aiohttp.ClientSession, url: str, depth: int = 0):
        raise NotImplementedError("Subclasses must implement process(session, url, depth)")
    
    def get_status_table(self):
        table = Table.grid()
        table.add_column()

        elapsed = time.time() - self.start_time
        rps = self.calculate_rps()
        percentage = (self.completed / self.total_entries) * 100 if self.total_entries > 0 else 0

        results_table = Table.grid(padding=(0, 10))
        results_table.add_column("Result", no_wrap=True)
        results_table.add_column("Details", no_wrap=True)
        
        with self.lock:
            for result, code, size, words, lines in sorted(self.valid_results):
                path_colored = Text(result, style=colored_status(code))
                status_info = Text.assemble(
                    ("[", "white"),
                    ("Status", "bold white"), (": ", "white"), (str(code), "bold cyan"),
                    (", ", "white"),
                    ("Size", "bold white"), (": ", "white"), (str(size), "bold cyan"),
                    (", ", "white"),
                    ("Words", "bold white"), (": ", "white"), (str(words), "bold cyan"),
                    (", ", "white"),
                    ("Lines", "bold white"), (": ", "white"), (str(lines), "bold cyan"),
                    ("]", "white")
                )
                results_table.add_row(path_colored, status_info)

        table.add_row(results_table)

        stats_table = Table.grid()
        stats_table.add_column()
        stats_table.add_row(Text.from_markup(
            f"[bold green]Requests:[/] {self.completed}/{self.total_entries} ({percentage:.1f}%) | "
            f"[bold yellow]Speed:[/] {rps:.0f} req/sec | "
            f"[bold cyan]Time:[/] {elapsed:.1f}s | "
            f"[bold red]Errors:[/] {self.errors}"
        ))
        table.add_row('')
        table.add_row(stats_table)
        return table

import asyncio
import logging
from rich.live import Live
from rich.console import Console

from .dir import Directory
from .vhost import Vhost

class Fuzzer:
    def __init__(self, mode: str, config: dict):
        self.mode = mode.lower()
        self.config = config
        self.console = Console()
        self.valid_results = []

        self.fuzzer = self.strategy()

    def strategy(self):
        """Initialize and return the correct fuzzer based on selected mode."""
        strategy_map = {
            "dir": Directory,
            "vhost": Vhost,
        }

        if self.mode not in strategy_map:
            raise ValueError(f"[!] Unsupported fuzzer mode: {self.mode}")

        return strategy_map[self.mode](config=self.config)

    async def start(self, url: str):
        """Public method to run the fuzzer synchronously (hides async)."""
        await self._run_event_loop(url)

    async def _run_event_loop(self, url: str):
        """Main async runner that wraps Live view and task handling."""
        with Live(console=self.console, refresh_per_second=10) as live:
            task = asyncio.create_task(self._start_fuzzing_task(url))

            try:
                while not task.done():
                    live.update(self._get_status())
                    await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                await self._handle_interrupt(task)

            live.update(self._get_status())
            self.valid_results = self.fuzzer.valid_results

    async def _start_fuzzing_task(self, url: str):
        """Starts the actual fuzzer's async fuzzing task."""
        try:
            await self.fuzzer.start_tasks(url)
        except Exception as e:
            logging.error(f"Unexpected Error: {e}")
            raise e

    def _get_status(self):
        """Fetch the status table from the current fuzzer instance."""
        return self.fuzzer.get_status_table()

    async def _handle_interrupt(self, task: asyncio.Task):
        """Gracefully handle keyboard interrupt and cancel tasks."""
        logging.warning("Interrupted by user, stopping workers...")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
