from flask import Flask, request, jsonify, make_response
from functools import wraps
from scraper import scrape_website
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

AUTH_USERNAME = "ayush1"
AUTH_PASSWORD = "blackbox098"
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")  # set this in Railway environment variables

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

def generate_ai_response_llama(query, context_text):
    try:
        prompt = (
            f"Answer this question based only on the context below. "
            f"If the answer is not relevant to the context or not found, respond: 'Sorry, not found'.\n\n"
            f"Context:\n{context_text}\n\nQuestion:\n{query}"
        )

        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "meta-llama/Llama-3-70b-chat-hf",
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post("https://api.together.xyz/v1/chat/completions", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return reply if reply else "Sorry, not found"
    except Exception as e:
        return "Sorry, not found"

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
                "error": "Invalid type parameter. Use 'raw', 'beautify', or 'ai'"
            }), 400

        result = scrape_website(url, 'beautify' if content_type == 'ai' else content_type)

        if result["status"] == "error":
            return jsonify(result), 500

        if content_type == 'ai':
            if not user_query.strip():
                return jsonify({
                    "status": "error",
                    "error": "Missing 'user_query' parameter for type 'ai'"
                }), 400

            context_parts = []
            for section in result['data']['sections']:
                heading = section.get("heading", {}).get("text", "")
                contents = section.get("content", [])
                if heading:
                    context_parts.append(heading)
                context_parts.extend(contents)
            context_text = "\n".join(context_parts)

            ai_response = generate_ai_response_llama(user_query, context_text)
            result["ai_response"] = ai_response

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
