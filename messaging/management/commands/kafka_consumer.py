from django.core.management.base import BaseCommand
from django.conf import settings
from messaging.services import MessagingService
import time
import signal
import sys


class Command(BaseCommand):
    help = 'Start Kafka consumers for messaging'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--topics',
            nargs='+',
            help='Specific topics to consume (default: all)',
            default=[]
        )
        parser.add_argument(
            '--group-id',
            type=str,
            help='Consumer group ID (default: auto-generated)',
            default=None
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon process'
        )
        parser.add_argument(
            '--urls-only',
            action='store_true',
            help='Start only URL collection consumer'
        )
        parser.add_argument(
            '--contents-only',
            action='store_true',
            help='Start only content consumer'
        )
    
    def handle(self, *args, **options):
        topics = options['topics']
        group_id = options['group_id']
        daemon = options['daemon']
        urls_only = options['urls_only']
        contents_only = options['contents_only']
        
        self.stdout.write(
            self.style.SUCCESS('Starting Kafka consumers...')
        )
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            if urls_only:
                # Start only URL collection consumer
                self.stdout.write('Starting URL collection consumer only...')
                MessagingService.start_urls_consumer(group_id)
            elif contents_only:
                # Start only content consumer
                self.stdout.write('Starting content consumer only...')
                MessagingService.start_contents_consumer(group_id)
            elif not topics:
                # Start all default consumers
                self.stdout.write('Starting all default consumers...')
                MessagingService.start_all_consumers()
            else:
                # Start specific consumers
                for topic in topics:
                    self.stdout.write(f'Starting consumer for topic: {topic}')
                    if 'url' in topic.lower():
                        MessagingService.start_urls_consumer(group_id)
                    elif 'content' in topic.lower():
                        MessagingService.start_contents_consumer(group_id)
                    elif 'notification' in topic.lower():
                        MessagingService.start_notifications_consumer(group_id)
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'Unknown topic: {topic}')
                        )
            
            # Get status
            status = MessagingService.get_status()
            self.stdout.write(
                self.style.SUCCESS(f'Consumers started successfully')
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
                self.style.ERROR(f'Error starting consumers: {e}')
            )
            sys.exit(1)
        finally:
            self._cleanup()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.stdout.write('\nReceived shutdown signal, stopping consumers...')
        self._cleanup()
        sys.exit(0)
    
    def _cleanup(self):
        """Clean up resources"""
        try:
            MessagingService.stop_all_consumers()
            self.stdout.write(
                self.style.SUCCESS('All consumers stopped successfully')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error stopping consumers: {e}')
            )
