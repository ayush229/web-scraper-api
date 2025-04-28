from flask import Flask, request, jsonify, make_response
from functools import wraps
from scraper import scrape_website
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Authentication credentials
AUTH_USERNAME = "ayush1"
AUTH_PASSWORD = "blackbox098"

def check_auth(username, password):
    """Check if username/password are correct"""
    return username == AUTH_USERNAME and password == AUTH_PASSWORD

def authenticate():
    """Send 401 response with auth prompt"""
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
        logging.info(f"Scrape request received. Method: {request.method}")
        if request.method == 'GET':
            url = request.args.get('url')
            content_type = request.args.get('type', 'beautify')
            logging.info(f"GET request - URL: {url}, Type: {content_type}")
        else:
            data = request.get_json()
            url = data.get('url')
            content_type = data.get('type', 'beautify')
            logging.info(f"POST request - URL: {url}, Type: {content_type}, Data: {data}")

        if not url:
            logging.warning("URL parameter is missing.")
            return jsonify({
                "status": "error",
                "error": "URL parameter is required"
            }), 400

        if content_type not in ('raw', 'beautify'):
            logging.warning(f"Invalid content type: {content_type}")
            return jsonify({
                "status": "error",
                "error": "Invalid type parameter. Use 'raw' or 'beautify'"
            }), 400

        logging.info(f"Calling scrape_website for URL: {url} with type: {content_type}")
        result = scrape_website(url, content_type)
        logging.info(f"scrape_website returned: {result['status']}")

        if result["status"] == "error":
            logging.error(f"Scraping error for URL {url}: {result['error']}")
            return jsonify(result), 500

        return jsonify(result)

    except Exception as e:
        logging.exception("An unexpected error occurred during the scrape request.")
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    logging.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=5000)
