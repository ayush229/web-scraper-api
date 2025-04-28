from flask import Flask, request, jsonify
from scraper import handle_request
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Basic auth (set API_AUTH in Railway vars)
API_AUTH = os.getenv('API_AUTH', 'ayush1:blackbox098')

@app.before_request
def authenticate():
    auth = request.authorization
    if not auth or f"{auth.username}:{auth.password}" != API_AUTH:
        return jsonify({"error": "Unauthorized"}), 401

@app.route('/scrape', methods=['GET', 'POST'])
def api_handler():
    try:
        # Get parameters
        params = request.args if request.method == 'GET' else request.get_json()
        
        if not params.get('url'):
            return jsonify({"error": "URL parameter is required"}), 400
            
        result = handle_request(
            url=params['url'],
            mode=params.get('type', 'beautify'),
            prompt=params.get('user_prompt')
        )
        
        if 'error' in result:
            return jsonify({"status": "error", **result}), 400
            
        return jsonify({
            "status": "success",
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Internal server error"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
