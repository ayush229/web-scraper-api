from flask import Flask, request, jsonify, make_response
from functools import wraps
from scraper import scrape_website
import subprocess
from threading import Thread
import logging

app = Flask(__name__)

# --- Authentication Setup ---
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

# --- Start Ollama in Background ---
def run_ollama():
    try:
        subprocess.run([
            "ollama", "serve"
        ], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Ollama failed to start: {e}")

# Start Ollama when Flask app launches
Thread(target=run_ollama, daemon=True).start()

# --- API Endpoint ---
@app.route('/scrape', methods=['GET', 'POST'])
@requires_auth
def scrape():
    try:
        if request.method == 'GET':
            url = request.args.get('url')
            content_type = request.args.get('type', 'beautify')
            user_prompt = request.args.get('user_prompt')
        else:
            data = request.get_json()
            url = data.get('url')
            content_type = data.get('type', 'beautify')
            user_prompt = data.get('user_prompt')

        if not url:
            return jsonify({"status": "error", "error": "URL is required"}), 400

        if content_type not in ('raw', 'beautify', 'ai'):
            return jsonify({"status": "error", "error": "Invalid type. Use 'raw', 'beautify', or 'ai'"}), 400

        if content_type == 'ai' and not user_prompt:
            return jsonify({"status": "error", "error": "user_prompt required for AI mode"}), 400

        result = scrape_website(url, content_type, user_prompt)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": f"Internal error: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
