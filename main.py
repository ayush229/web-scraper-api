from flask import Flask, request, jsonify, make_response
from scraper import scrape_website
from functools import wraps
import logging

app = Flask(__name__)

# Configure basic auth credentials
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
@requires_auth  # This decorator enforces authentication
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
            return jsonify({"error": "URL is required"}), 400
        
        result = scrape_website(url, selector)
        
        if result.get("status") == "error":
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
