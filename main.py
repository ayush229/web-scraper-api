from flask import Flask, request, jsonify
from scraper import scrape_website
import logging

app = Flask(__name__)

@app.route('/scrape', methods=['GET', 'POST'])
def scrape():
    try:
        # Handle both GET and POST requests
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
