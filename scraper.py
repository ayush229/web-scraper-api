from bs4 import BeautifulSoup, FeatureNotFound
import requests
import re
from urllib.parse import urljoin

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'&\w+;|[\xa0\u200b]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def organize_content_by_headings(soup, base_url):
    sections = []
    current_section = None

    for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'img', 'a']):
        if element.name.startswith('h'):
            if current_section:
                sections.append(current_section)
            current_section = {
                "heading": {
                    "level": int(element.name[1]),
                    "text": clean_text(element.get_text())
                },
                "content": [],
                "images": [],
                "links": []
            }
        else:
            if not current_section:
                current_section = {
                    "heading": None,
                    "content": [],
                    "images": [],
                    "links": []
                }

            if element.name in ['p', 'ul', 'ol']:
                text = clean_text(element.get_text())
                if text:
                    current_section["content"].append(text)
            elif element.name == 'img' and element.get('src'):
                current_section["images"].append({
                    "url": urljoin(base_url, element['src']),
                    "alt": clean_text(element.get('alt', ''))
                })
            elif element.name == 'a' and element.get('href'):
                if not element['href'].startswith(('#', 'javascript:')):
                    current_section["links"].append({
                        "url": urljoin(base_url, element['href']),
                        "text": clean_text(element.get_text())
                    })

    if current_section:
        sections.append(current_section)

    return sections

def extract_raw_content(soup, base_url):
    return {
        "raw_html": str(soup),
        "images": [urljoin(base_url, img['src']) 
                  for img in soup.find_all('img') if img.get('src')],
        "links": [urljoin(base_url, a['href']) 
                 for a in soup.find_all('a', href=True) 
                 if not a['href'].startswith(('#', 'javascript:'))]
    }

def extract_beautified_content(soup, base_url):
    content = {
        "metadata": {
            "title": clean_text(soup.title.string if soup.title else ""),
            "description": clean_text(soup.find('meta', attrs={'name': 'description'})['content']) 
                          if soup.find('meta', attrs={'name': 'description'}) else ""
        },
        "sections": organize_content_by_headings(soup, base_url)
    }
    return content

def scrape_website(url, content_type='beautify'):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        try:
            soup = BeautifulSoup(response.content, 'html.parser')
        except FeatureNotFound:
            return {
                "status": "error",
                "url": url,
                "error": "HTML parser not found or failed"
            }

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

    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "url": url,
            "error": "Request timed out. Please try again later."
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "url": url,
            "error": f"Request error: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "url": url,
            "error": f"Unexpected error: {str(e)}"
        }
