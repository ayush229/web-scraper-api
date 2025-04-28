from bs4 import BeautifulSoup
import requests
import re
from urllib.parse import urljoin

def clean_text(text):
    """Clean and normalize text content"""
    if not text:
        return ""
    text = re.sub(r'&\w+;|[\xa0\u200b]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_raw_content(soup, base_url):
    """Extract completely raw content with all HTML"""
    return {
        "raw_html": str(soup),
        "images": [urljoin(base_url, img['src']) 
                  for img in soup.find_all('img') if img.get('src')],
        "links": [urljoin(base_url, a['href']) 
                 for a in soup.find_all('a', href=True) 
                 if not a['href'].startswith(('#', 'javascript:'))]
    }

def extract_beautified_content(soup, base_url):
    """Extract cleaned and structured content"""
    content = {
        "text": [],
        "headings": [],
        "images": [],
        "metadata": {}
    }

    # Extract clean text from all paragraphs and divs
    for element in soup.find_all(['p', 'div', 'article']):
        text = clean_text(element.get_text())
        if text and len(text) > 20:
            content["text"].append(text)

    # Extract headings
    for level in range(1, 7):
        content["headings"].extend([
            {"level": level, "text": clean_text(h.get_text())}
            for h in soup.find_all(f'h{level}')
        ])

    # Extract images with alt text
    content["images"] = [{
        "url": urljoin(base_url, img['src']),
        "alt": clean_text(img.get('alt', ''))
    } for img in soup.find_all('img') if img.get('src')]

    # Extract metadata
    content["metadata"]["title"] = clean_text(soup.title.string if soup.title else "")
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    content["metadata"]["description"] = clean_text(meta_desc['content']) if meta_desc else ""

    return content

def scrape_website(url, content_type='beautify'):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'noscript']):
            element.decompose()

        if content_type == 'raw':
            result = extract_raw_content(soup, url)
        else:
            result = extract_beautified_content(soup, url)

        return {
            "status": "success",
            "url": url,
            "type": content_type,
            "data": result
        }

    except Exception as e:
        return {
            "status": "error",
            "url": url,
            "error": str(e)
        }
