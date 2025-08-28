import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from .kafka_client import KafkaClientManager
from .message_handlers import create_message_handler

logger = logging.getLogger(__name__)


class MessagingService:
    """Service layer for Kafka messaging operations"""
    
    @staticmethod
    def send_url_collection(url: str, portal_id: str, metadata: Dict[str, Any] = None) -> bool:
        """Send a URL collection message"""
        message = {
            'url': url,
            'portal_id': portal_id,
            'metadata': metadata or {},
            'timestamp': str(datetime.now().isoformat()),
            'type': 'url_collection'
        }
        
        return KafkaClientManager.send_message('urls', message, key=url)
    
    @staticmethod
    def send_content(content: str, metadata: Dict[str, Any] = None) -> bool:
        """Send a content message"""
        message = {
            'content': content,
            'metadata': metadata or {},
            'timestamp': str(datetime.now().isoformat()),
            'type': 'content'
        }
        
        return KafkaClientManager.send_message('contents', message, key=content)
    
    # Not implemented
    @staticmethod
    def send_notification(notification_type: str, recipient: str, content: Dict[str, Any]) -> bool:
        """Send a notification message"""
        message = {
            'type': notification_type,
            'recipient': recipient,
            'content': content,
            'timestamp': str(datetime.now().isoformat()),
            'message_type': 'notification'
        }
        
        return KafkaClientManager.send_message('notifications', message, key=recipient)
    
    @staticmethod
    def start_urls_consumer(group_id: str = 'urls_consumer_group', topics: List[str] = None):
        """Start consumer for URL collection messages from multiple topics"""
        if topics is None:
            # Default topics for URL collection
            topics = ['urls', 'scraping_results', 'crawler_results', 'discovered_urls']
        
        for topic in topics:
            handler = create_message_handler(topic, 'urls')
            KafkaClientManager.start_consumer(topic, group_id, handler.handle_message)
            logger.info(f"Started URL consumer for topic: {topic}")
    
    @staticmethod
    def start_contents_consumer(group_id: str = 'contents_consumer_group'):
        """Start consumer for content messages"""
        handler = create_message_handler('contents', 'contents')
        KafkaClientManager.start_consumer('contents', group_id, handler.handle_message)
    
    @staticmethod
    def start_notifications_consumer(group_id: str = 'notifications_consumer_group'):
        """Start consumer for notifications"""
        handler = create_message_handler('notifications', 'notifications')
        KafkaClientManager.start_consumer('notifications', group_id, handler.handle_message)
    
    @staticmethod
    def start_all_consumers():
        """Start all default consumers"""
        MessagingService.start_urls_consumer()
        MessagingService.start_contents_consumer()
        MessagingService.start_notifications_consumer()
    
    @staticmethod
    def stop_all_consumers():
        """Stop all consumers"""
        KafkaClientManager.stop_all_consumers()
    
    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Get messaging service status"""
        return KafkaClientManager.get_status()


class UrlCollectionService:
    """Service for URL collection messaging operations"""
    
    @staticmethod
    def collect_urls_from_portal(portal_id: str, urls: List[str], 
                                crawler_config_id: str = None, task_id: str = None,
                                source: str = 'manual', priority: str = 'normal') -> bool:
        """Collect multiple URLs from a portal"""
        success_count = 0
        total_count = len(urls)
        
        for url in urls:
            metadata = {
                'source': source,
                'priority': priority,
                'batch_size': total_count,
                'batch_position': success_count + 1
            }
            
            if crawler_config_id:
                metadata['crawler_config_id'] = crawler_config_id
            
            if task_id:
                metadata['task_id'] = task_id
            
            success = MessagingService.send_url_collection(url, portal_id, metadata)
            if success:
                success_count += 1
                logger.info(f"URL collection message sent: {url}")
            else:
                logger.error(f"Failed to send URL collection message: {url}")
        
        logger.info(f"URL collection completed: {success_count}/{total_count} successful")
        return success_count == total_count
    
    @staticmethod
    def collect_single_url(url: str, portal_id: str, 
                          crawler_config_id: str = None, task_id: str = None,
                          source: str = 'manual', priority: str = 'normal') -> bool:
        """Collect a single URL from a portal"""
        metadata = {
            'source': source,
            'priority': priority
        }
        
        if crawler_config_id:
            metadata['crawler_config_id'] = crawler_config_id
        
        if task_id:
            metadata['task_id'] = task_id
        
        success = MessagingService.send_url_collection(url, portal_id, metadata)
        
        if success:
            logger.info(f"Single URL collection message sent: {url}")
        else:
            logger.error(f"Failed to send single URL collection message: {url}")
        
        return success
    
    @staticmethod
    def collect_urls_with_status(urls: List[str], portal_id: str, status: str = 'pending',
                                crawler_config_id: str = None, task_id: str = None,
                                source: str = 'manual', priority: str = 'normal') -> bool:
        """Collect URLs with a specific initial status"""
        success_count = 0
        total_count = len(urls)
        
        for url in urls:
            metadata = {
                'source': source,
                'priority': priority,
                'status': status,
                'batch_size': total_count,
                'batch_position': success_count + 1
            }
            
            if crawler_config_id:
                metadata['crawler_config_id'] = crawler_config_id
            
            if task_id:
                metadata['task_id'] = task_id
            
            success = MessagingService.send_url_collection(url, portal_id, metadata)
            if success:
                success_count += 1
                logger.info(f"URL collection message sent with status '{status}': {url}")
            else:
                logger.error(f"Failed to send URL collection message: {url}")
        
        logger.info(f"URL collection with status '{status}' completed: {success_count}/{total_count} successful")
        return success_count == total_count


class ScrapyIntegrationService:
    """Service for integrating with Scrapy pipeline output"""
    
    @staticmethod
    def start_scrapy_url_consumer(group_id: str = 'scrapy_url_consumer_group'):
        """Start consumer specifically for Scrapy pipeline URL messages"""
        # Topics that Scrapy might use for URL discovery
        scrapy_topics = [
            'scraping_results',      # General scraping results
            'discovered_urls',       # URLs discovered during crawling
            'crawler_results',       # Crawler output
            'spider_output',         # Spider output
            'url_discovery',         # URL discovery results
            'urls'                   # Default URL topic
        ]
        
        for topic in scrapy_topics:
            handler = create_message_handler(topic, 'urls')
            KafkaClientManager.start_consumer(topic, group_id, handler.handle_message)
            logger.info(f"Started Scrapy URL consumer for topic: {topic}")
    
    @staticmethod
    def send_scrapy_url_discovery(url: str, portal_id: str, spider_name: str = None,
                                crawler_config_id: str = None, task_id: str = None,
                                metadata: Dict[str, Any] = None) -> bool:
        """Send URL discovery message in Scrapy-compatible format"""
        if metadata is None:
            metadata = {}
        
        # Add Scrapy-specific metadata
        metadata.update({
            'spider_name': spider_name,
            'crawler_config_id': crawler_config_id,
            'task_id': task_id,
            'source': 'scrapy_discovery',
            'discovery_method': 'spider_crawl',
            'timestamp': str(datetime.now().isoformat())
        })
        
        # Create Scrapy-compatible message structure
        message = {
            'url': url,
            'portal_id': portal_id,
            'meta': metadata,
            'kafka.topic': 'discovered_urls',
            'kafka.key': url,
            'type': 'url_discovery'
        }
        
        # Send to multiple topics for compatibility
        success = KafkaClientManager.send_message('discovered_urls', message, key=url)
        if success:
            logger.info(f"Scrapy URL discovery message sent: {url}")
        else:
            logger.error(f"Failed to send Scrapy URL discovery message: {url}")
        
        return success
    
    @staticmethod
    def send_scrapy_crawler_result(url: str, portal_id: str, spider_name: str,
                                 crawler_config_id: str = None, task_id: str = None,
                                 additional_data: Dict[str, Any] = None) -> bool:
        """Send crawler result message in Scrapy-compatible format"""
        if additional_data is None:
            additional_data = {}
        
        # Create Scrapy-compatible message structure
        message = {
            'url': url,
            'portal_id': portal_id,
            'spider_name': spider_name,
            'crawler_config_id': crawler_config_id,
            'task_id': task_id,
            'meta': {
                'source': 'scrapy_crawler',
                'crawler_type': 'generic_crawler',
                'timestamp': str(datetime.now().isoformat()),
                **additional_data
            },
            'kafka.topic': 'crawler_results',
            'kafka.key': url
        }
        
        success = KafkaClientManager.send_message('crawler_results', message, key=url)
        if success:
            logger.info(f"Scrapy crawler result message sent: {url}")
        else:
            logger.error(f"Failed to send Scrapy crawler result message: {url}")
        
        return success


class ContentService:
    """Service for content-related messaging operations"""
    
    @staticmethod
    def send_content_data(content: str, content_type: str = 'html', 
                         metadata: Dict[str, Any] = None) -> bool:
        """Send content data with type information"""
        if metadata is None:
            metadata = {}
        
        metadata['content_type'] = content_type
        metadata['content_length'] = len(content)
        
        return MessagingService.send_content(content, metadata)
    
    @staticmethod
    def send_article_content(title: str, body: str, description: str = None,
                           metadata: Dict[str, Any] = None) -> bool:
        """Send article content in structured format"""
        if metadata is None:
            metadata = {}
        
        content_data = {
            'title': title,
            'body': body,
            'description': description,
            'type': 'article'
        }
        
        metadata['content_type'] = 'article'
        metadata['title_length'] = len(title)
        metadata['body_length'] = len(body)
        
        return MessagingService.send_content(str(content_data), metadata)





