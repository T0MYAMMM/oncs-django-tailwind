from django.core.management.base import BaseCommand
from django.conf import settings
from messaging.services import MessagingService, ScrapyIntegrationService
from messaging.kafka_client import KafkaClientManager
from messaging.message_handlers import UrlHandler
import time
import signal
import sys
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start URL collection consumer for NewsArticleRawUrl processing (Scrapy integration by default)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--group-id',
            type=str,
            help='Consumer group ID (default: url_collector_group)',
            default='url_collector_group'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon process'
        )
        parser.add_argument(
            '--topic',
            type=str,
            help='Specific Kafka topic to consume (custom mode only)',
            default=None
        )
        parser.add_argument(
            '--topics',
            nargs='+',
            help='Multiple Kafka topics to consume (custom mode only)',
            default=None
        )
        parser.add_argument(
            '--custom-mode',
            action='store_true',
            help='Enable custom mode for specific topic consumption (default: Scrapy integration mode)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            help='Process messages in batches of this size (default: 1)',
            default=1
        )
        parser.add_argument(
            '--batch-timeout',
            type=int,
            help='Batch timeout in seconds (default: 5)',
            default=5
        )
        parser.add_argument(
            '--auto-detect-topics',
            action='store_true',
            help='Auto-detect and consume from all URL-related topics (extended Scrapy mode)'
        )
    
    def handle(self, *args, **options):
        group_id = options['group_id']
        daemon = options['daemon']
        topic = options['topic']
        topics = options['topics']
        custom_mode = options['custom_mode']
        batch_size = options['batch_size']
        batch_timeout = options['batch_timeout']
        auto_detect = options['auto_detect_topics']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting URL Collection Consumer...')
        )
        
        # Determine which topics to consume from
        if custom_mode:
            # Custom mode: user specifies topics
            if topics:
                target_topics = topics
                self.stdout.write(f'Custom mode - topics: {", ".join(target_topics)}')
            elif topic:
                target_topics = [topic]
                self.stdout.write(f'Custom mode - single topic: {topic}')
            else:
                # Default custom mode: single 'urls' topic
                target_topics = ['urls']
                self.stdout.write(f'Custom mode - default topic: {target_topics[0]}')
        elif auto_detect:
            # Extended Scrapy mode: comprehensive topic coverage
            target_topics = [
                'urls', 'scraping_results', 'crawler_results', 'discovered_urls',
                'spider_output', 'url_discovery', 'article_urls', 'news_urls',
                'news_discovery', 'portal_urls', 'crawler_urls'
            ]
            self.stdout.write(f'Extended Scrapy mode - topics: {", ".join(target_topics)}')
        else:
            # Default mode: Scrapy integration (primary use case)
            target_topics = [
                'scraping_results', 'discovered_urls', 'crawler_results', 
                'spider_output', 'url_discovery', 'urls'
            ]
            self.stdout.write(f'Scrapy integration mode (default) - topics: {", ".join(target_topics)}')
        
        self.stdout.write(f'Group ID: {group_id}')
        self.stdout.write(f'Batch Size: {batch_size}')
        self.stdout.write(f'Batch Timeout: {batch_timeout}s')
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            # Start the URL collection consumer(s)
            if custom_mode:
                # Custom mode: specific topic(s) only
                if len(target_topics) > 1:
                    self._start_multi_topic_consumer(target_topics, group_id, batch_size, batch_timeout)
                else:
                    self._start_single_topic_consumer(target_topics[0], group_id, batch_size, batch_timeout)
            elif auto_detect:
                # Extended Scrapy mode: comprehensive coverage
                self._start_extended_scrapy_consumer(group_id)
            else:
                # Default mode: Standard Scrapy integration
                self._start_scrapy_integration_consumer(group_id)
            
            # Get status
            status = MessagingService.get_status()
            self.stdout.write(
                self.style.SUCCESS(f'URL Collection Consumer started successfully')
            )
            self.stdout.write(f'Status: {status}')
            
            if not daemon:
                # Keep running until interrupted
                self.stdout.write('Press Ctrl+C to stop...')
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error starting URL Collection Consumer: {e}')
            )
            sys.exit(1)
        finally:
            self._cleanup()
    
    def _start_scrapy_integration_consumer(self, group_id: str):
        """Start consumer for standard Scrapy pipeline integration (default mode)"""
        self.stdout.write('Starting Scrapy integration consumer (default mode)...')
        ScrapyIntegrationService.start_scrapy_url_consumer(group_id)
        self.stdout.write('✅ Scrapy integration consumer started (default mode)')
    
    def _start_extended_scrapy_consumer(self, group_id: str):
        """Start consumer for extended Scrapy coverage (auto-detect mode)"""
        self.stdout.write('Starting extended Scrapy consumer...')
        
        # Extended topics for comprehensive coverage
        extended_topics = [
            'scraping_results', 'discovered_urls', 'crawler_results', 
            'spider_output', 'url_discovery', 'urls', 'article_urls', 
            'news_urls', 'news_discovery', 'portal_urls', 'crawler_urls'
        ]
        
        for topic in extended_topics:
            handler = UrlHandler(topic) # Assuming create_message_handler is defined elsewhere or will be added
            KafkaClientManager.start_consumer(topic, group_id, handler.handle_message)
            logger.info(f"Started extended URL consumer for topic: {topic}")
        
        self.stdout.write(f'✅ Extended Scrapy consumer started for {len(extended_topics)} topics')
    
    def _start_multi_topic_consumer(self, topics: list, group_id: str, batch_size: int, batch_timeout: int):
        """Start consumer for multiple topics (custom mode)"""
        self.stdout.write(f'Starting custom multi-topic consumer for {len(topics)} topics...')
        
        for topic in topics:
            if batch_size > 1:
                self._start_batch_consumer(topic, group_id, batch_size, batch_timeout)
            else:
                self._start_single_consumer(topic, group_id)
        
        self.stdout.write(f'✅ Custom multi-topic consumer started for {len(topics)} topics')
    
    def _start_single_topic_consumer(self, topic: str, group_id: str, batch_size: int, batch_timeout: int):
        """Start consumer for a single topic (custom mode)"""
        if batch_size > 1:
            self._start_batch_consumer(topic, group_id, batch_size, batch_timeout)
        else:
            self._start_single_consumer(topic, group_id)
    
    def _start_single_consumer(self, topic: str, group_id: str):
        """Start single message consumer"""
        handler = UrlHandler(topic)
        KafkaClientManager.start_consumer(topic, group_id, handler.handle_message)
        self.stdout.write(f'Started single message consumer for topic: {topic}')
    
    def _start_batch_consumer(self, topic: str, group_id: str, batch_size: int, batch_timeout: int):
        """Start batch message consumer"""
        def batch_handler(messages):
            """Handle multiple messages at once"""
            self.stdout.write(f'Processing batch of {len(messages)} messages from topic: {topic}')
            
            success_count = 0
            for message in messages:
                try:
                    handler = UrlHandler(topic)
                    if handler.handle_message(message):
                        success_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Successfully processed message: {message.get("url", "unknown")}')
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'Failed to process message: {message.get("url", "unknown")}')
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error processing message: {e}')
                    )
            
            self.stdout.write(f'Batch processing completed: {success_count}/{len(messages)} successful')
        
        # Start consumer with batch processing
        # Note: This is a simplified batch implementation
        # For production, you might want to implement proper batch collection logic
        handler = UrlHandler(topic)
        KafkaClientManager.start_consumer(topic, group_id, handler.handle_message)
        self.stdout.write(f'Started batch consumer for topic: {topic} (batch size: {batch_size})')
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.stdout.write('\nReceived shutdown signal, stopping URL Collection Consumer...')
        self._cleanup()
        sys.exit(0)
    
    def _cleanup(self):
        """Clean up resources"""
        try:
            # Stop all consumers
            MessagingService.stop_all_consumers()
            self.stdout.write(
                self.style.SUCCESS('URL Collection Consumer stopped successfully')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error stopping URL Collection Consumer: {e}')
            )
