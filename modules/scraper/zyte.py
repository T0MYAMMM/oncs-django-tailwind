import logging
import time
from urllib.parse import urlparse, urlunparse, unquote
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
import psycopg2
import psycopg2.extras
import pytz

from crawlers.utils.zyteAPI import request_article
from database.crud import (
    extract_source_name, 
    onm_urls_update_url_status, 
    onm_urls_is_url_added,
    onm_contents_is_url_added,
    onm_urls_update_metadata,
    onm_redirects_check_in_db,
    onm_redirects_store,
    onm_urls_get_status,
    onm_urls_add_url
)
from kafka_clients.scraper_producer import send_content
from scrapers.zyte.base_scraper import BaseScraper
from scrapers.zyte.fetch_dateformat import get_general_published_date, convert_voi_date
from scrapers.utils.date_utils import (
    is_valid_date,
    get_current_format,
    normalize_date,
    parse_date,
    INGESTION_FORMAT
)
from scrapers.zyte.check_date_published import check_url_date_published
from scrapers.zyte.check_portal_scraper import get_spider_from_domain, get_article_from_scraper, get_tribunnews_content, get_pikiranrakyat_content
from variables import URLS_TABLE, SENTRY_DSN

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger('ZyteScraper')

# Initialize Sentry SDK
sentry_logging = LoggingIntegration(
    level=logging.INFO,        # Capture info and above as breadcrumbs
    event_level=logging.ERROR  # Send errors as events
)

sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[sentry_logging],
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production,
    traces_sample_rate=0.2,
    
    # Enable performance monitoring
    enable_tracing=True,
    
    # By default the SDK will try to use the SENTRY_RELEASE
    # environment variable, or infer a git commit
    # release=os.environ.get("MY_APP_RELEASE", "unknown"),
    
    # Set a uniform sample rate for all users
    # If you want higher sampling in production, you can do:
    # traces_sample_rate=0.5 if os.environ.get("ENV", "dev") == "production" else 0.05,
)

class DuplicateURLError(Exception): pass
class ExcludedDomainError(Exception): pass
class ExpectedCleanFailure(Exception): pass
class ZyteAPIError(Exception): pass

class ZyteScraper(BaseScraper):
    name = 'zyte'
    # Add excluded domains list for easier maintenance
    EXCLUDED_DOMAINS = [
        "borneonews.co.id", "realitanews.co.id", "tradewindsnews.com", "dhlottery.co.kr", "shein.com", 
        "support.google.com", "support.microsoft.com", "answer.microsoft.com", "revistabiociencias.uan.edu.mx",
        "life.tut.edu.tw", "yandex.com", "newneraca.neraca.co.id", "bestbuy.com", "google.com", "microsoft.com", "youtube.com",
        "twitter.com", "instagram.com", "facebook.com", "tiktok.com", "linkedin.com", "pinterest.com", "reddit.com",
        "dpg.danawa.com", "jglobal.jst.go.jp", "opencarry.org", " dawoolaw.com", "tcu.ac.jp", "hcc.edu.tw", "acfun.cn",
        "gamer.com", 
        ]

    def process_url(self, url: str, cursor=None) -> None:
        """
        Processes a single URL to scrape article content and metadata.
        
        Args:
            url: The URL to process
            cursor: Database cursor for updating status (if None, will create own connection)
        """
        # Initialize variables that are used across try/except blocks
        original_url = url
        redirect_detected = False
        cleaned_url = None
        
        # Get own database connection if no cursor provided (thread-safe approach)
        own_connection = cursor is None
        conn = None
        
        if own_connection:
            from database.connect import get_connection, close_connection
            conn = get_connection()
            if not conn:
                logger.error(f"Failed to get database connection for URL: {url}")
                return
            conn.autocommit = True
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Create a Sentry transaction for the entire URL processing
            with sentry_sdk.start_transaction(op="process_url", name=f"Process URL: {url}") as transaction:
                # Set initial URL context
                sentry_sdk.set_context("url_processing", {
                    "original_url": url,
                    "processing_start": time.time()
                })
                
                try:
                    start_time = time.time()
                    logger.info(f"Processing URL: {url}")
                    
                    # Check current URL status and update to running if appropriate
                    if cursor:
                        try:
                            current_status = onm_urls_get_status(url, cursor)
                            if current_status == 'pending':
                                logger.info(f"Marking URL as running: {url}")
                                onm_urls_update_url_status(url, 'running', cursor=cursor, increment_retry=False)
                            else:
                                logger.info(f"URL current status: {current_status}")
                                
                            # Update Sentry context with status info
                            sentry_sdk.set_context("url_status", {      
                                "initial_status": current_status,
                                "url": url
                            })
                        except Exception as e:
                            logger.error(f"Error checking or updating URL status: {e}")
                            sentry_sdk.capture_exception(e)
                            # Continue processing
        
                    # Create a Sentry span for URL cleaning
                    with sentry_sdk.start_span(op="url_cleaning", description="Clean URL") as span:
                        # Clean URL by removing fragments and excluded url keywords
                        try:
                            cleaned_url = self._clean_url(url)
                            span.set_data("cleaned_url", cleaned_url)
                            
                            if not cleaned_url: 
                                logger.warning(f"SCENARIO: INVALID URL - URL failed cleaning: {url}")
                                sentry_sdk.set_tag("scenario", "invalid_url")
                                # Ensure we update the correct URL status to error
                                if cursor:
                                    try:
                                        onm_urls_update_url_status(original_url, 'error', error_message="URL failed validation during cleaning", cursor=cursor, increment_retry=False)
                                        logger.info(f"Marked URL as error due to cleaning failure: {original_url}")
                                    except Exception as status_e:
                                        logger.warning(f"Failed to update status to error after cleaning failure: {status_e}")
                                raise ValueError("Invalid URL after cleaning.")
                        except Exception as e:
                            span.set_data("error", str(e))
                            sentry_sdk.capture_exception(e)
                            # Ensure we mark the URL as error if cleaning fails
                            if cursor and "Invalid URL after cleaning" in str(e):
                                try:
                                    onm_urls_update_url_status(original_url, 'error', error_message=str(e), cursor=cursor, increment_retry=False)
                                    logger.info(f"Marked URL as error due to cleaning exception: {original_url}")
                                except Exception as status_e:
                                    logger.warning(f"Failed to update status to error after cleaning exception: {status_e}")
                            raise

                    # Create a Sentry span for redirect checking
                    with sentry_sdk.start_span(op="redirect_checking", description="Check for redirects") as span:
                        # Check for redirects - this handles typo links and canonicalization
                        try:
                            canonical_url = self._check_and_store_redirect(cleaned_url, cursor)
                            span.set_data("canonical_url", canonical_url)
                            
                            if canonical_url != cleaned_url:
                                logger.info(f"SCENARIO: REDIRECTED URL - {cleaned_url} redirects to {canonical_url}")
                                sentry_sdk.set_tag("scenario", "redirected_url")
                                cleaned_url = canonical_url
                                # clean the www. from the url
                                if 'www.' in cleaned_url:
                                    logger.info(f"SCENARIO: Removing www. from {cleaned_url}")
                                    cleaned_url = cleaned_url.replace('www.', '')

                                if ':443' in cleaned_url:
                                    logger.info(f"SCENARIO: Removing :443 from {cleaned_url}")
                                    cleaned_url = cleaned_url.replace(':443', '')

                                if 'http://' in cleaned_url:
                                    logger.info(f"SCENARIO: Change http:// to https:// of {cleaned_url}")
                                    cleaned_url = cleaned_url.replace('http://', 'https://')

                                if '?amp' in cleaned_url:
                                    logger.info(f"SCENARIO: Removing ?amp of {cleaned_url}")
                                    cleaned_url = cleaned_url.replace('?amp', '')
                                
                                redirect_detected = True
                                
                                # Check if redirected URL exists in onm_urls
                                if cursor and not onm_urls_is_url_added(canonical_url, cursor):
                                    logger.info(f"SCENARIO: NEW REDIRECT TARGET - Adding redirected URL to database: {canonical_url}")
                                    # Add the redirected URL to onm_urls with pending status
                                    redirect_source_name = extract_source_name(canonical_url)
                                    redirect_data = {
                                        'url': canonical_url,
                                        'source_name': redirect_source_name,
                                        'status': 'running'  # treat as running until it's processed
                                    }
                                    onm_urls_add_url(redirect_data, cursor)

                        except Exception as e:
                            span.set_data("error", str(e))
                            sentry_sdk.capture_exception(e)
                            # Use cleaned_url without redirect resolution
                            
                    # Apply domain-specific formatting (keeping this as mandatory per request)
                    # NOTE: This may create duplicates for tribunnews.com URLs as ?page=all gets added
                    formatted_url = self._domain_specific_formatting(cleaned_url)
                    
                    # Check if domain formatting created a different URL
                    if formatted_url != cleaned_url:
                        logger.info(f"Domain formatting applied: {cleaned_url} -> {formatted_url}")
                        # Use the formatted URL for processing
                        url = formatted_url
                        # If the formatted URL is different, we should check if it already exists
                        if cursor and onm_contents_is_url_added(formatted_url, cursor):
                            logger.info(f"SCENARIO: FORMATTED URL EXISTS - Formatted URL already in contents: {formatted_url}")
                            # Mark the formatted URL as success and original as duplicate
                            try:
                                onm_urls_update_url_status(formatted_url, 'success', cursor=cursor, increment_retry=False)
                            except Exception as e:
                                logger.warning(f"Failed to update formatted URL status: {e}")
                            
                            try:
                                onm_urls_update_url_status(original_url, "duplicate", error_message=f"URL resolves to formatted URL: {formatted_url}", cursor=cursor, increment_retry=False)
                            except Exception as e:
                                logger.warning(f"Failed to update original URL status: {e}")
                            return
                    else:
                        # Use the cleaned URL for processing
                        url = cleaned_url

                    # Update URL context after cleaning and redirect
                    sentry_sdk.set_context("url_processing", {
                        "original_url": original_url,
                        "final_url": url,
                        "processing_time_so_far": time.time() - start_time,
                        "redirect_detected": redirect_detected
                    })

                    # Check for excluded domains
                    domain = urlparse(url).netloc
                    if any(excluded in domain for excluded in self.EXCLUDED_DOMAINS):
                        logger.warning(f"SCENARIO: EXCLUDED DOMAIN - Domain is excluded: {domain}")
                        raise ValueError(f"Domain '{domain}' is excluded.")

                    # Final check for existing url in onm_contents
                    if cursor:
                        if url != original_url:
                            if onm_contents_is_url_added(url, cursor):
                                logger.info(f"SCENARIO: EXISTING URL IN CONTENTS - URL already exist in onm_contents: {url}")
                                try:
                                    onm_urls_update_url_status(url, 'success', cursor=cursor, increment_retry=False)
                                except Exception as e:
                                    logger.warning(f"Failed to update URL status to success: {e}")
                                try:
                                    onm_urls_update_url_status(original_url, "duplicate", error_message=f"URL redirects to: {url}", cursor=cursor, increment_retry=False)
                                except Exception as e:
                                    logger.warning(f"Failed to update original URL status to duplicate: {e}")
                                raise ValueError(f"URL '{url}' already exists in the contents database.")
                        else:
                            if onm_contents_is_url_added(url, cursor):
                                logger.info(f"SCENARIO: EXISTING URL IN CONTENTS - URL already exist in onm_contents: {url}")
                                try:
                                    onm_urls_update_url_status(url, 'success', error_message="URL already inserted", cursor=cursor, increment_retry=False)
                                except Exception as e:
                                    logger.warning(f"Failed to update URL status to success: {e}")
                                raise ValueError(f"URL '{url}' already exists in the contents database.")

                    # Initialize article_data variable
                    article_data = None
                    
                    # Try to get spider for the domain first
                    spider_result = get_spider_from_domain(url, self.domain_spider_list)
                    spider_name = spider_result[0] if spider_result and spider_result[0] else None
                    proxy_type = spider_result[1] if spider_result and spider_result[1] else "none"
                    
                    if spider_name:
                        logger.info(f"Using custom scraper: {spider_name} with proxy: {proxy_type}")
                        try:
                            # Check if it's the custom Tribunnews scraper
                            if spider_name == "CUSTOM_TRIBUNNEWS":
                                logger.info("Using custom Tribunnews HTML API scraper")
                                article_data = get_tribunnews_content(url)
                            elif spider_name == "CUSTOM_PIKIRANRAKYAT":
                                logger.info("Using custom PikiranRakyat HTML API scraper")
                                article_data = get_pikiranrakyat_content(url)
                            else:
                                # Use regular ScrapyRT API
                                article_data = get_article_from_scraper(url, spider_name, proxy_type)
                            
                            if article_data and isinstance(article_data, dict):
                                logger.info(f"SCENARIO: CUSTOM SCRAPER SUCCESS - Spider {spider_name} successfully processed {url}")
                                logger.debug(f"Extracted Article Data from spider: {article_data}")
                                
                                # Process the article data normally through the standard flow
                                # The article_data is now in the same format as Zyte data
                                
                            else:
                                logger.warning(f"Spider {spider_name} failed for {url}, falling back to Zyte")
                                article_data = None
                        except Exception as e:
                            logger.warning(f"Spider {spider_name} failed for {url}: {e}")
                            article_data = None
                    
                    # If no spider data available, use Zyte API
                    if not article_data:
                        logger.info("Using ZyteArticleScraper" + (" as fallback" if spider_name else " (no custom spider found)"))
                        
                        # Fetch article content from Zyte
                        article = request_article(url)
                        if not article:
                            raise ValueError("Failed to fetch article content.")
                        # Check if response contains error information
                        if isinstance(article, dict) and article.get("error"):
                            error_status = article.get("status_code", "unknown")
                            error_message = article.get("error_message", "No details available")
                            raise ValueError(f"Zyte API error: Status {error_status}, Message: {error_message}")
                            
                        article_data = self._extract_zyte_article_data(article, url)
                        logger.debug(f"Extracted Article Data from Zyte: {article_data}")

                    # Validate article data
                    if not article_data:
                        raise ValueError("No article data could be extracted from any source.")

                    # Send article data to Kafka if valid
                    if cursor:
                        # Pass original_url and redirect_detected flag to handle status updates properly
                        self._process_and_send_data(article_data, url, original_url, redirect_detected, cursor)
                    else:
                        logger.info(f"Article Data: {article_data}")

                    scrape_time = time.time() - start_time
                    logger.info(f"Scrape completed in {scrape_time:.2f} seconds.")

                except ValueError as e:
                    error_message = str(e)

                    if "URL already inserted" in error_message:
                        logger.info(f"SCENARIO: DUPLICATE - URL '{url}' already exists in the database.")
                    
                        # Set error tag for classification
                        sentry_sdk.set_tag("error_type", "duplicate_url")
                        if cursor:
                            try:
                                onm_urls_update_url_status(original_url, 'duplicate', error_message=error_message, cursor=cursor, increment_retry=False)
                            except Exception as inner_e:
                                logger.warning(f"Failed to update status to duplicate: {inner_e}")

                    elif "already exists in the contents database" in error_message:
                        logger.info(f"SCENARIO: IGNORING EXISTING URL - URL '{url}' already exists in the database.")
                
                    else:
                        logger.error(f"SCENARIO: ERROR - Error processing URL '{url}': {error_message}")
                        # Capture the error with context for non-duplicate errors
                        #sentry_sdk.set_tag("error_type", "processing_error")
                        #sentry_sdk.capture_exception(e)
                        if cursor:
                            try:
                                onm_urls_update_url_status(original_url, 'error', error_message=error_message, cursor=cursor, increment_retry=False)
                            except Exception as inner_e:
                                logger.warning(f"Failed to update status to error: {inner_e}")
                            
                            # Also mark the cleaned URL as error if it's different from the original
                            if original_url != url and redirect_detected:
                                logger.info(f"Also marking redirected URL as error: {url}")
                                try:
                                    onm_urls_update_url_status(url, 'error', error_message=error_message, cursor=cursor, increment_retry=False)
                                except Exception as inner_e:
                                    logger.error(f"Failed to update status for redirected URL: {inner_e}")
                                    #sentry_sdk.capture_exception(inner_e)


                except Exception as e:
                    error_message = str(e)
                    logger.error(f"SCENARIO: EXCEPTION - Error processing URL '{url}': {error_message}")
                    
                    # Capture the exception with full context for unexpected errors
                    sentry_sdk.set_tag("error_type", "unexpected_error")
                    sentry_sdk.set_tag("url", url)
                    sentry_sdk.set_tag("original_url", original_url)
                    #sentry_sdk.capture_exception(e)
                    
                    if cursor:
                        # Use the original URL for updating status to ensure consistency
                        try:
                            onm_urls_update_url_status(original_url, 'error', error_message=error_message, cursor=cursor, increment_retry=False)
                        except Exception as inner_e:
                            logger.warning(f"Failed to update status to error: {inner_e}")
                        
                        # Also mark the cleaned URL as error if it's different from the original
                        if redirect_detected and cleaned_url and original_url != cleaned_url:
                            logger.info(f"Also marking redirected URL as error: {cleaned_url}")
                            try:
                                onm_urls_update_url_status(cleaned_url, 'error', error_message=error_message, cursor=cursor, increment_retry=False)
                            except Exception as inner_e:
                                logger.error(f"Failed to update status for redirected URL: {inner_e}")
                                #sentry_sdk.capture_exception(inner_e)
                finally:
                    # If the URL was marked as running, make sure it's not left in running state on error
                    if cursor and original_url:
                        try:
                            current_status = onm_urls_get_status(original_url, cursor)
                            if current_status in ['running', 'processing']:
                                # The database function will automatically handle max retry logic
                                # If retry count reaches 3, it will move to error status automatically
                                logger.info(f"SCENARIO: CLEANUP - Changing status from {current_status} back to pending for {original_url}")
                                onm_urls_update_url_status(original_url, 'pending', error_message="Processing interrupted", cursor=cursor, increment_retry=True)
                            elif current_status is None:
                                # URL doesn't exist in database - this is expected for cleaned URLs
                                logger.debug(f"SCENARIO: CLEANUP - Original URL not found in database (likely cleaned): {original_url}")
                            else:
                                logger.debug(f"SCENARIO: CLEANUP - URL already in final state ({current_status}): {original_url}")
                        except Exception as e:
                            logger.warning(f"Error in cleanup for {original_url}: {e}")
                            # Don't log this as an error since it's often expected (cleaned URLs)
                    
                    # Record final processing time in Sentry context
                    processing_time = time.time() - start_time
                    sentry_sdk.set_context("url_processing", {
                        "original_url": original_url,
                        "final_url": url,
                        "total_processing_time": processing_time
                    })
                    transaction.set_data("processing_time", processing_time)

        except Exception as e:
            error_message = str(e)
            logger.error(f"SCENARIO: OUTER EXCEPTION - Error processing URL '{original_url}': {error_message}")
            
            # Capture the exception with full context for unexpected errors
            sentry_sdk.set_tag("error_type", "unexpected_error")
            sentry_sdk.set_tag("url", url if 'url' in locals() else original_url)
            sentry_sdk.set_tag("original_url", original_url)
            #sentry_sdk.capture_exception(e)
            
            if cursor:
                # Use the original URL for updating status to ensure consistency
                try:
                    onm_urls_update_url_status(original_url, 'error', error_message=error_message, cursor=cursor, increment_retry=False)
                except Exception as inner_e:
                    logger.warning(f"Failed to update status to error in outer exception: {inner_e}")
                
                # Also mark the cleaned URL as error if it's different from the original
                if redirect_detected and cleaned_url and original_url != cleaned_url:
                    logger.info(f"Also marking redirected URL as error: {cleaned_url}")
                    try:
                        onm_urls_update_url_status(cleaned_url, 'error', error_message=error_message, cursor=cursor, increment_retry=False)
                    except Exception as inner_e:
                        logger.error(f"Failed to update status for redirected URL: {inner_e}")
                        #sentry_sdk.capture_exception(inner_e)
        finally:
            # Close the database connection if it was opened
            if own_connection and conn:
                try:
                    close_connection(conn)
                except Exception as e:
                    logger.error(f"Error closing database connection: {e}")
                    #sentry_sdk.capture_exception(e)

    def _clean_url(self, url: str) -> Optional[str]:
        """
        Cleaning URL by:
        1. URL decoding (fixing %3F to ? etc.)
        2. Removing fragments
        3. Filtering out URLs with excluded keywords
        4. Converting '?page={n}' to '?page=all' and dropping other query params
        5. Removing 'www.' from domains
        6. Filtering out image files and invalid content types
        7. Filtering out malformed URLs with duplicate domains or structural issues
        8. Filtering out unwanted URL patterns
        9. Filtering out non-article content patterns
        10. Handle www removal
        11. Filtering out query parameters
        12. Rebuild URL without fragments - always remove fragments
        13. Final validation of cleaned URL
        14. Check for excluded keywords
        
        Args:
            url: The URL to clean
                
        Returns:
            The cleaned URL or None if URL should be excluded
        """
        if not url or not isinstance(url, str):
            return None
        
        # 1. URL decode first (fixes %3F -> ? encoding issues)
        try:
            decoded_url = unquote(url)
            if decoded_url != url:
                logger.debug(f"URL decoded: {url} -> {decoded_url}")
                url = decoded_url
        except Exception as e:
            logger.warning(f"Failed to decode URL {url}: {e}")
            # Continue with original URL
            
        # 2. Check for malformed URL patterns early
        malformed_patterns = [
            r'\/\\/',  # Escaped forward slashes
            r'\\/',    # Mixed slash patterns
            r'/\/\/',  # Multiple forward slashes with escapes
            r'\.co\.id.*\.co\.id',  # Duplicate .co.id domains
            r'\.com.*\.com',        # Duplicate .com domains
            r'\.net.*\.net',        # Duplicate .net domains
            r'\.org.*\.org',        # Duplicate .org domains
        ]
        
        import re
        for pattern in malformed_patterns:
            if re.search(pattern, url):
                logger.warning(f"URL contains malformed pattern '{pattern}': {url}")
                return None
        
        # 3. Check for duplicate domain in path
        parsed_url = urlparse(url)
        if parsed_url.netloc:
            domain_in_path_patterns = [
                parsed_url.netloc.replace('www.', ''),  # Remove www for comparison
                parsed_url.netloc,  # Full domain
            ]
            
            for domain_pattern in domain_in_path_patterns:
                if domain_pattern and domain_pattern in parsed_url.path:
                    logger.warning(f"URL contains duplicate domain '{domain_pattern}' in path: {url}")
                    return None
        
        # 4. Check for URL fragments and reject URLs with common non-article fragments
        if parsed_url.fragment:
            # Common fragments that indicate non-article content
            non_article_fragments = [
                'comments', 'comment', 'respond', 'reply', 'replies',
                'main', 'primary', 'sidebar', 'footer', 'header',
                'nav', 'navigation', 'menu', 'search', 'searchbar',
                'popular', 'related', 'trending', 'latest',
                'social', 'share', 'sharing', 'follow',
                'subscribe', 'newsletter', 'masthead', 'banner',
                'advertisement', 'ads', 'popup', 'modal',
                'tab1', 'tab2', 'tab3', 'tab4', 'tab5'
            ]
            
            fragment_lower = parsed_url.fragment.lower()
            if any(fragment in fragment_lower for fragment in non_article_fragments):
                logger.warning(f"URL contains non-article fragment '{parsed_url.fragment}': {url}")
                return None
            
            # Also reject fragments that look like UI elements (contain underscore patterns)
            if '_' in fragment_lower or fragment_lower.startswith(('btn', 'button', 'link')):
                logger.warning(f"URL contains UI-related fragment '{parsed_url.fragment}': {url}")
                return None
            
            # Log fragment removal for debugging
            logger.debug(f"Removing fragment '{parsed_url.fragment}' from URL: {url}")
        
        # 5. Validate URL has required components
        if not parsed_url.scheme or not parsed_url.netloc:
            logger.warning(f"URL missing scheme or netloc: {url}")
            return None
        
        # 6. Check for excessive URL length or suspicious patterns
        if len(url) > 2000:  # Reduced from 1000 for better detection
            logger.warning(f"URL too long: {url}")
            return None
        
        # 7. Check for URLs with suspicious repeated segments
        path_segments = [seg for seg in parsed_url.path.split('/') if seg]
        if len(path_segments) > 15:  # Too many path segments
            logger.warning(f"URL has too many path segments: {url}")
            return None
        
        # Check for repeated identical segments
        if len(path_segments) != len(set(path_segments)) and len(path_segments) > 3:
            repeated_segments = [seg for seg in set(path_segments) if path_segments.count(seg) > 1]
            if repeated_segments:
                logger.warning(f"URL has repeated path segments {repeated_segments}: {url}")
                return None
        
        # 8. Filter out image files and unwanted content types
        path = parsed_url.path.lower()
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico']
        unwanted_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar']
        
        if any(path.endswith(ext) for ext in image_extensions + unwanted_extensions):
            logger.warning(f"URL points to unwanted file type: {url}")
            return None
            
        # 9. Filter out unwanted URL patterns
        unwanted_patterns = [
            '/wp-content/uploads/',  # WordPress uploads (usually images)
            '/uploads/',
            '/images/',
            '/image/',   # Single image path (common in URLs like /image/2025/...)
            '/img/',
            '/assets/',
            '/static/',
            '/editor/',  # Editor pages
            '/tag/',     # Tag pages
            '/topic/',   # Topic pages (often not article content)
            '/category/' # Category pages
        ]
        
        if any(pattern in path for pattern in unwanted_patterns):
            logger.warning(f"URL contains unwanted pattern: {url}")
            return None
        
        # 10. Filter out non-article content patterns
        # Check for URLs that will resolve to just domain homepage after cleaning
        if parsed_url.query and not parsed_url.path or parsed_url.path == '/':
            # URLs like "domain.com/?p=123" or "domain.com/?q=node/123" with no meaningful path
            query_only_patterns = ['?p=', '?q=', '?id=', '?post=', '?page_id=']
            if any(pattern in url for pattern in query_only_patterns):
                logger.warning(f"URL is query-only with no article path: {url}")
                return None
        
        # Check for non-article content indicators in path
        non_article_path_patterns = [
            '/tag:',           # RSS/feed tag URLs
            '/views/World/tag:',  # Reuters-style tag URLs
            '/penulis/eyJ',    # Base64 encoded author/user tokens
            '/Index/flow',     # Generic flow/listing pages
            '/flowNewsDetail/id/',  # ID-based news detail pages (often dynamic)
        ]
        
        if any(pattern in parsed_url.path for pattern in non_article_path_patterns):
            logger.warning(f"URL contains non-article path pattern: {url}")
            return None
        
        # Check for very long encoded segments that look like tokens
        path_segments = [seg for seg in parsed_url.path.split('/') if seg]
        for segment in path_segments:
            # Check for very long base64-like segments (likely tokens/IDs)
            if len(segment) > 100 and any(char in segment for char in ['eyJ', 'ey0', 'ey1', 'ey2', 'ey3', 'ey4', 'ey5', 'ey6', 'ey7', 'ey8', 'ey9']):
                logger.warning(f"URL contains very long encoded segment (likely token): {url}")
                return None
            
            # Check for segments that are just long strings of alphanumeric characters (likely IDs)
            if len(segment) > 50 and segment.isalnum():
                logger.warning(f"URL contains very long alphanumeric segment (likely ID): {url}")
                return None
        
        # 11. Handle www removal
        netloc = parsed_url.netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]  # Remove 'www.'
        
        # 12. Handle query parameters - keep only 'page' param and drop all others
        new_query = ""
        if parsed_url.query:
            page_param = None
            dropped_params = []
            
            for pair in parsed_url.query.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    if key == 'page':
                        # Convert page=N to page=all if it's a digit
                        if value.isdigit():
                            page_param = 'page=all'
                            logger.debug(f"Converting page parameter: page={value} -> page=all")
                        else:
                            page_param = f'page={value}'
                    else:
                        dropped_params.append(f"{key}={value}")
                else:
                    if pair == 'page':
                        page_param = 'page'
                    else:
                        dropped_params.append(pair)
            
            # Only keep the page parameter if it exists
            if page_param:
                new_query = page_param
            
            # Log dropped parameters for debugging
            if dropped_params:
                logger.debug(f"Dropping query parameters: {', '.join(dropped_params)}")
        
        # 13. Rebuild URL without fragments - always remove fragments
        cleaned_url = urlunparse(
            (parsed_url.scheme, netloc, parsed_url.path, 
            parsed_url.params, new_query, '')
        )
        
        # 14. Final validation of cleaned URL
        try:
            final_parsed = urlparse(cleaned_url)
            if not final_parsed.scheme or not final_parsed.netloc:
                logger.warning(f"Cleaned URL failed final validation: {cleaned_url}")
                return None
        except Exception as e:
            logger.warning(f"Error in final URL validation: {e}")
            return None
        
        # Log the cleaning process for debugging
        if url != cleaned_url:
            logger.debug(f"URL cleaned: {url} -> {cleaned_url}")
        
        # 15. Check for excluded keywords
        excluded_keywords = ["login", "register", "signup", "signin", 
                            "sign-up", "sign-in", ".amp", "/amp"]

        if any(keyword in cleaned_url for keyword in excluded_keywords):
            logger.warning(f"URL contains excluded keywords: {cleaned_url}")
            return None
            
        logger.debug(f"Cleaned URL: {cleaned_url}")
        return cleaned_url

    def _domain_specific_formatting(self, url: str) -> str:
        """
        Formatting URL by:
        1. Filtering out or adding specific pattern checking for certain domains

        Args:
            url: The URL to format
                
        Returns:
            The formatted URL or original URL if no matching domain formatting rule is applied
        """
        domain_specific_formatting = {
            "tribunnews.com": {
                "must_end": "?page=all"
            },
            "jawapos.com": {
                "must_end": "?page=all"
            },
            "kompasiana.com": {
                "must_end": "?page=all"
            },
            "kompas.com": {
                "must_end": "?page=all"
            },
            "viva.co.id": {
                "must_end": "?page=all"
            },
        }

        parsed = urlparse(url)
        domain = parsed.netloc

        for target_domain, rules in domain_specific_formatting.items():
            if target_domain in domain:
                must_end = rules.get("must_end")
                if must_end and not url.endswith(must_end):
                    return url + must_end
                return url  # Already ends correctly

        return url  # No matching domain

    def _extract_author_names(self, authors: List[Any]) -> List[str]:
        """
        Extracts author names from various author formats.
        
        Args:
            authors: List of author information in various formats
            
        Returns:
            List of author name strings
        """
        author_names = []
        
        if not authors:
            return author_names
            
        for author in authors:
            if not author:
                continue
                
            if isinstance(author, str):
                author_names.append(author)
            elif isinstance(author, dict) and "name" in author:
                author_names.append(author["name"])
            elif hasattr(author, "get") and author.get("name"):
                author_names.append(author.get("name"))
                
        return author_names

    def _extract_image_urls(self, images: List[Any]) -> List[str]:
        """
        Extracts image URLs from image data.
        
        Args:
            images: List of image information
            
        Returns:
            List of image URLs
        """
        image_urls = []
        
        if not images:
            return image_urls
            
        for image in images:
            if not image:
                continue
                
            if isinstance(image, str):
                image_urls.append(image)
            elif isinstance(image, dict) and "url" in image:
                image_urls.append(image["url"])
            elif hasattr(image, "get") and image.get("url"):
                image_urls.append(image.get("url"))
                
        return image_urls

    def _extract_zyte_article_data(self, article: dict, url: str) -> Dict[str, Any]:
        """
        Extracts necessary fields from the article response.
        
        Args:
            article: The article data from Zyte
            url: The URL of the article
            
        Returns:
            Dictionary with extracted article data
        """
        title = article.get("headline", "")
        body = article.get("articleBody", "")
        authors = article.get("authors", [])
        images = article.get("images", [])
        language = article.get("inLanguage", "")
        source_name = extract_source_name(url)

        # Attempt to get the published date
        date_published_raw = check_url_date_published(url)
        if not date_published_raw:
            logger.warning("Published date not found in external service, using article data.")
            date_published_raw = article.get("datePublishedRaw", "")

        # Extract author names using dedicated method
        author_names = self._extract_author_names(authors)
        
        # Fall back to source name if no authors found
        if not author_names:
            author_names = [source_name]
        
        # Extract image URLs using dedicated method
        image_urls = self._extract_image_urls(images)

        # Intercept zyte extractor to handle dateformat conditioning
        from datetime import datetime, timedelta, timezone

        if source_name == 'mistar.id':
            _, tanggal_waktu = date_published_raw.split(", ", 1)
            dt = datetime.strptime(tanggal_waktu, "%d %B %Y %H.%M")
            datePublishedStr = dt.replace(tzinfo=timezone(timedelta(hours=7)))
            date_published_raw = datePublishedStr.isoformat()

        # Build article data dictionary
        article_data = {
            "source_name": source_name,
            "title": title,
            "description": "",
            "body": body,
            "date_published": date_published_raw,
            "author_list": author_names,  # Now consistently a list of strings
            "images": image_urls,
            "link": url,
            "language": language,
        }
    
        return article_data

    def _process_and_send_data(self, article_data: Dict[str, Any], url: str, original_url: str, redirect_detected: bool, cursor) -> None:
        """
        Processes the article data and sends it to Kafka if valid.
        
        Args:
            article_data: The article data to process
            url: The URL of the article (after redirects)
            original_url: The original URL before redirects
            redirect_detected: Flag indicating if redirection occurred
            cursor: Database cursor for updating status
        """
        processed = article_data.copy()
        published_date = processed.get('date_published')
        
        # Handle empty title or body
        if not processed.get("title") or not processed.get("body"):
            logger.warning(f"SCENARIO: INVALID CONTENT - Missing title or body for {url}")
            onm_urls_update_url_status(url, "error", error_message="Missing title or body", cursor=cursor, increment_retry=False)
            if redirect_detected and original_url != url:
                onm_urls_update_url_status(original_url, "error", error_message=f"Missing title or body (redirects to: {url})", cursor=cursor, increment_retry=False)
            return
        
        # Handle invalid date format
        if not is_valid_date(published_date):
            # Try preprocessing the date to handle special formats like "2025-06-19T11-04-20Z"
            preprocessed_date = self._preprocess_date_format(published_date)
            if preprocessed_date != published_date and is_valid_date(preprocessed_date):
                logger.info(f"SCENARIO: DATE PREPROCESSING - Fixed date format: {published_date} -> {preprocessed_date} for {url}")
                processed["date_published"] = preprocessed_date
                published_date = preprocessed_date
            else:
                error_msg = f"Invalid date format: '{published_date}'"
                logger.warning(f"SCENARIO: DATE ERROR - {error_msg} in article: {url}")
                send_content(article_data, self.producer, topic="onm-contents-dateformat-error")
                onm_urls_update_url_status(url, "error", error_message=error_msg, cursor=cursor, increment_retry=False)
                if redirect_detected and original_url != url:
                    onm_urls_update_url_status(original_url, "error", error_message=f"{error_msg} (redirects to: {url})", cursor=cursor, increment_retry=False)
                return
        
        # Check if date is incomplete (date-only format) and enrich with current time
        if published_date and self._is_date_only_format(published_date):
            enriched_date = self._enrich_date_with_current_time(published_date)
            if enriched_date:
                logger.info(f"SCENARIO: DATE ENRICHMENT - Enriching date-only format: {published_date} -> {enriched_date} for {url}")
                processed["date_published"] = enriched_date
                published_date = enriched_date
                article_data = processed
        
        # Normalize date if needed
        current_format = get_current_format(published_date, use_parsing=False)
        if current_format not in INGESTION_FORMAT:
            normalized_date = normalize_date(published_date, url)
            processed["date_published"] = normalized_date
            logger.info(f"SCENARIO: DATE NORMALIZATION - Normalizing date: {published_date} to {normalized_date} for {url}")
            article_data = processed
        
        # Apply conditional date formatting based on portal
        article_data = self.conditionals_dateformatting_by_portals(article_data)

        # Send content if valid
        if article_data.get("title") and article_data.get("date_published"):
            # Save metadata
            try:
                # Prepare metadata as JSON for the database
                metadata = {
                    "title": article_data.get("title"),
                    "url": article_data.get("link"),  # Use 'link' field instead of 'url'
                    "source_name": article_data.get("source_name"),
                    "date_published": article_data.get("date_published"),
                    "processed_at": datetime.now().isoformat()
                }
                
                # Update the database with metadata
                logger.info(f"SCENARIO: SUCCESSFUL PROCESSING - Saving metadata for {url}")
                
                # Save metadata for both original and redirected URLs when appropriate
                if redirect_detected and original_url != url:
                    try:
                        onm_urls_update_metadata(url, metadata, cursor)
                    except Exception as e:
                        logger.warning(f"Failed to update metadata for redirected URL {url}: {e}")
                
                    # Also update original URL metadata with indication of redirect
                    redirect_metadata = metadata.copy()
                    redirect_metadata["redirected_to"] = url
                    try:
                        onm_urls_update_metadata(original_url, redirect_metadata, cursor)
                    except Exception as e:
                        logger.warning(f"Failed to update metadata for original URL {original_url}: {e}")
                else:
                    # Just update the metadata for the single URL
                    onm_urls_update_metadata(url, metadata, cursor)

            except Exception as e:
                logger.error(f"Metadata save error: {e}")
                # Continue anyway, this is not critical
                
            # Send content to Kafka
            logger.info(f"Sending article to kafka: {article_data}")
            send_content(article_data, self.producer)
            
            # Update status for both URLs appropriately
            if redirect_detected and original_url != url:
                logger.info(f"SCENARIO: REDIRECT SUCCESS - Marking redirected URL as success: {url}")
                if not onm_urls_is_url_added(url, cursor):
                    logger.warning(f"URL '{url}' missing from onm_urls table, adding it before status update")
                    redirect_data = {
                        'url': url,
                        'source_name': extract_source_name(url),
                        'status': 'running'  # Use running instead of processing
                    }
                    onm_urls_add_url(redirect_data, cursor)
                onm_urls_update_url_status(url, "success", cursor=cursor, increment_retry=False)
                
                logger.info(f"SCENARIO: REDIRECT SUCCESS - Marking original URL as duplicate: {original_url}")
                onm_urls_update_url_status(original_url, "duplicate", error_message=f"URL redirects to: {url}", cursor=cursor, increment_retry=False)
            else:
                if not onm_urls_is_url_added(url, cursor):
                    logger.warning(f"URL '{url}' missing from onm_urls table, adding it before status update")
                    redirect_data = {
                        'url': url,
                        'source_name': extract_source_name(url),
                        'status': 'running'  # Use running instead of processing
                    }
                    onm_urls_add_url(redirect_data, cursor)
                onm_urls_update_url_status(url, "success", cursor=cursor, increment_retry=False)
                
            logger.info(f"SCENARIO: COMPLETED - Article successfully sent: {url}")
            logger.debug(f"Article data: {article_data}")
        else:
            error_msg = "Missing title or published date"
            logger.warning(f"SCENARIO: VALIDATION ERROR - Invalid article data ({error_msg}): {url}")
            onm_urls_update_url_status(url, "error", error_message=error_msg, cursor=cursor, increment_retry=False)
            if redirect_detected and original_url != url:
                onm_urls_update_url_status(original_url, "error", error_message=f"{error_msg} (redirects to: {url})", cursor=cursor, increment_retry=False)

    def conditionals_dateformatting_by_portals(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies conditional date formatting based on the portal.
        
        Args:
            article_data: The article data to process
            
        Returns:
            The modified article data
        """

        url = article_data.get("link")
        source_name = article_data.get("source_name")
        if not url or not source_name:
            logger.warning("URL or source name is missing.")
            return article_data
        
        domains = [
            "gelora.co",
            "portal-islam.id",
            "oposisicerdas.com",
            "voi.id"
            #"beritatrans.com"
            # Add more domains as needed
        ]
        
        if source_name in domains:
            date_published = article_data.get("date_published")
            if date_published and date_published.endswith("T00:00:00.000+0000"):
                new_published_date = get_general_published_date(url)
                article_data["date_published"] = new_published_date
                logger.info(f"Updated date for {url}: {new_published_date}")
            else:
                if source_name =="voi.id" and date_published != None:
                    new_published_date = convert_voi_date(date_published)
                    article_data["date_published"] = new_published_date
                    logger.info(f"Updated date for {url}: {new_published_date}")
                else:
                    logger.info(f"No date update needed for {url}")

        return article_data

    def _check_and_store_redirect(self, url: str, cursor) -> str:
        """
        Checks if a URL redirects to another URL and stores the mapping.
        
        This function performs a GET request to detect redirects.
        Using GET instead of HEAD ensures better redirect detection as some
        servers handle these methods differently.
        
        Args:
            url: The URL to check for redirects
                
        Returns:
            The final URL after following redirects
        """
        import requests
        from requests.exceptions import RequestException
        import re
        
        def _validate_url_structure(url_to_check: str) -> bool:
            """
            Validates URL structure to prevent malformed URLs from being accepted.
            
            Returns:
                True if URL is valid, False otherwise
            """
            if not url_to_check:
                return False
                
            # Check for malformed patterns
            malformed_patterns = [
                r'\/\\/',  # Escaped forward slashes
                r'\\/',    # Mixed slash patterns
                r'/\/\/',  # Multiple forward slashes with escapes
                r'\.co\.id.*\.co\.id',  # Duplicate .co.id domains
                r'\.com.*\.com',        # Duplicate .com domains
                r'\.net.*\.net',        # Duplicate .net domains
                r'\.org.*\.org',        # Duplicate .org domains
            ]
            
            for pattern in malformed_patterns:
                if re.search(pattern, url_to_check):
                    logger.warning(f"Redirect validation: URL contains malformed pattern '{pattern}': {url_to_check}")
                    return False
            
            # Check for duplicate domain in path
            try:
                parsed = urlparse(url_to_check)
                if parsed.netloc:
                    domain_clean = parsed.netloc.replace('www.', '')
                    if domain_clean and domain_clean in parsed.path:
                        logger.warning(f"Redirect validation: URL contains duplicate domain '{domain_clean}' in path: {url_to_check}")
                        return False
                        
                    # Check for excessive path segments
                    path_segments = [seg for seg in parsed.path.split('/') if seg]
                    if len(path_segments) > 15:
                        logger.warning(f"Redirect validation: URL has too many path segments: {url_to_check}")
                        return False
                        
            except Exception as e:
                logger.warning(f"Redirect validation: Error parsing URL {url_to_check}: {e}")
                return False
                
            return True
        
        # Set up Sentry transaction and context
        with sentry_sdk.start_transaction(op="redirect_check", name=f"Redirect Check: {url}"):
            sentry_sdk.set_context("url_redirect", {"original_url": url})
            
            # Validate input URL first
            if not _validate_url_structure(url):
                logger.warning(f"Input URL failed validation: {url}")
                return url  # Return original URL if validation fails
            
            # First check in database
            try:
                canonical_url = onm_redirects_check_in_db(url, cursor)
                if canonical_url:
                    # Validate the cached canonical URL
                    if not _validate_url_structure(canonical_url):
                        logger.warning(f"Cached canonical URL failed validation: {canonical_url}")
                        # Continue to HTTP check instead of using invalid cached URL
                    else:
                        logger.info(f"Using canonical URL from redirect database: {canonical_url}")
                        sentry_sdk.set_context("url_redirect", {
                            "original_url": url, 
                            "canonical_url": canonical_url,
                            "source": "database_cache"
                        })
                        return canonical_url
            except Exception as e:
                logger.error(f"Error checking redirect in database for {url}: {e}")
                sentry_sdk.capture_exception(e)
                # Continue to HTTP check instead of failing
                
            # Don't check for redirects if we're in test mode
            if hasattr(self, '_test_mode') and self._test_mode:
                return url
                
            try:
                # Perform a GET request with redirect tracking
                # Using browser-like headers for better compatibility
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                response = requests.get(
                    url, 
                    allow_redirects=True,
                    timeout=15,  # Increased timeout for GET requests
                    headers=headers,
                    stream=True,  # Stream to avoid downloading full content
                    verify=True   # Verify SSL certificates
                )
                
                # Close the stream immediately as we only need the final URL
                response.close()
                
                # Get the final URL from the response
                final_url = response.url
                
                # Validate the final URL before accepting it
                if not _validate_url_structure(final_url):
                    logger.warning(f"Final URL failed validation after redirect: {final_url}")
                    return url  # Return original URL if final URL is malformed
                
                # Check if we were redirected by comparing URLs or checking history
                if response.history or final_url != url:
                    original_url = url
                    
                    # Build the redirect chain from history
                    if response.history:
                        all_urls = [r.url for r in response.history] + [final_url]
                    else:
                        # Sometimes there's no history but URL changed (e.g., fragment removal)
                        all_urls = [url, final_url]
                    
                    # Validate all URLs in the redirect chain
                    valid_chain = []
                    for chain_url in all_urls:
                        if _validate_url_structure(chain_url):
                            valid_chain.append(chain_url)
                        else:
                            logger.warning(f"Invalid URL in redirect chain: {chain_url}")
                            # Break the chain at the first invalid URL
                            break
                    
                    # If the chain was broken, use the last valid URL
                    if len(valid_chain) < len(all_urls):
                        logger.warning(f"Redirect chain broken due to invalid URL, using last valid: {valid_chain[-1] if valid_chain else url}")
                        final_url = valid_chain[-1] if valid_chain else url
                        all_urls = valid_chain
                    
                    logger.info(f"Redirect detected: {original_url} -> {final_url}")
                    
                    # Set redirect chain info in Sentry
                    sentry_sdk.set_context("url_redirect", {
                        "original_url": original_url,
                        "final_url": final_url,
                        "redirect_chain": all_urls,
                        "redirect_count": len(response.history) if response.history else 1,
                        "status_code": response.status_code
                    })
                    
                    # Store each step in the redirect chain (only valid URLs)
                    for i in range(len(all_urls) - 1):
                        from_url = all_urls[i]
                        to_url = all_urls[i+1]
                        try:
                            # Store each step in the redirect chain
                            onm_redirects_store(from_url, to_url, cursor)
                            logger.debug(f"Stored redirect step: {from_url} -> {to_url}")
                        except Exception as e:
                            error_msg = f"Failed to store redirect step: {e}"
                            logger.warning(error_msg)
                            # Capture this specific error with context
                            sentry_sdk.capture_exception(
                                e, 
                                extras={
                                    "from_url": from_url,
                                    "to_url": to_url,
                                    "step_index": i,
                                    "redirect_chain": all_urls
                                }
                            )
                    
                    # Check if there's a significant difference between original and final URLs
                    original_parsed = urlparse(original_url)
                    final_parsed = urlparse(final_url)
                    
                    original_domain = original_parsed.netloc
                    if original_domain.startswith('www.'):
                        original_domain = original_domain[4:]
                        
                    final_domain = final_parsed.netloc
                    if final_domain.startswith('www.'):
                        final_domain = final_domain[4:]
                    
                    original_path = original_parsed.path.rstrip('/')
                    final_path = final_parsed.path.rstrip('/')
                    
                    # Log cross-domain redirects more prominently
                    if original_domain != final_domain:
                        logger.info(f"Cross-domain redirect: {original_domain} -> {final_domain}")
                        logger.info(f"Full redirect: {original_url} -> {final_url}")
                        
                        # Record cross-domain redirects as a special event
                        sentry_sdk.capture_message(
                            f"Cross-domain redirect detected",
                            level="info",
                            extras={
                                "original_domain": original_domain,
                                "final_domain": final_domain,
                                "original_url": original_url,
                                "final_url": final_url
                            }
                        )
                    elif original_path != final_path:
                        logger.info(f"Path redirect: {original_path} -> {final_path}")
                        
                    # Normalize the URL to remove default ports
                    parsed = urlparse(final_url)
                    netloc = parsed.netloc
                    if ':' in netloc:
                        domain, port = netloc.split(':', 1)
                        # Remove default ports (443 for HTTPS, 80 for HTTP)
                        if (parsed.scheme == 'https' and port == '443') or (parsed.scheme == 'http' and port == '80'):
                            netloc = domain
                            final_url = urlunparse((
                                parsed.scheme, netloc, parsed.path,
                                parsed.params, parsed.query, parsed.fragment
                            ))
                            logger.debug(f"Normalized URL by removing default port: {final_url}")
                    
                    # Also normalize the original URL if it has default ports
                    original_parsed = urlparse(original_url)
                    original_netloc = original_parsed.netloc
                    if ':' in original_netloc:
                        domain, port = original_netloc.split(':', 1)
                        if (original_parsed.scheme == 'https' and port == '443') or (original_parsed.scheme == 'http' and port == '80'):
                            original_netloc = domain
                            original_url = urlunparse((
                                original_parsed.scheme, original_netloc, original_parsed.path,
                                original_parsed.params, original_parsed.query, original_parsed.fragment
                            ))
                            logger.debug(f"Normalized original URL by removing default port: {original_url}")
                    
                    # Final validation after normalization
                    if not _validate_url_structure(final_url):
                        logger.warning(f"Final URL failed validation after normalization: {final_url}")
                        return url  # Return original URL if normalization created invalid URL
                    
                    # Always use the final URL from a redirect
                    return final_url
                else:
                    # No redirect detected - URLs are the same
                    logger.debug(f"No redirect detected for: {url}")
                
                # Return the final URL (could be same as original if no redirect)
                return final_url
                
            except RequestException as e:
                error_msg = f"Error checking redirects for {url}: {e}"
                logger.warning(error_msg)
                
                # Capture network-related redirect errors with context
                sentry_sdk.capture_exception(
                    e,
                    extras={
                        "url": url,
                        "operation": "redirect_check",
                        "error_type": "request_exception"
                    }
                )
                
                return url  # Return original URL on error
            except Exception as e:
                error_msg = f"Unexpected error in redirect check: {e}"
                logger.error(error_msg)
                
                # Capture unexpected errors with context
                sentry_sdk.capture_exception(
                    e,
                    extras={
                        "url": url,
                        "operation": "redirect_check",
                        "error_type": "unexpected"
                    }
                )
                
                return url  # Return original URL on error

    def _is_date_only_format(self, date_str: str) -> bool:
        """
        Check if the date string contains only date information without time.
        
        Args:
            date_str: The date string to check
            
        Returns:
            True if the date is in date-only format, False otherwise
        """
        if not date_str:
            return False
        
        # Common date-only patterns
        date_only_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',                    # 2025-06-10
            r'^\d{4}/\d{2}/\d{2}$',                    # 2025/06/10
            r'^\d{2}/\d{2}/\d{4}$',                    # 10/06/2025
            r'^\d{2}-\d{2}-\d{4}$',                    # 10-06-2025
            r'^\d{4}\.\d{2}\.\d{2}$',                  # 2025.06.10
        ]
        
        import re
        for pattern in date_only_patterns:
            if re.match(pattern, date_str.strip()):
                logger.debug(f"Detected date-only format: {date_str}")
                return True
        
        return False
    
    def _enrich_date_with_current_time(self, date_str: str) -> Optional[str]:
        """
        Enrich a date-only string with the current scraping time.
        
        Args:
            date_str: The date-only string (e.g., "2025-06-10")
            
        Returns:
            Enriched date string with current time or None if enrichment fails
        """
        try:
            # Parse the date-only string
            parsed_date = parse_date(date_str)
            if not parsed_date:
                logger.warning(f"Failed to parse date for enrichment: {date_str}")
                return None
            
            # Get current time in Jakarta timezone (WIB)
            jakarta_tz = pytz.timezone('Asia/Jakarta')
            current_time = datetime.now(jakarta_tz)
            
            # Combine the parsed date with current time
            enriched_datetime = parsed_date.replace(
                hour=current_time.hour,
                minute=current_time.minute,
                second=current_time.second,
                tzinfo=jakarta_tz
            )
            
            # Format as ISO string with timezone
            enriched_date_str = enriched_datetime.strftime('%Y-%m-%dT%H:%M:%S%z')
            
            # Ensure proper timezone format (+07:00 instead of +0700)
            if enriched_date_str.endswith('+0700'):
                enriched_date_str = enriched_date_str[:-5] + '+07:00'
            elif enriched_date_str.endswith('-0700'):
                enriched_date_str = enriched_date_str[:-5] + '-07:00'
            elif len(enriched_date_str) >= 4 and enriched_date_str[-4:].isdigit():
                # Handle cases like +0707 or -0707
                if enriched_date_str[-5] in ['+', '-']:
                    tz_part = enriched_date_str[-5:]
                    if len(tz_part) == 5 and tz_part[1:].isdigit():
                        # Convert +0707 to +07:07, but for Jakarta it should be +07:00
                        hours = tz_part[1:3]
                        minutes = tz_part[3:5]
                        if minutes == '07':  # Jakarta timezone specific fix
                            minutes = '00'
                        enriched_date_str = enriched_date_str[:-5] + f"{tz_part[0]}{hours}:{minutes}"
            
            logger.debug(f"Enriched date: {date_str} -> {enriched_date_str}")
            return enriched_date_str
            
        except Exception as e:
            logger.warning(f"Error enriching date {date_str}: {e}")
            return None

    def _preprocess_date_format(self, date_str: str) -> str:
        """
        Preprocesses the date format to handle special formats like "2025-06-19T11-04-20Z"
        
        Args:
            date_str: The date string to preprocess
            
        Returns:
            Preprocessed date string
        """
        import re
        if not date_str:
            return date_str
        
        # Handle the specific case of ISO format with hyphens in time portion
        # Pattern: YYYY-MM-DDTHH-MM-SSZ -> YYYY-MM-DDTHH:MM:SSZ
        if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z$', date_str):
            # Replace hyphens with colons only in the time portion (after T)
            date_part, time_part = date_str.split('T')
            time_part = time_part.replace('-', ':')
            return f"{date_part}T{time_part}"
        
        return date_str


if __name__ == "__main__":
    scraper = ZyteScraper()
    scraper.start_scrape()

