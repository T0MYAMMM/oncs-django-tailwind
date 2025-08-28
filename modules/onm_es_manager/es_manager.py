import json
import logging
from django.conf import settings
from .elastic_utils import ElasticsearchManager

# Set up logging
logger = logging.getLogger(__name__)

class ONMManager:
    """
    Online Media Manager for integrating with the ONM system.
    Provides a clean interface for interacting with the ONM content index.
    """
    
    def __init__(self):
        """Initialize the ONM Manager with default settings"""
        # Get ONM settings from Django settings or use defaults
        self.es_host = getattr(settings, 'ELASTICSEARCH_HOST', 'https://esnode02.dashboard.nolimit.id')
        self.es_username = getattr(settings, 'ELASTICSEARCH_USERNAME', 'esclient01')
        self.es_password = getattr(settings, 'ELASTICSEARCH_PASSWORD', 'nolimitsukses27A!$')
        self.onm_index = getattr(settings, 'ELASTICSEARCH_ONM_INDEX', 'v3_prod_online_media')
        
        # Initialize Elasticsearch manager
        self.es_manager = ElasticsearchManager(index=self.onm_index)
    
    def search_articles(self, query_text, page=1, page_size=20, sort_by='date_published', 
                       sort_order='desc', date_from=None, date_to=None, language=None, 
                       search_type='text', source_filter=None, use_cache=True, search_context='all'):
        """
        Search for articles in the ONM index with enhanced filtering and pagination.
        
        Args:
            query_text (str): The search query
            page (int, optional): Page number for pagination. Defaults to 1.
            page_size (int, optional): Number of results per page. Defaults to 20.
            sort_by (str, optional): Field to sort results by. Defaults to 'date_published'.
            sort_order (str, optional): Sort direction - 'asc' or 'desc'. Defaults to 'desc'.
            date_from (str, optional): Start date for filtering (YYYY-MM-DD).
            date_to (str, optional): End date for filtering (YYYY-MM-DD).
            language (str, optional): Filter by document language.
            search_type (str, optional): Type of search - 'text', 'link', 'advanced'. Defaults to 'text'.
            source_filter (list, optional): List of source names to filter by.
            use_cache (bool, optional): Whether to use cache. Defaults to True.
            search_context (str, optional): Which field to focus search on. Defaults to 'all'.
            
        Returns:
            dict: Search results with hits, facets and pagination metadata
        """
        # Convert page and page_size to integers for calculation
        try:
            page = int(page)
            page_size = int(page_size)
        except (ValueError, TypeError):
            page = 1
            page_size = 20
        
        # Calculate from_pos (zero-based for Elasticsearch)
        from_pos = (page - 1) * page_size
        
        # Perform search with all parameters
        search_results = self.es_manager.search(
            query_text=query_text,
            size=page_size,
            from_pos=from_pos,
            sort_by=sort_by,
            sort_order=sort_order,
            date_from=date_from,
            date_to=date_to,
            language=language,
            search_type=search_type,
            source_filter=source_filter,
            use_cache=use_cache,
            search_context=search_context
        )
        
        # Add pagination metadata
        total_results = search_results.get('total', 0)
        total_pages = (total_results + page_size - 1) // page_size if total_results > 0 else 0
        
        search_results['pagination'] = {
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'total_results': total_results,
            'has_next': page < total_pages,
            'has_previous': page > 1,
            'next_page': page + 1 if page < total_pages else None,
            'previous_page': page - 1 if page > 1 else None
        }
        
        return search_results
    
    def search_articles_by_link(self, link, index=None):
        """
        Search for articles by exact link URL.
        
        Args:
            link (str): The article URL to search for
            index (str, optional): The index to search in
            
        Returns:
            dict: Search results focusing on matching link
        """
        return self.es_manager.search_by_link(link, index)
    
    def get_article(self, article_id):
        """
        Get a specific article by ID.
        
        Args:
            article_id (str): The article ID
            
        Returns:
            dict: The article document
        """
        return self.es_manager.get_document(article_id)
    
    def get_article_by_url(self, url):
        """
        Get an article by its URL.
        
        Args:
            url (str): The article URL
            
        Returns:
            dict: The article document or None if not found
        """
        docs = self.es_manager.get_document_by_link(url)
        if docs and len(docs) > 0:
            return docs[0]['_source']
        return None
    
    def update_article(self, article_id, update_data):
        """
        Update an article by ID.
        
        Args:
            article_id (str): The article ID
            update_data (dict): Data to update
            
        Returns:
            bool: True if successful, None if error
        """
        return self.es_manager.update_document(article_id, update_data)
    
    def update_article_by_url(self, url, update_data):
        """
        Update an article by URL.
        
        Args:
            url (str): The article URL
            update_data (dict): Data to update
            
        Returns:
            bool or str: True if successful, error message if not
        """
        return self.es_manager.update_document_by_link(url, update_data)
    
    def add_article(self, article_data):
        """
        Add a new article to the ONM index.
        
        Args:
            article_data (dict): Article data to insert
            
        Returns:
            bool: True if successful, None if error
        """
        # Make sure required fields are present
        required_fields = ['title', 'body', 'link', 'source_name']
        missing_fields = [field for field in required_fields if field not in article_data]
        
        if missing_fields:
            logger.error(f"Missing required fields for article: {', '.join(missing_fields)}")
            return None
        
        return self.es_manager.insert_document(article_data)
    
    def delete_article(self, article_id):
        """
        Delete an article by ID.
        
        Args:
            article_id (str): The article ID
            
        Returns:
            bool: True if successful, False if not found, None if error
        """
        return self.es_manager.delete_document(article_id)
    
    def delete_article_by_url(self, url):
        """
        Delete an article by its URL.
        
        Args:
            url (str): The article URL
            
        Returns:
            bool or str: True if successful, error message if not
        """
        return self.es_manager.delete_document_by_link(url)
    
    def get_statistics(self):
        """
        Get statistics about the ONM index.
        
        Returns:
            dict: Statistics about the ONM system
        """
        # This would normally involve more complex queries to get statistics
        # For now, returning a basic structure
        return {
            'articles_count': 0,  # Would be replaced with actual count
            'sources_count': 0,   # Would be replaced with actual count
            'languages': {},      # Would be replaced with language distributions
            'recent_articles': 0  # Would be replaced with recent article count
        }