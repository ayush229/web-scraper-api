# main.py

from flask import Flask, request, jsonify, make_response
from functools import wraps
from scraper import scrape_website, crawl_website
import logging
import os
from together import Together

app = Flask(__name__)

# Authentication credentials
AUTH_USERNAME = "ayush1"
AUTH_PASSWORD = "blackbox098"

# Initialize Together API client using the API token from environment variable
client = Together()

def check_auth(username, password):
    return username == AUTH_USERNAME and password == AUTH_PASSWORD

def authenticate():
    return make_response(
        jsonify({"error": "Authentication required"}),
        401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def ask_llama(prompt):
    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
            messages=[{"role": "user", "content": prompt}]
        )
        if response.choices:
            return response.choices[0].message.content.strip()
        else:
            return None
    except Exception as e:
        print(f"LLM error: {e}")
        return None

@app.route('/scrape', methods=['GET', 'POST'])
@requires_auth
def scrape():
    try:
        if request.method == 'GET':
            url = request.args.get('url')
            content_type = request.args.get('type', 'beautify')
            user_query = request.args.get('user_query', '')
        else:
            try:
                data = request.get_json(force=True) or {}
            except Exception:
                data = {}
            url = data.get('url', '')
            content_type = data.get('type', 'beautify')
            user_query = data.get('user_query', '')

        if not url:
            return jsonify({
                "status": "error",
                "error": "URL parameter is required"
            }), 400

        if content_type not in (
            'raw', 'beautify', 'ai',
            'crawl_raw', 'crawl_beautify', 'crawl_ai'
        ):
            return jsonify({
                "status": "error",
                "error": "Invalid type parameter."
            }), 400

        # Handle crawling types with extended logic
        if content_type.startswith("crawl_"):
            crawl_type = content_type.replace("crawl_", "")
            initial_scrape = scrape_website(url, 'beautify')
            if initial_scrape["status"] == "error":
                return jsonify(initial_scrape), 500

            unique_links = set()
            if "sections" in initial_scrape["data"]:
                for section in initial_scrape["data"]["sections"]:
                    for link in section.get("links", []):
                        unique_links.add(link)

            all_page_content = {}
            all_page_content[url] = initial_scrape["data"]
            visited_urls = {url}

            for link in list(unique_links):  # Iterate over a copy to allow modifications
                if link not in visited_urls:
                    page_result = scrape_website(link, 'beautify' if crawl_type == 'ai' else crawl_type)
                    if page_result["status"] == "success":
                        all_page_content[link] = page_result["data"]
                        visited_urls.add(link)

            if crawl_type == "ai":
                full_text = ""
                for page_url, page_data in all_page_content.items():
                    if "sections" in page_data:
                        for sec in page_data["sections"]:
                            if sec.get("heading") and sec["heading"].get("text"):
                                full_text += f"\n\n{sec['heading']['text']}"
                            for para in sec.get("content", []):
                                full_text += f"\n{para}"
                prompt = f"""You are an intelligent assistant helping users get answers from website content.
User query: "{user_query}"
Website content: \"\"\"{full_text}\"\"\"
Answer the query in a natural and informative way. If no answer is found, say: "Sorry, not found."
"""
                ai_response = ask_llama(prompt)
                if not ai_response or "Sorry, not found" in ai_response or len(ai_response.strip()) < 10:
                    ai_response = "Sorry, not found"
                return jsonify({
                    "status": "success",
                    "url": url,
                    "type": "crawl_ai",
                    "ai_response": ai_response
                })
            elif crawl_type in ["raw", "beautify"]:
                crawl_data = []
                for page_url, page_data in all_page_content.items():
                    crawl_data.append({"url": page_url, "data": page_data})
                return jsonify({
                    "status": "success",
                    "url": url,
                    "type": content_type,
                    "data": crawl_data
                })

        # Handle normal raw/beautify/ai
        result = scrape_website(url, 'beautify' if content_type == 'ai' else content_type)

        if result["status"] == "error":
            return jsonify(result), 500

        if content_type == 'ai':
            scraped_text = ""
            try:
                if "sections" in result["data"]:
                    sections = result["data"]["sections"]
                    for sec in sections:
                        if sec.get("heading") and sec["heading"].get("text"):
                            scraped_text += f"\n\n{sec['heading']['text']}"
                        for para in sec.get("content", []):
                            scraped_text += f"\n{para}"
            except Exception as e:
                print(f"Content parsing failed: {e}")
                return jsonify({
                    "status": "error",
                    "error": "Failed to parse structured content for AI query"
                }), 500

            prompt = f"""You are an intelligent assistant helping users get answers from a website's text.
User query: "{user_query}"
Website content: \"\"\"{scraped_text}\"\"\"
Answer the query in a natural and informative way. If no answer is found, say: "Sorry, not found."
"""
            ai_response = ask_llama(prompt)
            if not ai_response or "Sorry, not found" in ai_response or len(ai_response.strip()) < 10:
                ai_response = "Sorry, not found"

            return jsonify({
                "status": "success",
                "url": url,
                "type": "ai",
                "ai_response": ai_response
            })

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

# scraper.py

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
                page_count += 1

                # Only add internal links for future crawling
                if "sections" in result["data"]:
                    for section in result["data"]["sections"]:
                        links = section.get("links", [])
                        for link in links:
                            parsed = urlparse(link)
                            clean_link = link.rstrip('/')

                            if (parsed.netloc == domain or parsed.netloc == '') and clean_link not in visited and clean_link not in to_visit:
                                to_visit.append(clean_link)
            elif result["status"] == "error":
                print(f"Error scraping {current_url}: {result['error']}")
        except Exception as e:
            print(f"Error processing {current_url}: {e}")
            continue

    return {
        "status": "success",
        "url": base_url,
        "type": f"crawl_{type}",
        "data": all_data
    }
