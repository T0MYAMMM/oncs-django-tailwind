import logging
import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from django.conf import settings
from django.db import transaction
from apps.common.models import NewsArticleRawUrl, NewsPortal, CrawlerConfig, CrawlerTask

logger = logging.getLogger(__name__)


class BaseMessageHandler(ABC):
    """Base class for Kafka message handlers"""
    
    def __init__(self, topic: str):
        self.topic = topic
    
    @abstractmethod
    def handle_message(self, message: Dict[str, Any]) -> bool:
        """Handle a Kafka message"""
        pass
    
    def log_message(self, message: Dict[str, Any], success: bool = True):
        """Log message processing result"""
        if success:
            logger.info(f"Successfully processed message from {self.topic}: {message.get('id', 'unknown')}")
        else:
            logger.error(f"Failed to process message from {self.topic}: {message.get('id', 'unknown')}")


class UrlHandler(BaseMessageHandler):
    """Handler for URL collection messages from Scrapy pipeline - saves to NewsArticleRawUrl"""
    
    def handle_message(self, message: Dict[str, Any]) -> bool:
        try:
            # Handle both Scrapy pipeline format and direct URL collection format
            if self._is_scrapy_message(message):
                return self._handle_scrapy_message(message)
            else:
                return self._handle_direct_url_message(message)
                
        except Exception as e:
            logger.error(f"Error handling URL collection message: {e}")
            self.log_message(message, success=False)
            return False
    
    def _is_scrapy_message(self, message: Dict[str, Any]) -> bool:
        """Check if this is a Scrapy pipeline message"""
        # Scrapy messages typically have encoded content and metadata structure
        return (
            'meta' in message or 
            'kafka.topic' in message or
            'kafka.key' in message or
            isinstance(message.get('value'), bytes) or
            'url' in message and 'title' in message  # Typical Scrapy item fields
        )
    
    def _handle_scrapy_message(self, message: Dict[str, Any]) -> bool:
        """Handle message from Scrapy pipeline"""
        try:
            # Extract URL from Scrapy item
            url = self._extract_url_from_scrapy_item(message)
            if not url:
                logger.warning("No URL found in Scrapy message")
                return False
            
            # Extract portal information from metadata
            portal_id = self._extract_portal_id_from_scrapy_meta(message)
            if not portal_id:
                logger.warning(f"No portal_id found in Scrapy message for URL: {url}")
                return False
            
            # Extract additional metadata
            metadata = self._extract_metadata_from_scrapy_meta(message)
            
            logger.info(f"Processing Scrapy URL collection message for: {url}")
            
            # Process the URL collection
            success = self._process_url_collection(url, portal_id, metadata)
            
            if success:
                self.log_message(message, success=True)
                logger.info(f"Successfully saved Scrapy URL: {url}")
            else:
                self.log_message(message, success=False)
                logger.error(f"Failed to save Scrapy URL: {url}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error handling Scrapy message: {e}")
            return False
    
    def _handle_direct_url_message(self, message: Dict[str, Any]) -> bool:
        """Handle direct URL collection message (original format)"""
        try:
            # Extract required fields
            url = message.get('url')
            portal_id = message.get('portal_id')
            metadata = message.get('metadata', {})
            
            if not url or not portal_id:
                logger.warning(f"Invalid direct URL message: missing url or portal_id")
                return False
            
            logger.info(f"Processing direct URL collection message for: {url}")
            
            # Process the URL collection
            success = self._process_url_collection(url, portal_id, metadata)
            
            if success:
                self.log_message(message, success=True)
                logger.info(f"Successfully saved direct URL: {url}")
            else:
                self.log_message(message, success=False)
                logger.error(f"Failed to save direct URL: {url}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error handling direct URL message: {e}")
            return False
    
    def _extract_url_from_scrapy_item(self, message: Dict[str, Any]) -> Optional[str]:
        """Extract URL from Scrapy item message"""
        # Try different possible locations for URL
        url = None
        
        # Direct field access
        if 'url' in message:
            url = message['url']
        elif 'link' in message:
            url = message['link']
        elif 'href' in message:
            url = message['href']
        
        # Check if URL is in encoded value (Scrapy pipeline format)
        if not url and 'value' in message:
            try:
                # Try to decode the encoded value
                if isinstance(message['value'], bytes):
                    decoded_value = message['value'].decode('utf-8')
                    # Try to parse as JSON
                    try:
                        parsed_value = json.loads(decoded_value)
                        if isinstance(parsed_value, dict):
                            url = parsed_value.get('url') or parsed_value.get('link') or parsed_value.get('href')
                    except json.JSONDecodeError:
                        # Not JSON, try to extract URL from text
                        import re
                        url_match = re.search(r'https?://[^\s<>"\']+', decoded_value)
                        if url_match:
                            url = url_match.group(0)
            except Exception as e:
                logger.warning(f"Error decoding Scrapy value: {e}")
        
        return url
    
    def _extract_portal_id_from_scrapy_meta(self, message: Dict[str, Any]) -> Optional[str]:
        """Extract portal_id from Scrapy message metadata"""
        portal_id = None
        
        # Check direct metadata field
        if 'meta' in message and isinstance(message['meta'], dict):
            meta = message['meta']
            portal_id = meta.get('portal_id') or meta.get('portal') or meta.get('source_id')
        
        # Check if portal_id is in the main message
        if not portal_id:
            portal_id = message.get('portal_id') or message.get('portal') or message.get('source_id')
        
        # Check if we can derive portal_id from domain
        if not portal_id and 'url' in message:
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(message['url'])
                domain = parsed_url.netloc
                
                # Try to find portal by domain
                try:
                    portal = NewsPortal.objects.filter(domain=domain).first()
                    if portal:
                        portal_id = str(portal.id)
                        logger.info(f"Derived portal_id {portal_id} from domain {domain}")
                except Exception as e:
                    logger.warning(f"Error looking up portal by domain {domain}: {e}")
            except Exception as e:
                logger.warning(f"Error parsing URL for domain extraction: {e}")
        
        return portal_id
    
    def _extract_metadata_from_scrapy_meta(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from Scrapy message"""
        metadata = {}
        
        # Extract from meta field
        if 'meta' in message and isinstance(message['meta'], dict):
            meta = message['meta']
            
            # Map Scrapy metadata fields to our expected format
            metadata_mapping = {
                'crawler_config_id': ['crawler_config_id', 'crawler_config', 'config_id'],
                'task_id': ['task_id', 'task', 'job_id', 'scrapyd_job_id'],
                'spider_name': ['spider_name', 'spider', 'crawler_name'],
                'source': ['source', 'origin', 'discovery_method'],
                'priority': ['priority', 'importance'],
                'status': ['status', 'item_status'],
                'batch_id': ['batch_id', 'batch', 'group_id'],
                'timestamp': ['timestamp', 'created_at', 'discovered_at']
            }
            
            for target_key, source_keys in metadata_mapping.items():
                for source_key in source_keys:
                    if source_key in meta:
                        metadata[target_key] = meta[source_key]
                        break
            
            # Copy any other metadata fields
            for key, value in meta.items():
                if key not in [k for keys in metadata_mapping.values() for k in keys]:
                    metadata[f"scrapy_{key}"] = value
        
        # Extract from main message fields
        if 'spider_name' in message:
            metadata['spider_name'] = message['spider_name']
        if 'crawler_config_id' in message:
            metadata['crawler_config_id'] = message['crawler_config_id']
        if 'task_id' in message:
            metadata['task_id'] = message['task_id']
        
        # Add message type indicator
        metadata['message_source'] = 'scrapy_pipeline'
        metadata['processed_at'] = str(datetime.now().isoformat())
        
        return metadata
    
    def _process_url_collection(self, url: str, portal_id: str, metadata: Dict[str, Any]) -> bool:
        """Process URL collection and save to database"""
        try:
            with transaction.atomic():
                # Get or create the portal
                try:
                    portal = NewsPortal.objects.get(id=portal_id)
                except NewsPortal.DoesNotExist:
                    logger.error(f"Portal with ID {portal_id} not found")
                    return False
                
                # Check if URL already exists
                if NewsArticleRawUrl.objects.filter(url=url).exists():
                    logger.info(f"URL already exists: {url}")
                    return True  # Consider this a success
                
                # Create new NewsArticleRawUrl
                url_obj = NewsArticleRawUrl.objects.create(
                    url=url,
                    portal=portal,
                    status='pending'  # Default status
                )
                
                # Update status based on metadata if provided
                if 'status' in metadata:
                    url_obj.status = metadata['status']
                    url_obj.save(update_fields=['status'])
                
                # Log additional metadata
                logger.info(f"Created NewsArticleRawUrl: {url_obj.id} for portal: {portal.name}")
                
                # Process additional metadata if available
                self._process_additional_metadata(url_obj, metadata)
                
                return True
                
        except Exception as e:
            logger.error(f"Error processing URL collection: {e}")
            return False
    
    def _process_additional_metadata(self, url_obj: NewsArticleRawUrl, metadata: Dict[str, Any]):
        """Process additional metadata from the message"""
        try:
            # Log crawler config information if available
            if 'crawler_config_id' in metadata:
                try:
                    crawler_config = CrawlerConfig.objects.get(id=metadata['crawler_config_id'])
                    logger.info(f"URL associated with crawler config: {crawler_config.name}")
                except CrawlerConfig.DoesNotExist:
                    logger.warning(f"Crawler config {metadata['crawler_config_id']} not found")
            
            # Log task information if available
            if 'task_id' in metadata:
                try:
                    task = CrawlerTask.objects.get(id=metadata['task_id'])
                    logger.info(f"URL associated with crawler task: {task.id} - {task.status}")
                except CrawlerTask.DoesNotExist:
                    logger.warning(f"Crawler task {metadata['task_id']} not found")
            
            # Log other relevant metadata
            if 'source' in metadata:
                logger.info(f"URL source: {metadata['source']}")
            
            if 'priority' in metadata:
                logger.info(f"URL priority: {metadata['priority']}")
            
            if 'spider_name' in metadata:
                logger.info(f"Spider name: {metadata['spider_name']}")
                
        except Exception as e:
            logger.warning(f"Error processing additional metadata: {e}")


class ContentHandler(BaseMessageHandler):
    """Handler for content messages"""
    
    def handle_message(self, message: Dict[str, Any]) -> bool:
        try:
            content = message.get('content')
            metadata = message.get('metadata', {})
            
            if not content:
                logger.warning(f"Invalid content message: missing content")
                return False
            
            logger.info(f"Processing content message")
            
            # Process the content message
            # This is where you'd implement your content processing logic
            # For example, save to database, trigger notifications, etc.
            
            # Example: Save to database (implement based on your models)
            # self._save_content(content, metadata)
            
            # Example: Trigger notifications
            # self._notify_stakeholders(content, metadata)
            
            self.log_message(message, success=True)
            return True
            
        except Exception as e:
            logger.error(f"Error handling content message: {e}")
            self.log_message(message, success=False)
            return False


class NotificationHandler(BaseMessageHandler):
    """Handler for notification messages"""
    
    def handle_message(self, message: Dict[str, Any]) -> bool:
        try:
            notification_type = message.get('type')
            recipient = message.get('recipient')
            content = message.get('content')
            
            if not all([notification_type, recipient, content]):
                logger.warning(f"Invalid notification message: missing required fields")
                return False
            
            logger.info(f"Processing {notification_type} notification for {recipient}")
            
            # Send notification based on type
            if notification_type == 'email':
                self._send_email_notification(recipient, content)
            elif notification_type == 'sms':
                self._send_sms_notification(recipient, content)
            elif notification_type == 'webhook':
                self._send_webhook_notification(recipient, content)
            else:
                logger.warning(f"Unknown notification type: {notification_type}")
                return False
            
            self.log_message(message, success=True)
            return True
            
        except Exception as e:
            logger.error(f"Error handling notification message: {e}")
            self.log_message(message, success=False)
            return False
    
    def _send_email_notification(self, recipient: str, content: Dict[str, Any]):
        """Send email notification"""
        # Implement email sending logic
        logger.info(f"Sending email notification to {recipient}")
    
    def _send_sms_notification(self, recipient: str, content: Dict[str, Any]):
        """Send SMS notification"""
        # Implement SMS sending logic
        logger.info(f"Sending SMS notification to {recipient}")
    
    def _send_webhook_notification(self, recipient: str, content: Dict[str, Any]):
        """Send webhook notification"""
        # Implement webhook sending logic
        logger.info(f"Sending webhook notification to {recipient}")


# Factory function to create handlers
def create_message_handler(topic: str, handler_type: str = None) -> BaseMessageHandler:
    """Create a message handler based on topic and type"""
    
    # Map topics to handler types
    topic_handler_mapping = {
        'urls': UrlHandler,
        'contents': ContentHandler,
        'notifications': NotificationHandler,
    }
    
    # Determine handler type from topic if not specified
    if not handler_type:
        for topic_pattern, handler_class in topic_handler_mapping.items():
            if topic_pattern in topic:
                handler_type = topic_pattern
                break
    
    # Create appropriate handler
    if handler_type == 'urls':
        return UrlHandler(topic)
    elif handler_type == 'contents':
        return ContentHandler(topic)
    elif handler_type == 'notifications':
        return NotificationHandler(topic)
    else:
        # Default handler for unknown topics
        logger.warning(f"No specific handler found for topic {topic}, using base handler")
        return BaseMessageHandler(topic)


# Import datetime at the top
from datetime import datetime
