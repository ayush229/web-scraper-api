from flask import Flask, request, jsonify, make_response
from functools import wraps
from scraper import scrape_website
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Authentication
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
        # Get parameters
        if request.method == 'GET':
            url = request.args.get('url')
            selector = request.args.get('selector')
        else:
            data = request.get_json()
            url = data.get('url')
            selector = data.get('selector')

        if not url:
            return jsonify({
                "status": "error",
                "error": "URL parameter is required"
            }), 400

        result = scrape_website(url, selector)
        
        if result["status"] == "error":
            return jsonify(result), result.get("status_code", 500)
            
        return jsonify(result)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Internal server error"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
