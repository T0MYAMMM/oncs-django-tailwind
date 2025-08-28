#!/usr/bin/env python3
"""
Example showing how the modified URL consumer integrates with Scrapy generic crawler pipeline.
This demonstrates the compatibility between your existing Scrapy pipeline and the new URL consumer.
"""

from messaging.services import ScrapyIntegrationService, MessagingService
from messaging.kafka_client import KafkaClientManager
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_scrapy_pipeline_integration():
    """
    Example: How your Scrapy pipeline output will be processed by the URL consumer
    """
    
    # 1. Simulate Scrapy pipeline output (what your pipeline actually sends)
    scrapy_message_example_1 = {
        # This is what your Scrapy pipeline sends
        'url': 'https://example.com/news/article1',
        'title': 'Breaking News Article',
        'content': 'Article content here...',
        'meta': {
            'portal_id': 'portal_123',
            'crawler_config_id': 'crawler_config_456',
            'task_id': 'task_789',
            'spider_name': 'news_spider',
            'source': 'crawler_discovery',
            'priority': 'high',
            'status': 'pending'
        },
        'kafka.topic': 'scraping_results',
        'kafka.key': 'https://example.com/news/article1'
    }
    
    scrapy_message_example_2 = {
        # Another example with different structure
        'value': b'{"url": "https://example.com/news/article2", "title": "Second Article"}',  # Encoded bytes
        'meta': {
            'portal_id': 'portal_123',
            'spider_name': 'news_spider',
            'crawler_config_id': 'crawler_config_456'
        },
        'kafka.topic': 'discovered_urls'
    }
    
    scrapy_message_example_3 = {
        # Example with domain-based portal detection
        'url': 'https://newsportal.com/article3',
        'title': 'Third Article',
        'meta': {
            'spider_name': 'news_spider',
            'crawler_config_id': 'crawler_config_456'
            # Note: no portal_id - will be derived from domain
        },
        'kafka.topic': 'crawler_results'
    }
    
    logger.info("=== Scrapy Pipeline Integration Examples ===")
    
    # 2. Show how the URL consumer will process these messages
    logger.info("Example 1: Standard Scrapy message with portal_id")
    logger.info(f"  URL: {scrapy_message_example_1['url']}")
    logger.info(f"  Portal ID: {scrapy_message_example_1['meta']['portal_id']}")
    logger.info(f"  Spider: {scrapy_message_example_1['meta']['spider_name']}")
    
    logger.info("Example 2: Scrapy message with encoded value")
    logger.info(f"  Encoded value: {scrapy_message_example_2['value']}")
    logger.info(f"  Topic: {scrapy_message_example_2['kafka.topic']}")
    
    logger.info("Example 3: Scrapy message with domain-based portal detection")
    logger.info(f"  URL: {scrapy_message_example_3['url']}")
    logger.info(f"  Will auto-detect portal from domain: newsportal.com")
    
    return [scrapy_message_example_1, scrapy_message_example_2, scrapy_message_example_3]


def example_scrapy_url_discovery():
    """
    Example: How to send URL discovery messages from your Scrapy spiders
    """
    
    logger.info("\n=== Scrapy URL Discovery Examples ===")
    
    # 1. Send URL discovery when spider finds new URLs
    success = ScrapyIntegrationService.send_scrapy_url_discovery(
        url="https://example.com/news/article4",
        portal_id="portal_123",
        spider_name="news_spider",
        crawler_config_id="crawler_config_456",
        task_id="task_789",
        metadata={
            'discovery_method': 'link_extraction',
            'parent_url': 'https://example.com/news',
            'link_text': 'Read More',
            'priority': 'normal'
        }
    )
    
    if success:
        logger.info("✅ Scrapy URL discovery message sent successfully")
    else:
        logger.error("❌ Failed to send Scrapy URL discovery message")
    
    # 2. Send crawler results
    success = ScrapyIntegrationService.send_scrapy_crawler_result(
        url="https://example.com/news/article5",
        portal_id="portal_123",
        spider_name="news_spider",
        crawler_config_id="crawler_config_456",
        task_id="task_789",
        additional_data={
            'extracted_links': 15,
            'processing_time': 2.5,
            'content_length': 2048,
            'has_images': True
        }
    )
    
    if success:
        logger.info("✅ Scrapy crawler result message sent successfully")
    else:
        logger.error("❌ Failed to send Scrapy crawler result message")


def example_consumer_startup_modes():
    """
    Example: Different ways to start the URL consumer for Scrapy integration
    """
    
    logger.info("\n=== Consumer Startup Modes ===")
    
    # 1. Default mode: Scrapy integration (primary use case)
    logger.info("Mode 1: Scrapy Integration Mode (DEFAULT)")
    logger.info("  Command: python manage.py url_collector_consumer")
    logger.info("  Topics: scraping_results, discovered_urls, crawler_results, spider_output, url_discovery, urls")
    logger.info("  Use case: Production environment with thousands of Scrapy crawlers")
    
    # 2. Extended Scrapy mode
    logger.info("Mode 2: Extended Scrapy Mode")
    logger.info("  Command: python manage.py url_collector_consumer --auto-detect-topics")
    logger.info("  Topics: urls, scraping_results, crawler_results, discovered_urls, spider_output, url_discovery, article_urls, news_urls, news_discovery, portal_urls, crawler_urls")
    logger.info("  Use case: Maximum coverage for complex Scrapy setups")
    
    # 3. Custom mode (for specific needs)
    logger.info("Mode 3: Custom Mode")
    logger.info("  Command: python manage.py url_collector_consumer --custom-mode --topics scraping_results discovered_urls")
    logger.info("  Topics: Only the specified topics")
    logger.info("  Use case: Specific topic consumption or testing")
    
    # 4. Single topic custom mode
    logger.info("Mode 4: Single Topic Custom Mode")
    logger.info("  Command: python manage.py url_collector_consumer --custom-mode --topic scraping_results")
    logger.info("  Topics: Only the specified topic")
    logger.info("  Use case: Single topic testing or limited consumption")


def example_message_processing_flow():
    """
    Example: Complete message processing flow from Scrapy to database
    """
    
    logger.info("\n=== Message Processing Flow ===")
    
    # 1. Scrapy pipeline sends message
    logger.info("Step 1: Scrapy Pipeline Sends Message")
    logger.info("  Topic: scraping_results")
    logger.info("  Message: URL + metadata")
    
    # 2. URL consumer receives message
    logger.info("Step 2: URL Consumer Receives Message")
    logger.info("  Detects Scrapy format")
    logger.info("  Extracts URL and portal_id")
    logger.info("  Maps metadata fields")
    
    # 3. Database processing
    logger.info("Step 3: Database Processing")
    logger.info("  Creates NewsArticleRawUrl record")
    logger.info("  Links to NewsPortal")
    logger.info("  Stores metadata")
    
    # 4. Result
    logger.info("Step 4: Result")
    logger.info("  URL saved to database")
    logger.info("  Status: pending")
    logger.info("  Ready for content scraping")


def example_scrapy_settings_integration():
    """
    Example: How to configure your Scrapy settings to work with the URL consumer
    """
    
    logger.info("\n=== Scrapy Settings Integration ===")
    
    # 1. Kafka topic configuration
    logger.info("Kafka Topic Configuration:")
    logger.info("  KAFKA_PRODUCER_TOPIC: scraping_results")
    logger.info("  Or use item['meta']['kafka.topic'] for per-item topics")
    
    # 2. Item structure
    logger.info("Item Structure:")
    logger.info("  item['url']: The discovered URL")
    logger.info("  item['meta']['portal_id']: Target portal ID")
    logger.info("  item['meta']['crawler_config_id']: Crawler configuration")
    logger.info("  item['meta']['task_id']: Task identifier")
    logger.info("  item['meta']['spider_name']: Spider name")
    
    # 3. Pipeline configuration
    logger.info("Pipeline Configuration:")
    logger.info("  Enable KafkaPipeline in ITEM_PIPELINES")
    logger.info("  Configure KAFKA_PRODUCER_BROKERS")
    logger.info("  Set KAFKA_PRODUCER_TOPIC")


def example_error_handling():
    """
    Example: How the URL consumer handles different error scenarios
    """
    
    logger.info("\n=== Error Handling Examples ===")
    
    # 1. Missing portal_id
    logger.info("Scenario 1: Missing portal_id")
    logger.info("  Consumer will try to derive from domain")
    logger.info("  Falls back to domain lookup in database")
    logger.info("  Logs warning if portal not found")
    
    # 2. Encoded message format
    logger.info("Scenario 2: Encoded message format")
    logger.info("  Handles both JSON and text encoding")
    logger.info("  Extracts URL from encoded content")
    logger.info("  Graceful fallback for parsing errors")
    
    # 3. Invalid URL format
    logger.info("Scenario 3: Invalid URL format")
    logger.info("  Validates URL structure")
    logger.info("  Logs warning for malformed URLs")
    logger.info("  Continues processing other messages")
    
    # 4. Database errors
    logger.info("Scenario 4: Database errors")
    logger.info("  Uses Django transactions")
    logger.info("  Rollback on errors")
    logger.info("  Logs detailed error information")


def example_production_deployment():
    """
    Example: Production deployment with thousands of Scrapy crawlers
    """
    
    logger.info("\n=== Production Deployment Examples ===")
    
    # 1. Default deployment (recommended for production)
    logger.info("Production Deployment - Default Mode:")
    logger.info("  Command: python manage.py url_collector_consumer")
    logger.info("  Coverage: All standard Scrapy topics")
    logger.info("  Use case: Production environment with thousands of crawlers")
    logger.info("  Resource usage: Optimized for high throughput")
    
    # 2. Extended deployment (for complex setups)
    logger.info("Production Deployment - Extended Mode:")
    logger.info("  Command: python manage.py url_collector_consumer --auto-detect-topics")
    logger.info("  Coverage: Comprehensive topic coverage")
    logger.info("  Use case: Complex Scrapy infrastructure with custom topics")
    logger.info("  Resource usage: Higher memory usage, maximum coverage")
    
    # 3. Custom deployment (for specific needs)
    logger.info("Production Deployment - Custom Mode:")
    logger.info("  Command: python manage.py url_collector_consumer --custom-mode --topics scraping_results")
    logger.info("  Coverage: Specific topics only")
    logger.info("  Use case: Limited scope or testing environments")
    logger.info("  Resource usage: Minimal, focused consumption")


def main():
    """Main function to run all examples"""
    logger.info("🚀 Scrapy Pipeline Integration Examples")
    
    try:
        # Run examples
        example_scrapy_pipeline_integration()
        example_scrapy_url_discovery()
        example_consumer_startup_modes()
        example_message_processing_flow()
        example_scrapy_settings_integration()
        example_error_handling()
        example_production_deployment()
        
        logger.info("\n✅ All examples completed successfully!")
        logger.info("\n📋 Next Steps:")
        logger.info("  1. Start URL consumer (default): python manage.py url_collector_consumer")
        logger.info("  2. For extended coverage: python manage.py url_collector_consumer --auto-detect-topics")
        logger.info("  3. For custom topics: python manage.py url_collector_consumer --custom-mode --topics topic1 topic2")
        logger.info("  4. Configure Scrapy to send to compatible topics")
        logger.info("  5. Ensure portal_id is included in Scrapy item metadata")
        logger.info("  6. Monitor consumer logs for processing status")
        
    except Exception as e:
        logger.error(f"❌ Examples failed with error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Scrapy integration examples completed successfully!")
    else:
        print("\n💥 Scrapy integration examples failed!")
        exit(1)
