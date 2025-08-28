import logging
import json
import re
from datetime import datetime, timedelta
from django.conf import settings
from elasticsearch6 import Elasticsearch as Elasticsearch6
from elasticsearch import Elasticsearch

# Set up logging
logger = logging.getLogger(__name__)

class ElasticsearchManager:
    """
    Utility class for interacting with Elasticsearch.
    Handles connections, searching, and document operations.
    """
    
    def __init__(self, index='v3_prod_online_media'):
        """
        Initialize the Elasticsearch connection.
        
        Args:
            index (str): The default Elasticsearch index to use
        """
        self.index = index
        self.connected = False
        self.es = None
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # Cache TTL in seconds
        self.cache_last_cleaned = datetime.now()
        
        # Get Elasticsearch settings from Django settings or use defaults
        self.hosts = getattr(settings, 'ELASTICSEARCH_HOST', 'https://esnode02.dashboard.nolimit.id')
        self.username = getattr(settings, 'ELASTICSEARCH_USERNAME', 'esclient01')
        self.password = getattr(settings, 'ELASTICSEARCH_PASSWORD', 'nolimitsukses27A!')

        
        # Initialize connection
        self._connect()
    
    def _connect(self):
        """Establish connection to Elasticsearch"""
        try:
            # Use Elasticsearch6 client for compatibility
            self.es = Elasticsearch6(
                [self.hosts],
                http_auth=(self.username, self.password),
                timeout=30
            )
            
            # Check if connection is successful
            if self.es.ping():
                self.connected = True
                logger.info(f"Successfully connected to Elasticsearch at {self.hosts}")
            else:
                logger.error("Failed to connect to Elasticsearch - ping failed")
                self.connected = False
                
        except Exception as e:
            logger.error(f"Elasticsearch connection error: {str(e)}")
            self.connected = False
    
    def _clean_cache(self):
        """Clean expired items from cache"""
        now = datetime.now()
        # Only clean periodically to avoid excessive checks
        if (now - self.cache_last_cleaned).total_seconds() > 60:
            expired_keys = []
            for key, (timestamp, _) in self.cache.items():
                if (now - timestamp).total_seconds() > self.cache_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
            
            self.cache_last_cleaned = now
    
    def _escape_query_string(self, query_text):
        """
        Escape special characters in query string to prevent injection
        
        Args:
            query_text (str): The original query string
            
        Returns:
            str: The escaped query string
        """
        if not query_text:
            return query_text
            
        # Escape special characters: + - = && || > < ! ( ) { } [ ] ^ " ~ * ? : \ /
        special_chars = ['+', '-', '=', '&&', '||', '>', '<', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?', ':', '\\', '/']
        escaped_query = query_text
        
        for char in special_chars:
            escaped_query = escaped_query.replace(char, f"\\{char}")
            
        return escaped_query
    
    def search(self, query_text, index=None, size=50, from_pos=0, sort_by='date_published', 
               sort_order='desc', date_from=None, date_to=None, source_filter=None, 
               search_type='text', language=None, fields=None, use_cache=True, search_context='all'):
        """
        Perform a search query on Elasticsearch.
        
        Args:
            query_text (str): The search query
            index (str, optional): The index to search in. Defaults to None (uses default index).
            size (int, optional): Maximum number of results to return. Defaults to 50.
            from_pos (int, optional): Starting position for pagination. Defaults to 0.
            sort_by (str, optional): Field to sort results by. Defaults to 'date_published'.
            sort_order (str, optional): Sort direction - 'asc' or 'desc'. Defaults to 'desc'.
            date_from (str, optional): Start date for filtering (YYYY-MM-DD).
            date_to (str, optional): End date for filtering (YYYY-MM-DD).
            source_filter (list, optional): List of source names to filter by.
            search_type (str, optional): Type of search - 'text', 'link', 'advanced'. Defaults to 'text'.
            language (str, optional): Filter by document language.
            fields (list, optional): Custom fields to search in, overrides defaults.
            use_cache (bool, optional): Whether to use cache. Defaults to True.
            search_context (str, optional): Which field to focus search on. Defaults to 'all'.
            
        Returns:
            dict: Search results with hits and metadata
        """
        if not self.connected:
            self._connect()
            if not self.connected:
                raise ConnectionError("Could not connect to Elasticsearch")
        
        search_index = index or self.index
        
        # Clean cache if using cache
        if use_cache:
            self._clean_cache()
            
            # Check if result is in cache
            cache_key = f"{search_index}_{query_text}_{size}_{from_pos}_{sort_by}_{sort_order}_{date_from}_{date_to}_{source_filter}_{search_type}_{language}_{search_context}"
            if cache_key in self.cache:
                logger.debug(f"Cache hit for query: {query_text}")
                return self.cache[cache_key][1]
        
        try:
            # Define default search fields with boosting
            default_search_fields = ["title^3", "body", "source_name", "description^2", "link^4"]
            
            # Override fields based on search_context if specified
            if search_context and search_context != 'all':
                if search_context == 'title':
                    search_fields = ["title^5"]
                elif search_context == 'source_name':
                    search_fields = ["source_name^5"]
                elif search_context == 'body':
                    search_fields = ["body^5"]
                elif search_context == 'link':
                    search_fields = ["link^5"]
                else:
                    search_fields = fields or default_search_fields
            else:
                search_fields = fields or default_search_fields
            
            # Build filters list for query
            filters = []
            
            # Add date range filter if specified
            if date_from or date_to:
                date_range = {}
                if date_from:
                    date_range["gte"] = date_from
                if date_to:
                    date_range["lte"] = date_to
                
                filters.append({
                    "range": {
                        "date_published": date_range
                    }
                })
            
            # Add source filter if specified
            if source_filter:
                filters.append({
                    "terms": {
                        "source_name": source_filter
                    }
                })
            
            # Add language filter if specified
            if language:
                filters.append({
                    "term": {
                        "language": language
                    }
                })
            
            # Determine query type based on search_type
            if search_type == 'link':
                # Exact match on link field
                main_query = {
                    "match": {
                        "link": query_text
                    }
                }
            elif search_type == 'advanced':
                # Use query_string for advanced operators (AND, OR, NOT)
                main_query = {
                    "query_string": {
                        "query": self._escape_query_string(query_text),
                        "fields": search_fields,
                        "default_operator": "AND"
                    }
                }
            else:
                # Default text search
                main_query = {
                    "multi_match": {
                        "query": query_text,
                        "fields": search_fields,
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                }
            
            # Build the final query
            if filters:
                query = {
                    "bool": {
                        "must": main_query,
                        "filter": filters
                    }
                }
            else:
                query = main_query
            
            # Build the search query
            search_query = {
                "from": from_pos,
                "size": size,
                "query": query,
                "highlight": {
                    "fields": {
                        "title": {},
                        "body": {"fragment_size": 150, "number_of_fragments": 3},
                        "description": {}
                    },
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                },
                "_source": ["title", "source_name", "date_published", "link", "language", "author_list", "created_at", "date_created"],
                "sort": self._build_sort_config(sort_by, sort_order)
            }
            
            # Add aggregations for faceted search
            search_query["aggs"] = {
                "sources": {
                    "terms": {
                        "field": "source_name",
                        "size": 20
                    }
                },
                "languages": {
                    "terms": {
                        "field": "language",
                        "size": 10
                    }
                },
                "date_histogram": {
                    "date_histogram": {
                        "field": "date_published",
                        "interval": "month"
                    }
                }
            }
            
            # Execute the search
            response = self.es.search(index=search_index, body=search_query)
            
            # Process results
            hits = response.get("hits", {}).get("hits", [])
            total = response.get("hits", {}).get("total", 0)
            results = []
            
            for hit in hits:
                # Get source data
                source = hit.get('_source', {})
                
                # Extract highlights
                highlights = hit.get('highlight', {})
                highlight_text = []
                
                for field, snippets in highlights.items():
                    if snippets:
                        highlight_text.extend(snippets)
                
                # Create result object
                result = {
                    'id': hit.get('_id'),  # Keep for backward compatibility
                    'title': source.get('title', 'No Title'),
                    'source': source.get('source_name', 'Unknown'),
                    'url': source.get('link', ''),
                    'date_published': source.get('date_published'),
                    'created_at': source.get('created_at') or source.get('date_created'),
                    'score': hit.get('_score'),
                    'highlights': highlight_text[:3],  # Limit to top 3 highlights
                    'language': source.get('language', 'id'),
                    'authors': source.get('author_list', []),
                    'doc_id': hit.get('_id'),  # Hidden ID for use with full data icon
                    'es_metadata': {
                        'id': hit.get('_id'),
                        'index': hit.get('_index'),
                        'version': hit.get('_version'),
                        'timestamp': datetime.now().isoformat()  # Current timestamp as fallback for creation time
                    }
                }
                
                results.append(result)
            
            # Process aggregations
            aggregations = response.get("aggregations", {})
            facets = {
                "sources": [],
                "languages": [],
                "dates": []
            }
            
            # Extract source facets
            for bucket in aggregations.get("sources", {}).get("buckets", []):
                facets["sources"].append({
                    "name": bucket.get("key"),
                    "count": bucket.get("doc_count")
                })
            
            # Extract language facets
            for bucket in aggregations.get("languages", {}).get("buckets", []):
                facets["languages"].append({
                    "code": bucket.get("key"),
                    "count": bucket.get("doc_count")
                })
            
            # Extract date facets
            for bucket in aggregations.get("date_histogram", {}).get("buckets", []):
                facets["dates"].append({
                    "date": bucket.get("key_as_string"),
                    "count": bucket.get("doc_count")
                })
            
            # Prepare final response
            final_response = {
                "total": total,
                "results": results,
                "facets": facets
            }
            
            # Cache the result if caching is enabled
            if use_cache:
                self.cache[cache_key] = (datetime.now(), final_response)
            
            return final_response
            
        except Exception as e:
            logger.error(f"Elasticsearch query error: {str(e)}")
            raise
    
    def search_by_link(self, link, index=None):
        """
        Search for an article by its exact link URL.
        Convenience method that wraps around the main search function.
        
        Args:
            link (str): The URL link to search for
            index (str, optional): The index to search in
            
        Returns:
            dict: Search results focusing on matching link
        """
        return self.search(
            query_text=link,
            index=index,
            search_type='link',
            size=5  # Limit to 5 results since we expect 1 or 0
        )
    
    def get_document(self, doc_id, index=None, doc_type="_doc"):
        """
        Retrieve a specific document by ID.
        
        Args:
            doc_id (str): The document ID
            index (str, optional): The index to search in. Defaults to None (uses default index).
            doc_type (str, optional): Document type. Defaults to "_doc".
            
        Returns:
            dict: The document with metadata
        """
        if not self.connected:
            self._connect()
            if not self.connected:
                raise ConnectionError("Could not connect to Elasticsearch")
        
        search_index = index or self.index
        
        try:
            # Get the document with full metadata
            result = self.es.get(index=search_index, doc_type=doc_type, id=doc_id, _source=True)
            
            # Combine source and metadata
            document = result.get('_source', {})
            
            # Add Elasticsearch metadata
            document['es_metadata'] = {
                'id': result.get('_id'),
                'index': result.get('_index'),
                'type': result.get('_type'),
                'version': result.get('_version'),
                'seqNo': result.get('_seq_no'),
                'primaryTerm': result.get('_primary_term'),
                'found': result.get('found'),
                'timestamp': datetime.now().isoformat()
            }
            
            return document
        except Exception as e:
            logger.error(f"Error retrieving document {doc_id}: {str(e)}")
            raise
    
    def get_document_by_link(self, link, index=None):
        """
        Fetches documents from the index by link.
        
        Args:
            link (str): The URL link to search for
            index (str, optional): The index to search in. Defaults to None (uses default index).
            
        Returns:
            list: Documents matching the link
        """
        if not self.connected:
            self._connect()
            if not self.connected:
                raise ConnectionError("Could not connect to Elasticsearch")
        
        search_index = index or self.index
        
        query = {
            "query": {
                "match": {
                    "link": link
                }
            }
        }
        
        try:
            response = self.es.search(index=search_index, body=query)
            hits = response.get("hits", {}).get("hits", [])

            if not hits:
                logger.info("No document found with the specified link.")
                return None

            return hits
        except Exception as e:
            logger.error(f"Error fetching document by link: {e}", exc_info=True)
            return None
    
    def update_document(self, doc_id, update_fields, index=None, doc_type="_doc"):
        """
        Update a document by ID.
        
        Args:
            doc_id (str): The document ID
            update_fields (dict): Fields to update
            index (str, optional): The index to update in. Defaults to None (uses default index).
            doc_type (str, optional): Document type. Defaults to "_doc".
            
        Returns:
            bool: True if successful, None if error
        """
        if not self.connected:
            self._connect()
            if not self.connected:
                raise ConnectionError("Could not connect to Elasticsearch")
        
        search_index = index or self.index
        
        try:
            self.es.update(
                index=search_index,
                doc_type=doc_type,
                id=doc_id,
                body={"doc": update_fields}
            )
            logger.info(f"Successfully updated document with ID {doc_id}")
            
            # Clear cache on update
            self._clean_cache()
            
            return True
        except Exception as e:
            logger.error(f"Error updating document with ID {doc_id}: {e}", exc_info=True)
            return None
    
    def update_document_by_link(self, link, update_fields, index=None):
        """
        Update a document by its link URL.
        
        Args:
            link (str): The URL link to find the document
            update_fields (dict): Fields to update
            index (str, optional): The index to update in. Defaults to None (uses default index).
            
        Returns:
            bool or str: True if successful, error message if not
        """
        if not self.connected:
            self._connect()
            if not self.connected:
                raise ConnectionError("Could not connect to Elasticsearch")
        
        logger.info(f"Attempting to update document with link: {link}")

        doc = self.get_document_by_link(link, index)

        if not doc:
            logger.warning(f"Document with link {link} not found.")
            return "Document not found"

        doc_id = doc[0]["_id"]

        try:
            result = self.update_document(doc_id, update_fields, index)
            if result:
                logger.info(f"Successfully updated document with ID {doc_id} - Link {link}")
                return True
            else:
                return None
        except Exception as e:
            logger.error(f"Error updating document with link {link}: {e}", exc_info=True)
            return None
    
    def insert_document(self, document, index=None):
        """
        Insert a new document.
        
        Args:
            document (dict): Document to insert
            index (str, optional): The index to insert into. Defaults to None (uses default index).
            
        Returns:
            bool: True if successful, None if error
        """
        if not self.connected:
            self._connect()
            if not self.connected:
                raise ConnectionError("Could not connect to Elasticsearch")
        
        search_index = index or self.index
        
        # Check if document already exists
        if 'link' in document:
            exist = self.get_document_by_link(document["link"], index)
            if exist:
                logger.warning(f"Document with link {document['link']} already exists")
                return None
        
        try:
            response = self.es.index(index=search_index, doc_type="_doc", body=document)
            logger.info(f"Document inserted successfully with ID {response['_id']}")
            
            # Clear cache on insert
            self._clean_cache()
            
            return True
        except Exception as e:
            logger.error(f"Error inserting document: {e}", exc_info=True)
            return None
    
    def delete_document(self, doc_id, index=None, doc_type="_doc"):
        """
        Delete a document by ID.
        
        Args:
            doc_id (str): The document ID
            index (str, optional): The index to delete from. Defaults to None (uses default index).
            doc_type (str, optional): Document type. Defaults to "_doc".
            
        Returns:
            bool: True if successful, False if not found, None if error
        """
        if not self.connected:
            self._connect()
            if not self.connected:
                raise ConnectionError("Could not connect to Elasticsearch")
        
        search_index = index or self.index
        
        try:
            response = self.es.delete(index=search_index, doc_type=doc_type, id=doc_id)
            
            # Clear cache on delete
            self._clean_cache()
            
            if response.get("result") == "deleted":
                logger.info(f"Document with ID {doc_id} successfully deleted.")
                return True
            else:
                logger.warning(f"Document with ID {doc_id} was not found or already deleted.")
                return False
        except Exception as e:
            logger.error(f"Error deleting document with ID {doc_id}: {e}", exc_info=True)
            return None
    
    def delete_document_by_link(self, link, index=None):
        """
        Delete a document by its link URL.
        
        Args:
            link (str): The URL link to find the document
            index (str, optional): The index to delete from. Defaults to None (uses default index).
            
        Returns:
            bool or str: True if successful, error message if not
        """
        if not self.connected:
            self._connect()
            if not self.connected:
                raise ConnectionError("Could not connect to Elasticsearch")
        
        logger.info(f"Attempting to delete document with link: {link}")

        doc = self.get_document_by_link(link, index)

        if not doc:
            logger.warning(f"Document with link {link} not found.")
            return "Document not found"

        doc_id = doc[0]["_id"]

        try:
            result = self.delete_document(doc_id, index)
            if result:
                logger.info(f"Successfully deleted document with ID {doc_id} - Link {link}")
                return True
            else:
                return None
        except Exception as e:
            logger.error(f"Error deleting document with link {link}: {e}", exc_info=True)
            return None
    
    def get_indices(self):
        """
        Get a list of available indices.
        
        Returns:
            list: List of index names
        """
        if not self.connected:
            self._connect()
            if not self.connected:
                raise ConnectionError("Could not connect to Elasticsearch")
        
        try:
            indices = self.es.indices.get_alias(index="*")
            return list(indices.keys())
        except Exception as e:
            logger.error(f"Error retrieving indices: {str(e)}")
            return []

    def _build_sort_config(self, sort_by, sort_order):
        """
        Build the sort configuration for the Elasticsearch query.
        
        Args:
            sort_by (str): Field to sort by
            sort_order (str): Sort order ('asc' or 'desc')
            
        Returns:
            list: Sort configuration for the query
        """
        if sort_by == '_score':
            # When sorting by score, we don't need the missing parameter
            return ["_score"]
        else:
            # For document fields, use the standard object notation with missing
            return [
                {
                    sort_by: {
                        "order": sort_order,
                        "missing": "_last"  # Documents without the field will appear last
                    }
                },
                "_score"  # Secondary sort by relevance score
            ]
