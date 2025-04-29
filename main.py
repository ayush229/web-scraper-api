from flask import Flask, request, jsonify, make_response
from functools import wraps
from flask_cors import CORS
from scraper import scrape_website
import logging
import requests

app = Flask(__name__)
CORS(app)

# Authentication credentials
AUTH_USERNAME = "ayush1"
AUTH_PASSWORD = "blackbox098"

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

@app.route('/scrape', methods=['GET', 'POST'])
@requires_auth
def scrape():
    try:
        if request.method == 'GET':
            url = request.args.get('url')
            content_type = request.args.get('type', 'beautify')
            user_query = request.args.get('user_query', '')
        else:
            data = request.get_json()
            url = data.get('url')
            content_type = data.get('type', 'beautify')
            user_query = data.get('user_query', '')

        if not url:
            return jsonify({
                "status": "error",
                "error": "URL parameter is required"
            }), 400

        if content_type not in ('raw', 'beautify', 'ai'):
            return jsonify({
                "status": "error",
                "error": "Invalid type parameter. Use 'raw', 'beautify' or 'ai'"
            }), 400

        # Handle AI flow separately
        if content_type == 'ai':
            if not user_query.strip():
                return jsonify({
                    "status": "error",
                    "error": "user_query parameter is required for type='ai'"
                }), 400

            result = scrape_website(url, 'beautify')

            if result["status"] == "error":
                return jsonify(result), 500

            data = result.get("data", {})
            sections = data.get("sections", []) if isinstance(data, dict) else []

            combined_text = ""
            for section in sections:
                heading = section.get("heading", {}).get("text", "")
                content = " ".join(section.get("content", []))
                combined_text += f"{heading}\n{content}\n"

            if not combined_text.strip():
                return jsonify({
                    "status": "success",
                    "type": "ai",
                    "url": url,
                    "ai_response": "Sorry, not found"
                })

            llama_prompt = f"""
You are a helpful assistant. Using the following content extracted from a website, answer the user query as clearly and concisely as possible.
If the answer is not directly found or relevant, respond with: "Sorry, not found".

### Website Content:
{combined_text}

### User Question:
{user_query}

### Answer:
"""

            headers = {
                "Authorization": "Bearer YOUR_TOGETHER_API_KEY",  # <-- Replace this
                "Content-Type": "application/json"
            }

            payload = {
                "model": "meta-llama/Llama-3-8b-chat-hf",
                "max_tokens": 300,
                "temperature": 0.7,
                "top_p": 0.9,
                "stop": ["</s>"],
                "messages": [
                    {"role": "user", "content": llama_prompt}
                ]
            }

            response = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, json=payload, timeout=20)

            if response.status_code == 200:
                ai_text = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                ai_text = ai_text.strip() or "Sorry, not found"
            else:
                ai_text = "Sorry, not found"

            return jsonify({
                "status": "success",
                "type": "ai",
                "url": url,
                "ai_response": ai_text
            })

        # Handle existing raw/beautify
        result = scrape_website(url, content_type)

        if result["status"] == "error":
            return jsonify(result), 500

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
