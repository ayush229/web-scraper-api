from bs4 import BeautifulSoup
import requests
import re
from urllib.parse import urljoin

def clean_text(text):
    """Clean and normalize extracted text"""
    if not text:
        return ""
    # Remove HTML entities and special spaces
    text = re.sub(r'&\w+;|[\xa0\u200b]', ' ', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def scrape_website(url, selector=None):
    """Main scraping function"""
    try:
        # Configure browser-like headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # If CSS selector is provided
        if selector:
            elements = soup.select(selector)
            return {
                "status": "success",
                "elements_found": len(elements),
                "result": [clean_text(el.get_text()) for el in elements],
                "status_code": 200
            }
        
        # Default: Extract all readable text
        text_content = clean_text(soup.get_text())
        return {
            "status": "success",
            "result": text_content,
            "status_code": 200
        }

    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error": f"Request failed: {str(e)}",
            "status_code": 400
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Processing error: {str(e)}",
            "status_code": 500
        }
