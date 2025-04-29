from flask import Flask, request, jsonify, make_response
from functools import wraps
from scraper import scrape_website, crawl_website  # extended import
import logging
import os
from together import Together  # Importing Together Python client

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

        # Handle crawling types
        if content_type.startswith("crawl_"):
            crawl_type = content_type.replace("crawl_", "")
            crawl_result = crawl_website(url, crawl_type)

            if crawl_result["status"] == "error":
                return jsonify(crawl_result), 500

            if content_type == "crawl_ai":
                full_text = ""
                for page in crawl_result["data"]:
                    for sec in page["sections"]:
                        if sec.get("heading") and sec["heading"].get("text"):
                            full_text += f"\n\n{sec['heading']['text']}"
                        for para in sec.get("content", []):
                            full_text += f"\n{para}"

                prompt = f"""You are an intelligent assistant helping users get answers from a website's text.
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
                    "ai_response": ai_response,
                    "pages": [
                        {
                            "url": page["url"],
                            "sections": page.get("sections")
                        }
                        for page in crawl_result["data"]
                    ]
                })

            return jsonify({
                "status": "success",
                "url": url,
                "type": content_type,
                "pages": [
                    {
                        "url": page["url"],
                        "sections": page.get("sections")
                    }
                    for page in crawl_result["data"]
                ]
            })

        # Handle normal raw/beautify/ai
        result = scrape_website(url, 'beautify' if content_type == 'ai' else content_type)

        if result["status"] == "error":
            return jsonify(result), 500

        if content_type == 'ai':
            scraped_text = ""
            try:
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
