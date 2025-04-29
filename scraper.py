import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def scrape_website(url, mode='beautify'):
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        if mode == 'raw':
            return {
                "status": "success",
                "data": soup.get_text()
            }

        # beautify
        structured = []
        for section in soup.find_all(['section', 'div']):
            heading_tag = section.find(['h1', 'h2', 'h3'])
            paragraphs = section.find_all(['p', 'li'])

            section_data = {
                "heading": {"text": heading_tag.get_text(strip=True)} if heading_tag else {},
                "content": [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
            }

            if section_data["heading"] or section_data["content"]:
                structured.append(section_data)

        return {
            "status": "success",
            "data": {
                "url": url,
                "sections": structured
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Scrape failed: {str(e)}"
        }


def crawl_website(base_url, mode='beautify', max_pages=5):
    try:
        visited = set()
        to_visit = [base_url]
        pages_data = []

        while to_visit and len(visited) < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)

            try:
                res = requests.get(current_url, timeout=10)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, 'html.parser')
            except Exception:
                continue

            if mode == 'raw':
                pages_data.append({
                    "url": current_url,
                    "content": soup.get_text()
                })
                continue

            # beautify
            page_sections = []
            for section in soup.find_all(['section', 'div']):
                heading_tag = section.find(['h1', 'h2', 'h3'])
                paragraphs = section.find_all(['p', 'li'])

                section_data = {
                    "heading": {"text": heading_tag.get_text(strip=True)} if heading_tag else {},
                    "content": [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
                }

                if section_data["heading"] or section_data["content"]:
                    page_sections.append(section_data)

            pages_data.append({
                "url": current_url,
                "sections": page_sections
            })

            # extract links
            for a_tag in soup.find_all('a', href=True):
                full_url = urljoin(base_url, a_tag['href'])
                if full_url.startswith(base_url) and full_url not in visited and len(visited) + len(to_visit) < max_pages:
                    to_visit.append(full_url)

        return {
            "status": "success",
            "data": pages_data
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Crawling failed: {str(e)}"
        }
