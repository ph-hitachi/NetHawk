import logging
from nethawk.core.config import Config

import google.generativeai as genai

class GeminiClient:
    model = 'gemini-2.0-flash'

    def __init__(self, api_key=None):
        self.config = Config()
        self.api_key = api_key or self.config.api_keys.GEMINI_API_KEY
    
    def generate_content(self, prompt):
        
        genai.configure(api_key=self.api_key)
    
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(prompt)
        
        return response