from bs4 import BeautifulSoup
import requests
import re
from urllib.parse import urljoin

def clean_text(text):
    """Clean and normalize text content"""
    if not text:
        return ""
    text = re.sub(r'&\w+;|[\xa0\u200b]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_ai_response(prompt, website_content):
    """Get AI response from locally running Ollama (Llama 3/Mistral)"""
    try:
        # Ollama's default local API endpoint
        ollama_url = "http://localhost:11434/api/generate"
        
        payload = {
            "model": "llama3",  # or "mistral" for lower RAM usage
            "prompt": f"Analyze this website content:\n{website_content}\n\nUser question: {prompt}",
            "stream": False,
            "options": {"temperature": 0.7}
        }
        
        response = requests.post(ollama_url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["response"]
    
    except Exception as e:
        return f"AI processing error: {str(e)}"

def scrape_website(url, content_type='beautify', user_prompt=None):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'noscript']):
            element.decompose()

        # Process based on content type
        if content_type == 'raw':
            result = {
                "raw_html": str(soup),
                "images": [urljoin(url, img['src']) 
                          for img in soup.find_all('img') if img.get('src')],
                "links": [urljoin(url, a['href']) 
                         for a in soup.find_all('a', href=True) 
                         if not a['href'].startswith(('#', 'javascript:'))]
            }
        elif content_type == 'ai':
            if not user_prompt:
                raise ValueError("user_prompt is required for AI mode")
            
            text_content = clean_text(soup.get_text())
            ai_response = get_ai_response(user_prompt, text_content)
            
            result = {
                "ai_response": ai_response,
                "source_url": url,
                "user_prompt": user_prompt
            }
        else:  # beautify mode
            result = {
                "content": clean_text(soup.get_text()),
                "metadata": {
                    "title": clean_text(soup.title.string if soup.title else ""),
                    "description": clean_text(soup.find('meta', attrs={'name': 'description'})['content']) 
                              if soup.find('meta', attrs={'name': 'description'}) else ""
                }
            }

        return {
            "status": "success",
            "url": url,
            "type": content_type,
            "data": result
        }

    except Exception as e:
        return {
            "status": "error",
            "url": url,
            "error": str(e)
        }
