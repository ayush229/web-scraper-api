# scraper.py

from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse
import logging

# Configure logging (optional, but recommended for debugging)
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def scrape_website(url, type="beautify"):
    """
    Scrapes a website and extracts content.

    Args:
        url (str): The URL of the website to scrape.
        type (str, optional): The type of content to extract.  Defaults to "beautify".
            Valid values are "raw" and "beautify".

    Returns:
        dict: A dictionary containing the status of the scraping operation and the extracted data.
            - "status": "success" or "error"
            - "url": The URL of the website.
            - "type": The type of content extracted.
            - "data": The extracted data.  If type is "raw", this is the raw HTML.
                      If type is "beautify", this is a structured dictionary.
            - "error": (Only present if status is "error") A string describing the error.
    """
    try:
        response = requests.get(url, timeout=15)  # Increased timeout slightly
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        error_message = f"Request failed for {url}: {str(e)}"
        logger.error(error_message)  # Log the error
        return {"status": "error", "error": error_message}

    try:
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
                    # Construct absolute URLs using urljoin
                    abs_url = urljoin(url, src)
                    section_data["images"].append(abs_url)

            for a in sec.find_all("a"):
                href = a.get("href")
                if href:
                    # Construct absolute URLs and remove hash anchors
                    abs_url = urljoin(url, href.split('#')[0])
                    section_data["links"].append(abs_url)

            # Only include sections with data
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
    except Exception as e:
        error_message = f"Error processing {url}: {str(e)}"
        logger.error(error_message)
        return {"status": "error", "error": error_message}



def crawl_website(base_url, type="beautify", max_pages=50):
    """
    Crawls a website, starting from a base URL, and extracts content from multiple pages.

    Args:
        base_url (str): The starting URL for the crawl.
        type (str, optional): The type of content to extract. Defaults to "beautify".
            Valid values are "raw" and "beautify".
        max_pages (int, optional): The maximum number of pages to crawl. Defaults to 50.

    Returns:
        dict: A dictionary containing the status of the crawl and the extracted data.
            - "status": "success" or "error"
            - "url": The base URL of the crawl.
            - "type": The type of content extracted.
            - "data": A list of dictionaries, where each dictionary represents the data from a crawled page.
                      Each page dictionary contains:
                        - "url": The URL of the page.
                        - "raw_data": (If type is "raw") The raw HTML of the page.
                        - "content": (If type is "beautify") A list of structured content sections.
            - "error": (Only present if status is "error") A string describing the error.
    """
    visited = set()
    to_visit = [base_url]
    domain = urlparse(base_url).netloc
    all_data = []

    try:
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
                        elif result["data"]: # handle when result["data"] is not None
                            page_data["content"] = [{"heading": None, "paragraphs": [result["data"]]}]
                    all_data.append(page_data)
                else:
                    logger.error(f"Error scraping {current_url} during crawl: {result['error']}")
                    all_data.append({"url": current_url, "error": result["error"]})
            except Exception as e:
                error_message = f"Error processing {current_url}: {e}"
                logger.error(error_message)
                all_data.append({"url": current_url, "error": error_message})

        return {
            "status": "success",
            "url": base_url,
            "type": f"crawl_{type}",
            "data": all_data
        }
    except Exception as e:
        error_message = f"Crawl failed for {base_url}: {e}"
        logger.error(error_message)
        return {"status": "error", "error": error_message}
