from bs4 import BeautifulSoup
import requests
import re
import os
from urllib.parse import urljoin
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_text(text):
    """Clean and normalize text content with enhanced processing"""
    if not text:
        return ""
    
    # Remove HTML entities, special spaces, and unwanted characters
    text = re.sub(r'&\w+;|[\xa0\u200b\u2028]', ' ', text)
    
    # Normalize whitespace and clean line breaks
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove common boilerplate text
    boilerplate = [
        "cookie policy", "privacy policy", "terms of service",
        "accept all cookies", "manage cookies", "skip to content"
    ]
    for phrase in boilerplate:
        text = text.replace(phrase, "")
    
    return text

def get_ai_response(prompt, website_content):
    """
    Get AI response from Ollama with:
    - Automatic retries
    - Timeout handling
    - Railway-specific endpoint
    """
    max_retries = 3
    retry_delay = 5  # seconds
    
    # Use Railway service DNS or fallback to localhost for local testing
    OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://ollama:11434/api/generate')
    
    for attempt in range(max_retries):
        try:
            payload = {
                "model": os.getenv('OLLAMA_MODEL', 'llama3'),
                "prompt": (
                    f"Website Content Analysis Task:\n"
                    f"CONTENT:\n{website_content[:15000]}\n\n"  # Truncate to avoid token limits
                    f"USER REQUEST: {prompt}\n\n"
                    "Provide a concise response focusing on the key information."
                ),
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 2000
                }
            }
            
            logger.info(f"Sending request to Ollama (Attempt {attempt + 1})")
            response = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if "response" not in result:
                raise ValueError("Invalid Ollama response format")
                
            return result["response"]
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return f"AI Service Unavailable: {str(e)}"
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return f"AI Processing Error: {str(e)}"

def extract_structured_content(soup, base_url):
    """Extract content with enhanced semantic organization"""
    sections = []
    current_section = {
        "heading": {"level": 0, "text": "Root Content"},
        "paragraphs": [],
        "images": [],
        "links": []
    }
    
    for element in soup.find_all():
        if element.name.startswith('h') and element.name[1:].isdigit():
            # New section found
            if current_section["paragraphs"] or current_section["images"]:
                sections.append(current_section)
                
            current_section = {
                "heading": {
                    "level": int(element.name[1]),
                    "text": clean_text(element.get_text())
                },
                "paragraphs": [],
                "images": [],
                "links": []
            }
            
        elif element.name == 'p':
            text = clean_text(element.get_text())
            if text and len(text.split()) > 5:  # Skip short paragraphs
                current_section["paragraphs"].append(text)
                
        elif element.name == 'img' and element.get('src'):
            current_section["images"].append({
                "url": urljoin(base_url, element['src']),
                "alt": clean_text(element.get('alt', ''))
            })
            
        elif element.name == 'a' and element.get('href'):
            href = element['href']
            if not href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                current_section["links"].append({
                    "url": urljoin(base_url, href),
                    "text": clean_text(element.get_text()),
                    "is_external": not href.startswith(base_url)
                })
    
    # Add the final section
    if current_section["paragraphs"] or current_section["images"]:
        sections.append(current_section)
        
    return sections

def scrape_website(url, content_type='beautify', user_prompt=None):
    """Main scraping function with enhanced error handling"""
    try:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            raise ValueError("Invalid URL format")
            
        # Configure browser-like headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        # Fetch with timeout and redirect handling
        response = requests.get(
            url,
            headers=headers,
            timeout=15,
            allow_redirects=True,
            verify=True  # Enable SSL verification
        )
        response.raise_for_status()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'noscript', 'iframe', 'svg']):
            element.decompose()
        
        # Process based on content type
        if content_type == 'raw':
            result = {
                "raw_html": str(soup),
                "images": [
                    urljoin(url, img['src'])
                    for img in soup.find_all('img')
                    if img.get('src')
                ],
                "links": [
                    urljoin(url, a['href'])
                    for a in soup.find_all('a', href=True)
                    if not a['href'].startswith(('#', 'javascript:'))
                ]
            }
            
        elif content_type == 'ai':
            if not user_prompt:
                raise ValueError("user_prompt is required for AI mode")
                
            text_content = clean_text(soup.get_text())
            if len(text_content) > 15000:  # Truncate very large content
                text_content = text_content[:15000] + "... [content truncated]"
                
            ai_response = get_ai_response(user_prompt, text_content)
            
            result = {
                "ai_response": ai_response,
                "content_preview": text_content[:500] + ("..." if len(text_content) > 500 else ""),
                "source_url": url,
                "user_prompt": user_prompt
            }
            
        else:  # beautify mode
            result = {
                "structured_content": extract_structured_content(soup, url),
                "metadata": {
                    "title": clean_text(soup.title.string if soup.title else ""),
                    "description": (
                        clean_text(soup.find('meta', attrs={'name': 'description'})['content'])
                        if soup.find('meta', attrs={'name': 'description'})
                        else ""
                    ),
                    "language": soup.find('html').get('lang', 'unknown')
                }
            }
        
        return {
            "status": "success",
            "url": url,
            "type": content_type,
            "data": result,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return {
            "status": "error",
            "url": url,
            "error": f"Network error: {str(e)}",
            "type": content_type
        }
        
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        return {
            "status": "error",
            "url": url,
            "error": f"Processing error: {str(e)}",
            "type": content_type
        }
