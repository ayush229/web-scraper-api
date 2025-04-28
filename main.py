from flask import Flask, request, jsonify
from scraper import scrape_website
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/scrape', methods=['GET', 'POST'])
def scrape():
    """
    API endpoint for web scraping
    Supports both GET and POST methods
    """
    try:
        # Get parameters based on request method
        if request.method == 'GET':
            url = request.args.get('url')
            selector = request.args.get('selector')
        else:
            data = request.get_json()
            url = data.get('url')
            selector = data.get('selector')
        
        # Validate URL parameter
        if not url:
            logger.error("Missing URL parameter")
            return jsonify({
                "status": "error",
                "error": "URL parameter is required"
            }), 400
        
        logger.info(f"Received scrape request for URL: {url}")
        
        # Scrape the website
        result = scrape_website(url, selector)
        
        # Return appropriate response
        if result.get("status") == "error":
            logger.error(f"Scraping failed for {url}: {result.get('error')}")
            return jsonify(result), 400 if "403" in str(result.get("error")) else 500
        
        logger.info(f"Successfully scraped {url}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Unexpected error in API: {str(e)}")
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)