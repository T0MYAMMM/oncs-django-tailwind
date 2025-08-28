import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Tuple, Dict, Any


def clean_url(url: str) -> Tuple[str, Dict[str, Any]]:
    """
    Clean URL according to specified rules:
    - Remove www.
    - Remove query params like utm_source, ref, etc.
    - Remove fragments like #google_vignette, #comments, #section
    - Remove trailing slash
    
    Args:
        url (str): Original URL to clean
        
    Returns:
        Tuple[str, Dict]: Cleaned URL and cleaning report
    """
    if not url:
        return "", {"error": "Empty URL provided"}
    
    original_url = url
    cleaning_report = {
        "original_url": original_url,
        "cleaned_url": "",
        "changes_made": [],
        "removed_params": [],
        "removed_fragments": [],
        "removed_www": False,
        "removed_trailing_slash": False
    }
    
    try:
        # Parse the URL
        parsed = urlparse(url)
        
        # Ensure protocol is present
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)
            cleaning_report["changes_made"].append("Added https:// protocol")
        
        # Remove www. from domain
        if parsed.netloc.startswith("www."):
            new_netloc = parsed.netloc[4:]
            parsed = parsed._replace(netloc=new_netloc)
            cleaning_report["removed_www"] = True
            cleaning_report["changes_made"].append("Removed 'www.' prefix")
        
        # Clean query parameters - remove tracking and unnecessary params
        if parsed.query:
            query_params = parse_qs(parsed.query)
            cleaned_params = {}
            removed_params = []
            
            # Define parameters to remove (tracking, analytics, etc.)
            params_to_remove = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'ref', 'referrer', 'source', 'campaign', 'fbclid', 'gclid',
                'mc_cid', 'mc_eid', 'si', 's', 'spm', 'from', 'via',
                'share', 'shared', 'sharing', 'social', 'social_source',
                'affiliate', 'aff', 'partner', 'click', 'clicked',
                'redirect', 'redirect_to', 'return', 'return_to',
                #'next', 'next_page', 'previous', 'prev', 'back', 'page', 'p', 
                'start', 'offset', 'limit', 'per_page',
                'sort', 'order', 'filter', 'search', 'q', 'query',
                'keyword', 'tags', 'category', 'cat', 'section',
                'author', 'writer', 'reporter', 'editor',
                'date', 'time', 'year', 'month', 'day',
                'lang', 'language', 'locale', 'region', 'country',
                'device', 'mobile', 'desktop', 'tablet',
                'version', 'v', 'build', 'release',
                'debug', 'test', 'staging', 'dev', 'development',
                'preview', 'draft', 'beta', 'alpha'
            }
            
            for param, values in query_params.items():
                param_lower = param.lower()
                if param_lower in params_to_remove or any(tracking in param_lower for tracking in ['utm_', 'ref', 'fbclid', 'gclid']):
                    removed_params.append(f"{param}={','.join(values)}")
                else:
                    cleaned_params[param] = values
            
            if removed_params:
                cleaning_report["removed_params"] = removed_params
                cleaning_report["changes_made"].append(f"Removed {len(removed_params)} tracking/unnecessary parameters")
            
            # Rebuild query string
            if cleaned_params:
                new_query = urlencode(cleaned_params, doseq=True)
                parsed = parsed._replace(query=new_query)
            else:
                parsed = parsed._replace(query="")
        
        # Remove fragments (hash parts)
        if parsed.fragment:
            # Check for specific fragments to remove
            fragments_to_remove = ['google_vignette', 'comments', 'section', 'content', 'main', 'article']
            fragment_lower = parsed.fragment.lower()
            
            if any(frag in fragment_lower for frag in fragments_to_remove):
                cleaning_report["removed_fragments"].append(parsed.fragment)
                cleaning_report["changes_made"].append("Removed fragment")
                parsed = parsed._replace(fragment="")
        
        # Remove trailing slash from path
        if parsed.path.endswith('/') and len(parsed.path) > 1:
            new_path = parsed.path.rstrip('/')
            parsed = parsed._replace(path=new_path)
            cleaning_report["removed_trailing_slash"] = True
            cleaning_report["changes_made"].append("Removed trailing slash")
        
        # Rebuild the cleaned URL
        cleaned_url = urlunparse(parsed)
        cleaning_report["cleaned_url"] = cleaned_url
        
        # Check if any changes were made
        if cleaned_url != original_url:
            cleaning_report["changes_made"].append("URL cleaned successfully")
        else:
            cleaning_report["changes_made"].append("No changes needed - URL already clean")
        
        return cleaned_url, cleaning_report
        
    except Exception as e:
        cleaning_report["error"] = f"Error cleaning URL: {str(e)}"
        return original_url, cleaning_report


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate if a URL is properly formatted
    
    Args:
        url (str): URL to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"
    
    try:
        parsed = urlparse(url)
        
        # Check if scheme is present
        if not parsed.scheme:
            return False, "URL must include protocol (http:// or https://)"
        
        # Check if scheme is valid
        if parsed.scheme not in ['http', 'https']:
            return False, "URL must use HTTP or HTTPS protocol"
        
        # Check if netloc (domain) is present
        if not parsed.netloc:
            return False, "URL must include a valid domain"
        
        # Basic domain format check
        domain_pattern = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$')
        domain = parsed.netloc.split(':')[0]  # Remove port if present
        
        if not domain_pattern.match(domain):
            return False, "URL contains invalid domain format"
        
        return True, "URL is valid"
        
    except Exception as e:
        return False, f"URL validation error: {str(e)}"


def get_url_cleaning_summary(cleaning_report: Dict[str, Any]) -> str:
    """
    Generate a user-friendly summary of URL cleaning changes
    
    Args:
        cleaning_report (Dict): Cleaning report from clean_url function
        
    Returns:
        str: Formatted summary message
    """
    if "error" in cleaning_report:
        return f"Error: {cleaning_report['error']}"
    
    changes = cleaning_report.get("changes_made", [])
    if not changes or changes == ["No changes needed - URL already clean"]:
        return "URL is already clean - no changes needed."
    
    summary_parts = []
    
    if cleaning_report.get("removed_www"):
        summary_parts.append("Removed 'www.' prefix")
    
    if cleaning_report.get("removed_params"):
        param_count = len(cleaning_report["removed_params"])
        summary_parts.append(f"Removed {param_count} tracking/unnecessary parameters")
    
    if cleaning_report.get("removed_fragments"):
        summary_parts.append("Removed unnecessary fragments")
    
    if cleaning_report.get("removed_trailing_slash"):
        summary_parts.append("Removed trailing slash")
    
    return "URL cleaned: " + ", ".join(summary_parts)
