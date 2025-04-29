from flask import Flask, request, jsonify, make_response
from functools import wraps
from scraper import scrape_website
import logging
import os
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Setup logging
logging.basicConfig(level=logging.INFO)

# Authentication credentials from environment
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "password")

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
        else:
            data = request.get_json()
            url = data.get('url')
            content_type = data.get('type', 'beautify')

        if not url:
            return jsonify({
                "status": "error",
                "error": "URL parameter is required"
            }), 400

        if content_type not in ('raw', 'beautify'):
            return jsonify({
                "status": "error",
                "error": "Invalid type parameter. Use 'raw' or 'beautify'"
            }), 400

        result = scrape_website(url, content_type)

        status_code = 500 if result["status"] == "error" else 200
        return jsonify(result), status_code

    except Exception as e:
        logging.exception("Unexpected server error")
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
