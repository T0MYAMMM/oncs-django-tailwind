#!/usr/bin/env python3
"""
Test script for URL collection functionality.
This script demonstrates how to send URL collection messages and test the consumer.
"""

import os
import sys
import django
import logging
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from messaging.services import UrlCollectionService, MessagingService
from messaging.kafka_client import KafkaClientManager
from apps.common.models import NewsPortal, NewsArticleRawUrl

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_portal():
    """Create a test portal if it doesn't exist"""
    try:
        portal, created = NewsPortal.objects.get_or_create(
            domain='test-example.com',
            defaults={
                'name': 'Test Example Portal',
                'news_scope': 'national',
                'country': 'ID'
            }
        )
        
        if created:
            logger.info(f"Created test portal: {portal.name} (ID: {portal.id})")
        else:
            logger.info(f"Using existing test portal: {portal.name} (ID: {portal.id})")
        
        return portal
        
    except Exception as e:
        logger.error(f"Error creating test portal: {e}")
        return None


def test_single_url_collection(portal_id: str):
    """Test single URL collection"""
    logger.info("Testing single URL collection...")
    
    url = "https://test-example.com/news/test-article-1"
    
    success = UrlCollectionService.collect_single_url(
        url=url,
        portal_id=portal_id,
        source="test_script",
        priority="high"
    )
    
    if success:
        logger.info(f"✅ Single URL collection successful: {url}")
    else:
        logger.error(f"❌ Single URL collection failed: {url}")
    
    return success


def test_batch_url_collection(portal_id: str):
    """Test batch URL collection"""
    logger.info("Testing batch URL collection...")
    
    urls = [
        "https://test-example.com/news/test-article-2",
        "https://test-example.com/news/test-article-3",
        "https://test-example.com/news/test-article-4",
        "https://test-example.com/news/test-article-5"
    ]
    
    success = UrlCollectionService.collect_urls_from_portal(
        portal_id=portal_id,
        urls=urls,
        source="test_script_batch",
        priority="normal"
    )
    
    if success:
        logger.info(f"✅ Batch URL collection successful: {len(urls)} URLs")
    else:
        logger.error(f"❌ Batch URL collection failed")
    
    return success


def test_url_collection_with_metadata(portal_id: str):
    """Test URL collection with rich metadata"""
    logger.info("Testing URL collection with metadata...")
    
    url = "https://test-example.com/news/test-article-metadata"
    
    metadata = {
        'source': 'test_script_metadata',
        'priority': 'high',
        'status': 'pending',
        'crawler_config_id': 'test_crawler_001',
        'task_id': 'test_task_001',
        'batch_size': 1,
        'batch_position': 1,
        'test_timestamp': datetime.now().isoformat(),
        'test_flag': True
    }
    
    success = UrlCollectionService.collect_urls_with_status(
        portal_id=portal_id,
        urls=[url],
        status='pending',
        crawler_config_id='test_crawler_001',
        task_id='test_task_001',
        source='test_script_metadata',
        priority='high'
    )
    
    if success:
        logger.info(f"✅ URL collection with metadata successful: {url}")
    else:
        logger.error(f"❌ URL collection with metadata failed: {url}")
    
    return success


def check_database_results():
    """Check what was saved to the database"""
    logger.info("Checking database results...")
    
    try:
        # Count total URLs
        total_urls = NewsArticleRawUrl.objects.count()
        logger.info(f"Total URLs in database: {total_urls}")
        
        # Count URLs by status
        status_counts = {}
        for status in ['pending', 'running', 'completed', 'failed']:
            count = NewsArticleRawUrl.objects.filter(status=status).count()
            status_counts[status] = count
        
        logger.info("URLs by status:")
        for status, count in status_counts.items():
            logger.info(f"  {status}: {count}")
        
        # Show recent URLs
        recent_urls = NewsArticleRawUrl.objects.order_by('-created_at')[:5]
        logger.info("Recent URLs:")
        for url_obj in recent_urls:
            logger.info(f"  {url_obj.url} (Status: {url_obj.status}, Portal: {url_obj.portal.name})")
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking database results: {e}")
        return False


def test_consumer_startup():
    """Test starting the URL consumer"""
    logger.info("Testing consumer startup...")
    
    try:
        # Start the URL consumer
        MessagingService.start_urls_consumer('test_group')
        
        # Check status
        status = MessagingService.get_status()
        logger.info(f"Consumer status: {status}")
        
        if 'urls' in status['consumers_running']:
            logger.info("✅ URL consumer started successfully")
            return True
        else:
            logger.error("❌ URL consumer failed to start")
            return False
            
    except Exception as e:
        logger.error(f"Error starting consumer: {e}")
        return False


def cleanup_test_data():
    """Clean up test data"""
    logger.info("Cleaning up test data...")
    
    try:
        # Remove test URLs
        test_urls = NewsArticleRawUrl.objects.filter(
            url__contains='test-example.com'
        )
        count = test_urls.count()
        test_urls.delete()
        
        logger.info(f"Cleaned up {count} test URLs")
        
        # Remove test portal if it was created for testing
        test_portals = NewsPortal.objects.filter(
            domain='test-example.com'
        )
        if test_portals.exists():
            test_portals.delete()
            logger.info("Cleaned up test portal")
        
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning up test data: {e}")
        return False


def main():
    """Main test function"""
    logger.info("🚀 Starting URL Collection Test Suite")
    
    try:
        # Create test portal
        portal = create_test_portal()
        if not portal:
            logger.error("Failed to create test portal. Exiting.")
            return False
        
        # Test consumer startup
        if not test_consumer_startup():
            logger.error("Consumer startup test failed. Exiting.")
            return False
        
        # Wait a moment for consumer to initialize
        import time
        time.sleep(2)
        
        # Run tests
        test_results = []
        
        test_results.append(("Single URL Collection", test_single_url_collection(portal.id)))
        test_results.append(("Batch URL Collection", test_batch_url_collection(portal.id)))
        test_results.append(("URL Collection with Metadata", test_url_collection_with_metadata(portal.id)))
        
        # Wait for messages to be processed
        logger.info("Waiting for messages to be processed...")
        time.sleep(5)
        
        # Check database results
        test_results.append(("Database Check", check_database_results()))
        
        # Print test summary
        logger.info("\n" + "="*50)
        logger.info("TEST SUMMARY")
        logger.info("="*50)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{test_name}: {status}")
            if result:
                passed += 1
        
        logger.info(f"\nResults: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All tests passed!")
        else:
            logger.warning(f"⚠️  {total - passed} tests failed")
        
        # Cleanup
        cleanup_test_data()
        
        return passed == total
        
    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        return False
    
    finally:
        # Stop consumers
        try:
            MessagingService.stop_all_consumers()
            logger.info("Stopped all consumers")
        except Exception as e:
            logger.error(f"Error stopping consumers: {e}")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
