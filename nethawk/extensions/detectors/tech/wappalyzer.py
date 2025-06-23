# detectors/wappalyzer_detector.py
from wappalyzer import analyze

from nethawk.helper.output import suppress_output

class WappalyzerDetector:
    def detect(self, url):
        with suppress_output():
            return analyze(url=url, scan_type='balanced')
