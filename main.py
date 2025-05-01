# main.py

from flask import Flask, request, jsonify, make_response
from functools import wraps
from scraper import scrape_website, crawl_website
import logging
import os
from together import Together
from urllib.parse import urlparse, urljoin
import uuid
import re
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

import nltk
try:
    stopwords.words('english')
except LookupError:
    nltk.download('stopwords')
try:
    word_tokenize("example")
except LookupError:
    nltk.download('punkt')

app = Flask(__name__)

# Authentication credentials
AUTH_USERNAME = "ayush1"
AUTH_PASSWORD = "blackbox098"

# Directory to store scraped content
SCRAPED_DATA_DIR = "scraped_content"
os.makedirs(SCRAPED_DATA_DIR, exist_ok=True)

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
        if not auth or not check_auth(auth.auth.username, auth.auth.password):
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

def get_stored_content(unique_code):
    filepath = os.path.join(SCRAPED_DATA_DIR, f"{unique_code}.txt")
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def find_relevant_sentences(content, query, num_sentences=7, min_meaningful_word_match=1):
    """
    Finds sentences in the content that are relevant to the query based on meaningful words.
    It requires at least 'min_meaningful_word_match' meaningful words from the query to be present in a sentence.
    """
    stop_words = set(stopwords.words('english'))
    query_tokens = [w.lower() for w in word_tokenize(query) if w.isalnum() and w.lower() not in stop_words]
    if not query_tokens:
        return []  # If no meaningful words in the query, return empty

    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', content)
    sentence_scores = []

    for sentence in sentences:
        sentence_tokens = [w.lower() for w in word_tokenize(sentence) if w.isalnum() and w.lower() not in stop_words]
        common_meaningful_words = len(set(query_tokens).intersection(sentence_tokens))
        if common_meaningful_words >= min_meaningful_word_match:
            sentence_scores.append((sentence, common_meaningful_words))

    sentence_scores.sort(key=lambda item: item[1], reverse=True)
    return [sentence for sentence, score in sentence_scores[:num_sentences]]

def process_crawl(base_url, crawl_type):
    visited = set()
    to_visit = [base_url]
    all_data = []
    domain = urlparse(base_url).netloc

    while to_visit:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)

        result = scrape_website(current_url, 'beautify')
        if result["status"] == "success":
            page_data = {"url": current_url, "content": []}
            if "sections" in result["data"]:
                for section in result["data"]["sections"]:
                    section_content = {"heading": section.get("heading"), "paragraphs": section.get("content", [])}
                    page_data["content"].append(section_content)
                    if crawl_type != "crawl_raw":
                        for link in section.get("links", []):
                            parsed_link = urlparse(link)
                            absolute_link = urljoin(current_url, parsed_link.path)
                            if parsed_link.netloc == domain or parsed_link.netloc == '':
                                clean_link = absolute_link.rstrip('/')
                                if clean_link not in visited and clean_link not in to_visit:
                                    to_visit.append(clean_link)
            elif crawl_type == "crawl_raw":
                page_data["raw_data"] = result["data"]
            all_data.append(page_data)
        else:
            print(f"Error scraping {current_url} during crawl: {result['error']}")
            all_data.append({"url": current_url, "error": result["error"]}) # Include error in response

    return all_data

@app.route('/scrape_and_store', methods=['POST'])
@requires_auth
def scrape_and_store():
    try:
        data = request.get_json(force=True) or {}
        urls_str = data.get('url')  # Changed to get 'url' which should be a comma-separated string
        if not urls_str:
            return jsonify({"status": "error", "error": "URL parameter is required"}), 400

        urls = [url.strip() for url in urls_str.split(',') if url.strip()]  # Split the string into a list of URLs

        combined_text = ""
        for url in urls:
            result = scrape_website(url, 'beautify')
            if result["status"] == "error":
                return jsonify({"status": "error", "error": f"Error scraping {url}: {result['error']}"}), 500  # Return error for individual URL

            try:
                if "sections" in result["data"]:
                    sections = result["data"]["sections"]
                    for sec in sections:
                        if sec.get("heading") and sec["heading"].get("text"):
                            combined_text += f"\n\n{sec['heading']['text']}"
                        for para in sec.get("content", []):
                            combined_text += f"\n{para}"
            except Exception as e:
                print(f"Content parsing failed for storage for url {url}: {e}")
                combined_text += result.get("data", "") # Fallback

        unique_code = str(uuid.uuid4())
        filepath = os.path.join(SCRAPED_DATA_DIR, f"{unique_code}.txt")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(combined_text)

        return jsonify({"status": "success", "unique_code": unique_code})

    except Exception as e:
        return jsonify({"status": "error", "error": f"Internal server error: {str(e)}"}), 500

@app.route('/ask_stored', methods=['POST'])
@requires_auth
def ask_stored():
    try:
        data = request.get_json(force=True) or {}
        unique_code = data.get('unique_code')
        user_query = data.get('user_query')

        if not unique_code:
            return jsonify({"status": "error", "error": "unique_code parameter is required"}), 400
        if not user_query:
            return jsonify({"status": "error", "error": "user_query parameter is required"}), 400

        stored_content = get_stored_content(unique_code)
        if not stored_content:
            return jsonify({"status": "error", "error": f"Content not found for unique_code: {unique_code}"}), 404

        # Find relevant sentences based on meaningful words
        relevant_sentences = find_relevant_sentences(stored_content, user_query)

        if not relevant_sentences:
            return jsonify({"status": "success", "ai_response": "Sorry, I am unable to help you with this.", "ai_used": False})
        else:
            relevant_content = "\n".join(relevant_sentences)
            ai_prompt = f"""As a knowledgeable agent, please provide a direct and conversational answer to the user's question **only if the answer is directly and clearly supported by the following website snippets.** If the answer cannot be confidently derived from these snippets, please respond with: "Sorry, I am unable to help you with this."

User question: "{user_query}"

Relevant website snippets:
\"\"\"{relevant_content}\"\"\"

Provide a direct and conversational answer **strictly based on the content above.** If the information to answer is not explicitly present, respond with: "Sorry, I am unable to help you with this."
"""

            ai_response = ask_llama(ai_prompt)
            if not ai_response or "Sorry, I am unable to help you with this" in ai_response or len(ai_response.strip()) < 10:
                return jsonify({"status": "success", "ai_response": "Sorry, I am unable to help you with this.", "ai_used": True})
            else:
                return jsonify({"status": "success", "ai_response": ai_response, "ai_used": True})

    except Exception as e:
        return jsonify({"status": "error", "error": f"Internal server error: {str(e)}"}), 500

@app.route('/scrape', methods=['GET', 'POST'])
@requires_auth
def scrape():
    try:
        if request.method == 'GET':
            urls_str = request.args.get('url')
            content_type = request.args.get('type', 'beautify')
            user_query = request.args.get('user_query', '')
        else:
            try:
                data = request.get_json(force=True) or {}
            except Exception:
                data = {}
            urls_str = data.get('url', '')
            content_type = data.get('type', 'beautify')
            user_query = data.get('user_query', '')

        if not urls_str:
            return jsonify({
                "status": "error",
                "error": "URL parameter is required"
            }), 400

        urls = [url.strip() for url in urls_str.split(',') if url.strip()]

        if content_type in ['raw', 'beautify']:
            all_results = []
            for url in urls:
                result = scrape_website(url, content_type)
                if result["status"] == "error":
                    all_results.append({"url": url, "error": result["error"]})
                else:
                    all_results.append({"url": url, "data": result["data"]})
            return jsonify(all_results)

        elif content_type == 'ai':
            combined_text = ""
            for url in urls:
                result = scrape_website(url, 'beautify')
                if result["status"] == "error":
                    print(f"Error scraping {url} for AI: {result['error']}")
                elif "sections" in result["data"]:
                    for sec in result["data"]["sections"]:
                        if sec.get("heading") and sec["heading"].get("text"):
                            combined_text += f"\n\n{sec['heading']['text']}"
                        for para in sec.get("content", []):
                            combined_text += f"\n{para}"

            # Find relevant sentences based on meaningful words
            relevant_sentences = find_relevant_sentences(combined_text, user_query)

            if not relevant_sentences:
                return jsonify({
                    "status": "success",
                    "type": "ai",
                    "ai_response": "Sorry, I am unable to help you with this.",
                    "ai_used": False
                })
            else:
                relevant_content = "\n".join(relevant_sentences)
                ai_prompt = f"""As a knowledgeable agent, please provide a direct and conversational answer to the user's question **only if the answer is directly and clearly supported by the following website content.** If the answer cannot be confidently derived from this content, please respond with: "Sorry, I am unable to help you with this."

User question: "{user_query}"

Website content:
\"\"\"{relevant_content}\"\"\"

Provide a direct and conversational answer **strictly based on the content above.** If the information to answer is not explicitly present, respond with: "Sorry, I am unable to help you with this."
"""
                ai_response = ask_llama(ai_prompt)
                if not ai_response or "Sorry, I am unable to help you with this" in ai_response or len(ai_response.strip()) < 10:
                    return jsonify({
                        "status": "success",
                        "type": "ai",
                        "ai_response": "Sorry, I am unable to help you with this.",
                        "ai_used": True
                    })
                else:
                    return jsonify({
                        "status": "success",
                        "type": "ai",
                        "ai_response": ai_response,
                        "ai_used": True
                    })

        elif content_type.startswith("crawl_"):
            all_crawl_data = []
            crawl_type = content_type
            for url in urls:
                crawl_results = process_crawl(url, crawl_type)
                all_crawl_data.extend(crawl_results)

            if crawl_type == "crawl_beautify":
                formatted_crawl_data = []
                for item in all_crawl_data:
                    if "content" in item:
                        formatted_crawl_data.append({"url": item["url"], "content": item["content"]})
                    elif "error" in item:
                        formatted_crawl_data.append({"url": item["url"], "error": item["error"]})
                return jsonify({"status": "success", "type": crawl_type, "data": formatted_crawl_data})
            elif crawl_type == "crawl_raw":
                formatted_crawl_data = []
                for item in all_crawl_data:
                    if "raw_data" in item:
                        formatted_crawl_data.append({"url": item["url"], "data": item["raw_data"]})
                    elif "error" in item:
                        formatted_crawl_data.append({"url": item["url"], "error": item["error"]})
                return jsonify({"status": "success", "type": crawl_type, "data": formatted_crawl_data})
            elif crawl_type == "crawl_ai":
                all_text_content = ""
                for item in all_crawl_data:
                    if "content" in item:
                        for section in item["content"]:
                            if section.get("heading") and section["heading"].get("text"):
                                all_text_content += f"\n\n{section['heading']['text']}"
                            for para in section.get("paragraphs", []):
                                all_text_content += f"\n{para}"

                # Find relevant sentences based on meaningful words
                relevant_sentences = find_relevant_sentences(all_text_content, user_query)

                if not relevant_sentences:
                    return jsonify({
                        "status": "success",
                        "type": crawl_type,
                        "ai_response": "Sorry, I am unable to help you with this.",
                        "ai_used": False
                    })
                else:
                    relevant_content = "\n".join(relevant_sentences)
                    ai_prompt = f"""As a knowledgeable agent, please provide a direct and conversational answer to the user's question **only if the answer is directly and clearly supported by the following website content.** If the answer cannot be confidently derived from this content, please respond with: "Sorry, I am unable to help you with this."

User question: "{user_query}"

Website content:
\"\"\"{relevant_content}\"\"\"

Provide a direct and conversational answer **strictly based on the content above.** If the information to answer is not explicitly present, respond with: "Sorry, I am unable to help you with this."
"""
                    ai_response =
