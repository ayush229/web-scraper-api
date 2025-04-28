from bs4 import BeautifulSoup
import requests
import random
import time
from urllib.parse import urlparse

# List of realistic user agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
]

# Common headers that mimic a real browser
COMMON_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

def get_domain(url):
    """Extract domain from URL"""
    parsed = urlparse(url)
    return parsed.netloc

def scrape_website(url, selector=None, max_retries=3):
    """
    Scrape a website with improved anti-bot bypass techniques
    :param url: URL to scrape
    :param selector: Optional CSS selector to filter elements
    :param max_retries: Number of retries if request fails
    :return: Dictionary with result or error
    """
    session = requests.Session()
    
    for attempt in range(max_retries):
        try:
            # Random delay between requests (1-4 seconds)
            if attempt > 0:
                time.sleep(random.uniform(1, 4))
            
            # Prepare headers for this attempt
            headers = COMMON_HEADERS.copy()
            headers['User-Agent'] = random.choice(USER_AGENTS)
            headers['Referer'] = f'https://{get_domain(url)}/'
            
            # Make the request
            response = session.get(
                url,
                headers=headers,
                timeout=10,
                allow_redirects=True
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Verify we got HTML content
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                return {
                    "error": f"URL does not return HTML content (Content-Type: {content_type})",
                    "status_code": response.status_code
                }
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # If selector provided, return matching elements
            if selector:
                elements = soup.select(selector)
                return {
                    "status": "success",
                    "result": [str(element) for element in elements],
                    "status_code": response.status_code,
                    "elements_found": len(elements)
                }
            
            # Otherwise return the entire body or the whole document
            body = soup.find('body')
            return {
                "status": "success",
                "result": str(body) if body else str(soup),
                "status_code": response.status_code
            }
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                return {
                    "error": f"Request failed after {max_retries} attempts: {str(e)}",
                    "status": "error"
                }
            continue
            
        except Exception as e:
            return {
                "error": f"An unexpected error occurred: {str(e)}",
                "status": "error"
            }
    
    return {
        "error": "Max retries reached without success",
        "status": "error"
    }