from bs4 import BeautifulSoup
import requests
import re
import os
import time

OLLAMA_ENDPOINT = os.getenv('OLLAMA_ENDPOINT', 'http://ollama:11434/api/generate')
MAX_CONTENT_LENGTH = 6000  # Keep responses manageable
REQUEST_TIMEOUT = 30  # Seconds

def clean_text(text):
    """Efficient text cleaning with length limit"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', re.sub(r'[^\w\s.,!?-]', ' ', text)).strip()
    return text[:MAX_CONTENT_LENGTH]

def get_ai_response(prompt, content):
    """Robust Ollama API handler with retries"""
    for attempt in range(3):
        try:
            response = requests.post(
                OLLAMA_ENDPOINT,
                json={
                    "model": "mistral",
                    "prompt": f"Analyze this content: {content[:5000]}\n\nQuestion: {prompt}\n\nAnswer:",
                    "stream": False,
                    "options": {"temperature": 0.5}
                },
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json().get("response", "No response generated")
        except requests.exceptions.RequestException:
            if attempt == 2:
                return "AI service unavailable"
            time.sleep(2)

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
        return {"content": content}
            
    except Exception as e:
        return {"error": str(e)}
