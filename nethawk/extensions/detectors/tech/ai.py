# detectors/ai_detector.py
import re
import json
import logging
import requests
from bs4 import BeautifulSoup
from google.auth.exceptions import DefaultCredentialsError
import google.generativeai as genai
from nethawk.core.config import Config

class AIDetector:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        try:
            self.config = Config()
            genai.configure(api_key=self.config.api_keys.GEMINI_API_KEY)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
            self.enabled = True

        except DefaultCredentialsError:
            self.logger.warning("GEMINI API key not set.")
            self.enabled = False

    def extract_title_and_footer(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No title"
        footer = soup.find('footer')
        footer_text = footer.get_text(separator=' ', strip=True) if footer else "No footer"
        return title, footer_text

    def build_prompt(self, title, footer_text):
        return (
            "Analyze the following HTML title and footer to detect any web applications, frameworks, or CMS in use."
            "Return the result in valid JSON format with this structure:\n\n"
            "{\n"
            "  \"<name>\" : {\n"
            "    \"version\": \"<version_if_known_else_leave_blank>\",\n"
            "    \"confidence\": 1-100,\n"
            "    \"categories\": [\"<category>\"],\n"
            "    \"groups\": [\"<groups>\"]\n"
            "  }\n"
            "}\n\n"
            f"Title: {title}\n"
            f"Footer: {footer_text}\n\n"
            "Return only the JSON object, nothing else."
        )

    def detect(self, url):
        if not self.enabled:
            return {}
        
        try:
            response = requests.get(url, timeout=10)
            title, footer = self.extract_title_and_footer(response.text)
            prompt = self.build_prompt(title, footer)
            result = self.model.generate_content(prompt).text.strip()
            clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", result, flags=re.DOTALL)
            return json.loads(clean)
        
        except DefaultCredentialsError:
            logging.warning("GEMINI_API_KEY is not set. Skipped detection.")

        except Exception as e:
            self.logger.error(f"AI detection failed: {e}")
            return {}
