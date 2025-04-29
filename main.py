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

def extract_text_from_section(section):
    text = ""
    if section.get("heading") and section["heading"].get("text"):
        text += f"{section['heading']['text']} "
    for para in section.get("content", []):
        text += f"{para} "
    return text.strip().lower()

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
                    return jsonify(result), 500
                all_results.append({"url": url, "data": result["data"]})
            return jsonify(all_results)

        elif content_type == 'ai':
            combined_text = ""
            for url in urls:
                result = scrape_website(url, 'beautify')
                if result["status"] == "error":
                    return jsonify(result), 500
                if "sections" in result["data"]:
                    for sec in result["data"]["sections"]:
                        if sec.get("heading") and sec["heading"].get("text"):
                            combined_text += f"\n\n{sec['heading']['text']}"
                        for para in sec.get("content", []):
                            combined_text += f"\n{para}"

            prompt = f"""You are an intelligent assistant. Your goal is to answer the user's query directly and concisely based on the provided website content from multiple URLs.

User query: "{user_query}"

Website content:
\"\"\"{combined_text}\"\"\"

Answer the user's query directly. If the answer is not found within the content, or if the query is irrelevant to the content, respond with: "Sorry, not found."
Do not include introductory phrases like "To find...", "According to...", or similar language. Just provide the direct answer if found.
"""
            ai_response = ask_llama(prompt)
            if not ai_response or "Sorry, not found" in ai_response or len(ai_response.strip()) < 10:
                ai_response = "Sorry, not found"
            return jsonify({
                "status": "success",
                "type": "ai",
                "ai_response": ai_response
            })

        elif content_type == "crawl_ai":
            all_crawled_content = {}
            for url in urls:
                crawl_result = crawl_website(url, 'beautify')
                if crawl_result["status"] == "success":
                    all_crawled_content[url] = crawl_result["data"]
                else:
                    return jsonify(crawl_result), 500

            relevant_content = []
            query_words = user_query.lower().split()

            for base_url, pages_data in all_crawled_content.items():
                for page in pages_data:
                    if "sections" in page:
                        for section in page["sections"]:
                            section_text_lower = extract_text_from_section(section)
                            for word in query_words:
                                if word in section_text_lower:
                                    relevant_content.append(section)
                                    break

            combined_relevant_text = ""
            for section in relevant_content:
                if section.get("heading") and section["heading"].get("text"):
                    combined_relevant_text += f"\n\n{section['heading']['text']}"
                for para in section.get("content", []):
                    combined_relevant_text += f"\n{para}"

            prompt = f"""You are an intelligent assistant. Your goal is to answer the user's query directly and concisely based on the relevant parts of website content crawled from multiple URLs.

User query: "{user_query}"

Relevant website content:
\"\"\"{combined_relevant_text}\"\"\"

Answer the user's query directly. If the answer is not found within the content, or if the query is irrelevant to the content, respond with: "Sorry, not found."
Do not include introductory phrases like "To find...", "According to...", or similar language. Just provide the direct answer if found.
"""
            ai_response = ask_llama(prompt)
            if not ai_response or "Sorry, not found" in ai_response or len(ai_response.strip()) < 10:
                ai_response = "Sorry, not found"
            return jsonify({
                "status": "success",
                "type": "crawl_ai",
                "ai_response": ai_response
            })

        elif content_type.startswith("crawl_"): # crawl_raw, crawl_beautify for multiple URLs
            all_crawl_results = []
            crawl_type = content_type.replace("crawl_", "")
            for url in urls:
                crawl_result = crawl_website(url, crawl_type)
                if crawl_result["status"] == "success":
                    all_crawl_results.extend(crawl_result["data"])
                else:
                    return jsonify(crawl_result), 500
            return jsonify({
                "status": "success",
                "type": content_type,
                "data": all_crawl_results
            })

        else:
            return jsonify({
                "status": "error",
                "error": "Invalid type parameter."
            }), 400

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
