# detectors/tech_detector.py

import logging
from rich.console import Console
from rich.table import Table

from nethawk.cli import banner
from nethawk.core.resolver import Resolver
from nethawk.extensions.network.scanner import NetworkScanner
from .ai import AIDetector
from .wappalyzer import WappalyzerDetector
from nethawk.extensions.network.service_scanner import ServiceScanner


class Detector:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.console = Console()
        self.ai = AIDetector()
        self.wappalyzer = WappalyzerDetector()
        self.scanner = ServiceScanner()

    def merge_tech_data(self, wappalyzer_data, ai_data):
        if not isinstance(ai_data, dict):
            return wappalyzer_data

        for tech, ai_info in ai_data.items():
            if tech not in wappalyzer_data:
                wappalyzer_data[tech] = ai_info
            else:
                existing = wappalyzer_data[tech]
                existing.setdefault('groups', ai_info.get('groups', []))
                existing.setdefault('categories', ai_info.get('categories', []))
                if not existing.get('version') and ai_info.get('version'):
                    existing['version'] = ai_info['version']
        return wappalyzer_data

    def group_technologies(self, techs, ai_results):
        grouped = {}
        ai_results = ai_results or []  # Fix fallback to empty list if None

        for name, info in techs.items():
            group = (info.get('groups') or ["Unknown"])[0]
            categories = info.get("categories", ["Unknown"])
            grouped.setdefault(group, []).append({
                'name': name,
                'version': info.get("version", ""),
                'categories': categories if isinstance(categories, list) else [categories],
                'confidence': f"{info.get('confidence', 0)}%",
                'group': group,
                'detected_by': 'genai' if name in ai_results else 'wappalyzer'
            })

        return grouped


    def get_technologies(self, url):
        try:
            wappalyzer_results = self.wappalyzer.detect(url)
            ai_results = self.ai.detect(url)
            self.logger.debug(f"AI Detected: {ai_results}")
            self.logger.debug(f"Wappalyzer Detected: {wappalyzer_results}")

            url_key = next(iter(wappalyzer_results.keys()), None)
            if not url_key:
                return

            combined_techs = self.merge_tech_data(wappalyzer_results[url_key], ai_results)
            grouped = self.group_technologies(combined_techs, ai_results)

            return grouped

        except Exception as e:
            self.logger.error(f"Unexpected Error: {e}")
            raise
