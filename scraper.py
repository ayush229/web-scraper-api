from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse


def scrape_website(url, type="beautify"):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}

    soup = BeautifulSoup(response.text, 'html.parser')

    if type == "raw":
        return {
            "status": "success",
            "url": url,
            "type": "raw",
            "data": soup.prettify()
        }

    # Structured content with headings, paragraphs, image and link info
    content = []
    sections = soup.find_all(['section', 'div', 'article'])
    for sec in sections:
        section_data = {
            "heading": None,
            "content": [],
            "images": [],
            "links": []
        }

        heading = sec.find(['h1', 'h2', 'h3', 'h4', 'h5'])
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
                section_data["links"].append(urljoin(url, href))

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


def crawl_website(base_url, type="beautify", max_pages=10):
    visited = set()
    to_visit = [base_url]
    domain = urlparse(base_url).netloc

    all_data = []
    page_count = 0

    while to_visit and page_count < max_pages:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue

        visited.add(current_url)
        try:
            result = scrape_website(current_url, type)
            if result["status"] == "success":
                page_data = {
                    "url": current_url,
                    "sections": result["data"]["sections"] if "sections" in result["data"] else result["data"]
                }
                all_data.append(page_data)

                # Extract and queue internal links
                for section in page_data["sections"]:
                    links = section.get("links", [])
                    for link in links:
                        parsed = urlparse(link)
                        if parsed.netloc == domain and link not in visited and link not in to_visit:
                            to_visit.append(link)

                page_count += 1
        except Exception as e:
            continue

    return {
        "status": "success",
        "url": base_url,
        "type": f"crawl_{type}",
        "data": all_data
    }
