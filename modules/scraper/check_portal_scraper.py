import json
import requests
import logging
from urllib.parse import urlparse, quote, urljoin
import tldextract
import re
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('scraper.check_portal')

def load_domain_spider_list(config_file):
    """Load domain-spider mapping from a JSON configuration file."""
    try:
        with open(config_file, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.warning(f"Config file {config_file} not found.")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Error parsing the JSON config file: {config_file}.")
        return {}

def get_spider_from_domain(url, domain_spider_list):
    """Get the spider name and proxy type based on the domain of the URL with enhanced subdomain support."""
    parsed_url = urlparse(url)
    full_domain = parsed_url.netloc.lower()
    
    # Remove port if present
    if ':' in full_domain:
        full_domain = full_domain.split(':')[0]
    
    # Helper function to extract spider config
    def extract_spider_config(config):
        if isinstance(config, dict):
            return config.get("spider_name"), config.get("proxy_type")
        elif isinstance(config, str):
            # Backward compatibility for old format
            return config, domain_spider_list.get("_default_proxy_type", "none")
        return None, None
    
    # Check for excluded subdomains first
    excluded_subdomains = domain_spider_list.get("_excluded_subdomains", [])
    if full_domain in excluded_subdomains:
        logger.info(f"Domain {full_domain} is in excluded subdomains list.")
        return None, None
    
    # First, try exact match with full domain (including subdomain)
    if full_domain in domain_spider_list:
        spider_name, proxy_type = extract_spider_config(domain_spider_list[full_domain])
        if spider_name:
            logger.info(f"Found exact match for full domain: {full_domain} -> {spider_name} (proxy: {proxy_type})")
            return spider_name, proxy_type
    
    # Extract base domain using tldextract
    extracted = tldextract.extract(full_domain)
    base_domain = f"{extracted.domain}.{extracted.suffix}"
    
    # Try exact match with base domain
    if base_domain in domain_spider_list:
        config = domain_spider_list[base_domain]
        spider_name, proxy_type = extract_spider_config(config)
        if spider_name:
            logger.info(f"Found match for base domain: {base_domain} (from {full_domain}) -> {spider_name} (proxy: {proxy_type})")
            return spider_name, proxy_type
    else:
        logger.debug(f"Base domain '{base_domain}' not found in domain_spider_list keys for {full_domain}")
        logger.debug(f"Available keys starting with 'pikiran': {[k for k in domain_spider_list.keys() if 'pikiran' in k]}")
    
    # Check subdomain patterns if available
    subdomain_patterns = domain_spider_list.get("_subdomain_patterns", {})
    for pattern, config in subdomain_patterns.items():
        if pattern.startswith("*."):
            pattern_domain = pattern[2:]  # Remove "*."
            if full_domain.endswith(pattern_domain):
                # Make sure it's actually a subdomain, not just ending with the pattern
                if full_domain == pattern_domain or full_domain.endswith("." + pattern_domain):
                    spider_name, proxy_type = extract_spider_config(config)
                    if spider_name:
                        logger.info(f"Found subdomain pattern match: {pattern} for {full_domain} -> {spider_name} (proxy: {proxy_type})")
                        return spider_name, proxy_type
    
    logger.info(f"No spider found for domain: {full_domain} (base: {base_domain})")
    return None, None

def get_article_from_scraper(url, spider_name, proxy_type="none"):
    """Get article content from ScrapyRT server API."""
    api_url = "http://206.189.158.55:9080/crawl"
    
    payload = {
        "spider_name": spider_name,
        "start_urls": [url],
        "proxy_type": proxy_type,
        "use_playwright": False,
        "debug": False,
        "wait_completion": True,
        "send_to_kafka": False  # Get content back instead of sending to Kafka
    }
    
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        logger.info(f"Requesting article from spider {spider_name} for URL: {url} (proxy: {proxy_type})")
        response = requests.post(api_url, json=payload, headers=headers, timeout=60)

        if response.status_code == 200:
            data = response.json()
            
            # Check if the spider completed successfully
            if data.get("status") == "completed":
                scraped_content = data.get("scraped_content", [])
                
                if scraped_content and len(scraped_content) > 0:
                    logger.info(f"Successfully retrieved article content for {url}")
                    # Return the first scraped content item
                    article_data = scraped_content[0]
                    
                    # Validate that we have the minimum required fields
                    if article_data.get("title") and article_data.get("body"):
                        logger.debug(f"Article data: title='{article_data.get('title')}', body_length={len(article_data.get('body', ''))}")
                        return article_data
                    else:
                        logger.warning(f"Scraped content missing title or body for {url}")
                        return None
                else:
                    logger.warning(f"No content scraped for {url}")
                    return None
            else:
                logger.error(f"Spider failed with status: {data.get('status')} for {url}")
                error_message = data.get("message", "Unknown error")
                logger.error(f"Error details: {error_message}")
                return None
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
            return None

    except requests.exceptions.Timeout:
        logger.error(f"Timeout while fetching article from {spider_name} for {url}")
    except Exception as e:
        logger.error(f"Error fetching article: {str(e)}")

    return None

def get_tribunnews_content(url):
    """Custom scraper for Tribunnews using the HTML API."""
    try:
        # Encode the URL for the API
        encoded_url = quote(url, safe='')
        api_url = f"http://178.128.100.171:10010/get-html?uri={encoded_url}"
        
        logger.info(f"Fetching Tribunnews content via HTML API for: {url}")
        response = requests.get(api_url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"HTML API error: {response.status_code} - {response.text}")
            return None
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract article content using CSS selectors
        title_meta = soup.find('meta', {'property': 'og:title'})
        title = title_meta.get('content') if title_meta else ""
        
        # Extract authors
        authors = []
        author_elements = soup.select('div[id="editor"] a')
        for author_elem in author_elements:
            if author_elem.get_text().strip():
                authors.append(author_elem.get_text().strip())

        if authors == []:
            for credit in soup.select('div.credit'):
                if 'Editor:' in credit.text:
                    a_tag = credit.select_one('b a')
                    if a_tag:
                        authors.append(a_tag.text.strip())

        # Extract date published from JSON-LD only
        date_published = ""
        json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
        
        # Parse date from JSON-LD - prioritize datePublished
        if json_ld_scripts:
            for script in json_ld_scripts:
                try:
                    raw = script.get_text()

                    cleaned_raw = re.sub(r'[\x00-\x1F\x7F]', '', raw)
                    data = json.loads(cleaned_raw)
                    
                    if isinstance(data, dict):
                        items = [data]
                    elif isinstance(data, list):
                        items = data
                    else:
                        continue 

                    for item in items:
                        if not isinstance(item, dict):
                            continue

                        if 'datePublished' in item:
                            date_published = item['datePublished']
                            logger.debug(f"Found datePublished: {date_published}")
                            break

                        # Fallback fields
                        for field in ['dateCreated', 'publishedTime', 'dateModified']:
                            if field in item:
                                date_published = item[field]
                                logger.debug(f"Found {field} as fallback: {date_published}")
                                break

                    if date_published:
                        break  # Stop once we find any date
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"JSON-LD parsing error: {e}")
                    continue
        
        # If no date found in JSON-LD, try meta tags
        if not date_published:
            meta_selectors = [
                {'property': 'article:published_time'},
                {'name': 'publish_date'},
                {'name': 'date'},
                {'name': 'pubdate'},
                {'property': 'og:updated_time'},
                {'name': 'created_date'}
            ]
            
            for selector in meta_selectors:
                meta_tag = soup.find('meta', selector)
                if meta_tag and meta_tag.get('content'):
                    date_published = meta_tag.get('content')
                    logger.debug(f"Found date in meta tag {selector}: {date_published}")
                    break
        
        if not date_published:
            script_texts = soup.find_all('script', {'type': 'text/javascript'})
            for script in script_texts:
                if 'dataLayer' in script.text:
                    match = re.search(r"'publish_date'\s*:\s*'([^']+)'", script.text)
                    if match:
                        date_published = match.group(1)
                        logger.debug(f"Found publish_date from dataLayer: {date_published}")
                        break

        # If no date found anywhere, use current scraping time
        if not date_published:
            logger.warning(f"SCENARIO: DATE_FALLBACK - No date published found for {url}. Using current scraping time.")
            from datetime import datetime
            now = datetime.now()
            date_published = now.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            logger.info(f"SCENARIO: DATE_SUCCESS - Found published date for {url}: {date_published}")
        
        source_name = "tribunnews.com"
        
        # Extract description
        description = ""
        desc_meta = soup.find('meta', {'name': 'description'})
        if desc_meta:
            description = desc_meta.get('content', "")
        
        # Extract main content
        content_selectors = [
            'div.side-article.txt-article p',
            'div.txt-article p', 
            'div.detail-text p',
            'article p'
        ]
        
        body = ''
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    text = re.sub(r'<[^>]+>', '', str(element))
                    text = text.strip()
                    if text:
                        body += text + ' '
                break  # Use first selector that finds content
        
        # Clean up content
        body = re.sub(r'\s+', ' ', body)
        body = body.strip()
        
        # Extract images
        images = []
        
        # Try multiple meta tag selectors for main image
        image_meta_selectors = [
            {'property': 'og:image'},
            {'property': 'image'},
            {'name': 'twitter:image'},
            {'property': 'og:image:url'}
        ]
        
        for selector in image_meta_selectors:
            image_meta = soup.find('meta', selector)
            if image_meta and image_meta.get('content'):
                image_url = image_meta.get('content')
                if image_url not in images:
                    images.append(image_url)
        
        # Also extract images from article content
        article_images = soup.select('article img, .txt-article img, .side-article img')
        for img in article_images:
            if img.get('src'):
                img_url = img.get('src')
                # Convert relative URLs to absolute
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = urljoin(url, img_url)
                
                if img_url not in images:
                    images.append(img_url)
        
        language = 'id'

        content = {
            "source_name": source_name,
            "title": title,
            "description": description,
            "body": body,
            "date_published": date_published,
            "author_list": authors,
            "images": images,
            "link": url,
            "language": language
        }
        
        # Validate content
        if not content.get("title") or not content.get("body"):
            logger.warning(f"Tribunnews content missing title or body for {url}")
            return None
            
        logger.info(f"Successfully scraped Tribunnews content: {url}")
        logger.debug(f"Title: {content['title'][:100]}...")
        logger.debug(f"Body length: {len(content['body'])}")
        
        return content
        
    except Exception as e:
        logger.error(f"Error scraping Tribunnews content for {url}: {e}")
        return None

def get_pikiranrakyat_content(url):
    """Custom scraper for PikiranRakyat using the HTML API."""
    try:
        # Encode the URL for the API
        encoded_url = quote(url, safe='')
        api_url = f"http://178.128.100.171:10010/get-html-open-page?uri={encoded_url}"
        
        logger.info(f"Fetching PikiranRakyat content via HTML API for: {url}")
        response = requests.get(api_url, timeout=30)
        
        if response.status_code == 200:
            html_content = response.text
            logger.info(f"Successfully fetched HTML content for {url}")
        else:
            logger.error(f"HTML API error: {response.status_code} - {response.text}")
            return None
        
        # Parse the HTML content
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract article content using CSS selectors
        title_meta = soup.find('meta', {'property': 'og:title'})
        title = title_meta.get('content') if title_meta else ""
        
        # Extract authors
        authors = []
        author_elements = soup.find_all('meta', {'name': 'author'})
        for author_elem in author_elements:
            if author_elem.get('content'):
                authors.append(author_elem.get('content'))
        
        # Extract date published from JSON-LD only
        date_published_meta = soup.find('meta', {'name': 'pubdate'})
        date_published = date_published_meta.get('content') if date_published_meta else ""

        source_name = "pikiran-rakyat.com"
        
        # Extract description
        description = ""
        desc_meta = soup.find('meta', {'name': 'description'})
        if desc_meta:
            description = desc_meta.get('content', "")
        
        # Extract main content
        content_selectors = [
            'article.read__content.clearfix p'
        ]
        
        body = ''
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    text = re.sub(r'<[^>]+>', '', str(element))
                    text = text.strip()
                    if text:
                        body += text + ' '
                break  # Use first selector that finds content
        
        # Clean up content
        body = re.sub(r'\s+', ' ', body)
        body = body.strip()
        
        # Extract images
        images = []
        
        # Try multiple meta tag selectors for main image
        image_meta_selectors = [
            {'property': 'og:image'},
            {'property': 'image'},
            {'name': 'twitter:image'},
            {'property': 'og:image:url'}
        ]
        
        for selector in image_meta_selectors:
            image_meta = soup.find('meta', selector)
            if image_meta and image_meta.get('content'):
                image_url = image_meta.get('content')
                if image_url not in images:
                    images.append(image_url)
        
        # Also extract images from article content
        article_images = soup.select('article img, .txt-article img, .side-article img')
        for img in article_images:
            if img.get('src'):
                img_url = img.get('src')
                # Convert relative URLs to absolute
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = urljoin(url, img_url)
                
                if img_url not in images:
                    images.append(img_url)
        
        language = 'id'

        content = {
            "source_name": source_name,
            "title": title,
            "description": description,
            "body": body,
            "date_published": date_published,
            "author_list": authors,
            "images": images,
            "link": url,
            "language": language
        }
        
        # Validate content
        if not content.get("title") or not content.get("body"):
            logger.warning(f"PikiranRakyat content missing title or body for {url}")
            return None
            
        logger.info(f"Successfully scraped PikiranRakyat content: {url}")
        logger.debug(f"Title: {content['title'][:100]}...")
        logger.debug(f"Body length: {len(content['body'])}")
        
        return content
        
    except Exception as e:
        logger.error(f"Error scraping PikiranRakyat content for {url}: {e}")
        return None

'''
if __name__ == "__main__":
    # Load the domain-spider mapping from the configuration file
    config_file = "scrapers/zyte/domain_spiders.json"
    domain_spider_list = load_domain_spider_list(config_file)

    # Test with a sample URL
    url = "https://sport.detok.com/sepakbola/liga-indonesia/d-7664427/postur-kiper-timnas-indonesia-kurang-ideal"
    result = get_spider_from_domain(url, domain_spider_list)

    if result:
        logger.info(f"Spider to use: {result}")
    else:
        logger.info("No spider found.")
        logger.debug(f"Result: {result}")

'''

