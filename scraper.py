# scraper.py

from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse


def scrape_website(url, type="beautify"):
    try:
        response = requests.get(url, timeout=15)  # Increased timeout slightly
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}

    soup = BeautifulSoup(response.text, 'html.parser')

    if type == "raw":
        return {
            "status": "success",
            "url": url,
            "type": "raw",
            "data": soup.prettify()
        }

    # Structured content with headings, paragraphs, images, and links
    content = []
    sections = soup.find_all(['section', 'div', 'article'])
    for sec in sections:
        section_data = {
            "heading": None,
            "content": [],
            "images": [],
            "links": []
        }

        heading = sec.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if heading:
            section_data["heading"] = {"tag": heading.name, "text": heading.get_text(strip=True)}

        paragraphs = sec.find_all(['p', 'li'])
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                section_data["content"].append(text)

        for img in sec.find_all("img"):
            src = img.get("src")
            if src:
                section_data["images"].append(urljoin(url, src))

        for a in sec.find_all("a"):
            href = a.get("href")
            if href:
                joined = urljoin(url, href.split('#')[0])  # Remove hash anchors
                section_data["links"].append(joined)

        if section_data["heading"] or section_data["content"] or section_data["images"] or section_data["links"]:
            content.append(section_data)

    return {
        "status": "success",
        "url": url,
        "type": "beautify",
        "data": {
            "sections": content
        }
    }


def crawl_website(base_url, type="beautify", max_pages=50):  # Increased default max_pages
    visited = set()
    to_visit = [base_url]
    domain = urlparse(base_url).netloc
    all_data = []

    while to_visit and len(visited) < max_pages:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)

        try:
            result = scrape_website(current_url, type)
            if result["status"] == "success":
                page_data = {"url": current_url}
                if type == "raw":
                    page_data["raw_data"] = result["data"]
                else:
                    page_data["content"] = []
                    if "sections" in result["data"]:
                        for section in result["data"]["sections"]:
                            section_content = {"heading": section.get("heading"), "paragraphs": section.get("content", [])}
                            page_data["content"].append(section_content)
                            for link in section.get("links", []):
                                parsed_link = urlparse(link)
                                absolute_link = urljoin(current_url, parsed_link.path)
                                if parsed_link.netloc == domain or parsed_link.netloc == '':
                                    clean_link = absolute_link.rstrip('/')
                                    if clean_link not in visited and clean_link not in to_visit:
                                        to_visit.append(clean_link)
                    else:
                        page_data["raw_data"] = result["data"] # Fallback for non-sectioned beautify
                all_data.append(page_data)
            else:
                print(f"Error scraping {current_url} during crawl: {result['error']}")
                all_data.append({"url": current_url, "error": result["error"]})
        except requests.exceptions.RequestException as e:
            print(f"Network error processing {current_url}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during crawl of {current_url}: {e}")

    return {
        "status": "success",
        "url": base_url,
        "type": f"crawl_{type}",
        "data": all_data
    }
