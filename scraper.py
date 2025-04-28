from bs4 import BeautifulSoup
import requests
import re
from urllib.parse import urlparse

def clean_text(text):
    """
    Clean and format extracted text by:
    - Removing extra whitespace
    - Removing special characters (optional)
    - Normalizing spacing
    """
    # Remove HTML entities
    text = re.sub(r'&\w+;', ' ', text)
    # Convert multiple spaces/newlines to single space
    text = re.sub(r'\s+', ' ', text).strip()
    # Optional: Remove non-ASCII characters
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text

def scrape_website(url, selector=None):
    """
    Scrape a website and return clean, readable text
    :param url: URL to scrape
    :param selector: Optional CSS selector to target specific elements
    :return: Dictionary with status, data, and source URL
    """
    try:
        # Configure request to look like a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        # Fetch the webpage
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise error for bad status codes

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # If CSS selector is provided
        if selector:
            elements = soup.select(selector)
            results = [clean_text(el.get_text()) for el in elements if el.get_text().strip()]
            return {
                "status": "success",
                "data": results if len(results) > 1 else results[0] if results else "No matching elements found",
                "source_url": url
            }

        # Otherwise, try to find main content automatically
        content_containers = [
            'main', 'article', '.content', '#content',
            '#main', '#bodyContent', '.post-content',
            '.article-body', '.entry-content'
        ]

        for container in content_containers:
            content = soup.select_one(container)
            if content:
                return {
                    "status": "success",
                    "data": clean_text(content.get_text()),
                    "source_url": url
                }

        # Fallback to body if no containers found
        body = soup.find('body')
        return {
            "status": "success",
            "data": clean_text(body.get_text()) if body else "No readable content found",
            "source_url": url
        }

    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error": f"Request failed: {str(e)}",
            "source_url": url
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"An error occurred: {str(e)}",
            "source_url": url
        }
