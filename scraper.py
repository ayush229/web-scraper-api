from bs4 import BeautifulSoup
import requests
import re
import os
import time
from urllib.parse import urljoin

# Configuration
OLLAMA_ENDPOINT = os.getenv('OLLAMA_ENDPOINT', 'http://ollama:11434/api/generate')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'mistral')
MAX_CONTENT_LENGTH = 8000  # Keep responses manageable
REQUEST_TIMEOUT = 45  # Seconds

def clean_text(text):
    """Efficient text cleaning with length limit"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', re.sub(r'[^\w\s.,!?-]', ' ', text)).strip()
    return text[:MAX_CONTENT_LENGTH]

def get_ai_response(prompt, content):
    """Robust Ollama API handler"""
    try:
        start_time = time.time()
        response = requests.post(
            OLLAMA_ENDPOINT,
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"Content: {content[:5000]}\n\nQuestion: {prompt}\n\nAnswer concisely:",
                "stream": False,
                "options": {"temperature": 0.5}
            },
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json().get("response", "No AI response generated")
    except requests.exceptions.RequestException as e:
        return f"AI service error: {type(e).__name__}"
    except Exception as e:
        return f"Processing error: {str(e)}"

def scrape_page(url):
    """Core scraping function with safety limits"""
    try:
        response = requests.get(
            url,
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=10
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove heavy/unwanted elements
        for element in soup(['script', 'style', 'noscript', 'iframe', 'svg']):
            element.decompose()
            
        return clean_text(soup.get_text())
    except Exception as e:
        raise ValueError(f"Scraping failed: {str(e)}")

def handle_request(url, mode='beautify', prompt=None):
    """Unified request handler"""
    try:
        content = scrape_page(url)
        
        if mode == 'raw':
            return {"content": content}
        elif mode == 'ai':
            if not prompt:
                raise ValueError("Prompt required for AI mode")
            return {
                "ai_response": get_ai_response(prompt, content),
                "content_preview": content[:500]
            }
        else:
            return {"content": content}
            
    except Exception as e:
        return {"error": str(e)}
