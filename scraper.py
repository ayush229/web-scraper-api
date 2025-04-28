from bs4 import BeautifulSoup
import requests
import re
from urllib.parse import urljoin

def clean_text(text):
    """Clean and normalize extracted text"""
    if not text:
        return ""
    # Remove HTML entities
    text = re.sub(r'&\w+;', ' ', text)
    # Convert all whitespace to single spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_full_page_content(soup, base_url):
    """Extract all meaningful content from the page"""
    results = {
        "text_content": [],
        "images": [],
        "links": [],
        "headings": [],
        "metadata": {}
    }

    # Extract all text content from paragraphs and divs
    for element in soup.find_all(['p', 'div', 'section', 'article']):
        text = clean_text(element.get_text())
        if text and len(text) > 30:  # Only keep meaningful text blocks
            results["text_content"].append(text)

    # Extract all images with src and alt text
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            full_url = urljoin(base_url, src)
            results["images"].append({
                "url": full_url,
                "alt": clean_text(img.get('alt', ''))
            })

    # Extract all links
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and not href.startswith(('javascript:', 'mailto:', 'tel:')):
            full_url = urljoin(base_url, href)
            results["links"].append({
                "url": full_url,
                "text": clean_text(link.get_text())
            })

    # Extract headings hierarchy
    for level in range(1, 7):
        for heading in soup.find_all(f'h{level}'):
            results["headings"].append({
                "level": level,
                "text": clean_text(heading.get_text())
            })

    # Extract metadata
    meta = soup.find('meta', attrs={'name': 'description'})
    results["metadata"]["description"] = clean_text(meta['content']) if meta else ""

    title = soup.find('title')
    results["metadata"]["title"] = clean_text(title.get_text()) if title else ""

    return results

def scrape_website(url, selector=None):
    try:
        # Configure browser-like headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # If specific selector requested
        if selector:
            elements = soup.select(selector)
            selected_content = [clean_text(el.get_text()) for el in elements]
            return {
                "status": "success",
                "selector_results": selected_content,
                "full_content": get_full_page_content(soup, url),
                "status_code": 200
            }

        # Default full page extraction
        return {
            "status": "success",
            "content": get_full_page_content(soup, url),
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
