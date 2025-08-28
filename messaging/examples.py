from messaging.services import MessagingService, UrlCollectionService, ContentService
from messaging.kafka_client import KafkaClientManager
import logging

logger = logging.getLogger(__name__)


def example_url_collection():
    """Example: How to use the URL collection service"""
    
    # 1. Collect a single URL
    success = UrlCollectionService.collect_single_url(
        url="https://example.com/news/article1",
        portal_id="portal_123",
        source="manual",
        priority="high"
    )
    
    if success:
        logger.info("Single URL collection message sent successfully")
    else:
        logger.error("Failed to send single URL collection message")
    
    # 2. Collect multiple URLs from a portal
    urls = [
        "https://example.com/news/article1",
        "https://example.com/news/article2",
        "https://example.com/news/article3",
        "https://example.com/news/article4"
    ]
    
    success = UrlCollectionService.collect_urls_from_portal(
        portal_id="portal_123",
        urls=urls,
        crawler_config_id="crawler_config_456",
        task_id="task_789",
        source="crawler",
        priority="normal"
    )
    
    if success:
        logger.info("Batch URL collection completed successfully")
    else:
        logger.error("Batch URL collection failed")
    
    # 3. Collect URLs with specific status
    success = UrlCollectionService.collect_urls_with_status(
        portal_id="portal_123",
        urls=urls[:2],
        status="running",
        crawler_config_id="crawler_config_456",
        source="scheduler",
        priority="low"
    )
    
    if success:
        logger.info("URL collection with status completed successfully")
    else:
        logger.error("URL collection with status failed")


def example_content_processing():
    """Example: How to use the content service"""
    
    # 1. Send content data
    success = ContentService.send_content_data(
        content="<html><body>Article content...</body></html>",
        content_type="html",
        metadata={
            "source_url": "https://example.com/article1",
            "portal_id": "portal_123"
        }
    )
    
    if success:
        logger.info("Content data sent successfully")
    else:
        logger.error("Failed to send content data")
    
    # 2. Send article content
    success = ContentService.send_article_content(
        title="Breaking News: Important Event",
        body="This is the article body with detailed information...",
        description="A brief description of the article",
        metadata={
            "author": "John Doe",
            "category": "politics",
            "portal_id": "portal_123"
        }
    )
    
    if success:
        logger.info("Article content sent successfully")
    else:
        logger.error("Failed to send article content")


def example_custom_message_handler():
    """Example: How to create custom message handlers"""
    from messaging.message_handlers import BaseMessageHandler
    
    class CustomUrlHandler(BaseMessageHandler):
        def handle_message(self, message):
            """Custom handler for URL collection with additional logic"""
            try:
                url = message.get('url')
                portal_id = message.get('portal_id')
                
                # Your custom processing logic here
                logger.info(f"Custom processing for URL: {url}")
                
                # Example: Additional validation
                if not self._validate_url(url):
                    logger.warning(f"Invalid URL format: {url}")
                    return False
                
                # Example: Rate limiting
                if not self._check_rate_limit(portal_id):
                    logger.warning(f"Rate limit exceeded for portal: {portal_id}")
                    return False
                
                # Call the original handler
                from messaging.message_handlers import UrlHandler
                original_handler = UrlHandler(self.topic)
                return original_handler.handle_message(message)
                
            except Exception as e:
                logger.error(f"Error in custom handler: {e}")
                return False
        
        def _validate_url(self, url: str) -> bool:
            """Custom URL validation"""
            return url.startswith('http') and len(url) > 10
        
        def _check_rate_limit(self, portal_id: str) -> bool:
            """Custom rate limiting logic"""
            # Implement your rate limiting logic here
            return True
    
    # Use the custom handler
    handler = CustomUrlHandler('custom_urls_topic')
    KafkaClientManager.start_consumer(
        'custom_urls_topic',
        'custom_consumer_group',
        handler.handle_message
    )


def example_monitoring_and_metrics():
    """Example: How to monitor URL collection operations"""
    
    # 1. Check service status
    status = MessagingService.get_status()
    logger.info(f"Messaging service status: {status}")
    
    # 2. Monitor URL consumer health
    if 'urls' in status['consumers_running']:
        logger.info("URL collection consumer is running")
    else:
        logger.warning("URL collection consumer is not running")
    
    # 3. Health check function
    def url_collection_health_check():
        """Perform health check of URL collection service"""
        try:
            status = MessagingService.get_status()
            
            # Check if URL collection is healthy
            is_healthy = (
                status['running'] and
                status['producer_connected'] and
                'urls' in status['consumers_running']
            )
            
            if is_healthy:
                logger.info("URL collection service is healthy")
                return True
            else:
                logger.error("URL collection service is unhealthy")
                return False
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    # Run health check
    url_collection_health_check()


def example_integration_with_existing_scraper():
    """Example: How to integrate with your existing scraper"""
    
    # 1. When your scraper finds new URLs, send them via Kafka
    def on_url_discovered(url: str, portal_id: str, crawler_config_id: str = None):
        """Callback when scraper discovers new URLs"""
        success = UrlCollectionService.collect_single_url(
            url=url,
            portal_id=portal_id,
            crawler_config_id=crawler_config_id,
            source="scraper_discovery",
            priority="normal"
        )
        
        if success:
            logger.info(f"URL discovered and queued: {url}")
        else:
            logger.error(f"Failed to queue discovered URL: {url}")
    
    # 2. When scraping completes, update URL status
    def on_scraping_complete(url: str, portal_id: str, success: bool):
        """Callback when scraping completes"""
        status = "completed" if success else "failed"
        
        success = UrlCollectionService.collect_urls_with_status(
            portal_id=portal_id,
            urls=[url],
            status=status,
            source="scraper_completion"
        )
        
        if success:
            logger.info(f"URL status updated to {status}: {url}")
        else:
            logger.error(f"Failed to update URL status: {url}")
    
    # 3. Example usage in your scraper
    # This would be called from your existing scraper code
    on_url_discovered(
        url="https://example.com/news/article1",
        portal_id="portal_123",
        crawler_config_id="crawler_config_456"
    )


if __name__ == "__main__":
    # Example usage
    logger.info("Running messaging app examples...")
    
    # Initialize the messaging service
    MessagingService.start_urls_consumer()  # Start only URL consumer for this example
    
    # Run examples
    example_url_collection()
    example_content_processing()
    example_custom_message_handler()
    example_monitoring_and_metrics()
    example_integration_with_existing_scraper()
    
    logger.info("Examples completed!")
