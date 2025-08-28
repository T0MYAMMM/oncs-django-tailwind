from django.core.management.base import BaseCommand
from messaging.services import MessagingService
import json


class Command(BaseCommand):
    help = 'Check Kafka messaging service status'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output status in JSON format'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed status information'
        )
    
    def handle(self, *args, **options):
        json_output = options['json']
        detailed = options['detailed']
        
        try:
            status = MessagingService.get_status()
            
            if json_output:
                self.stdout.write(json.dumps(status, indent=2))
            else:
                self._print_status(status, detailed)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error getting status: {e}')
            )
    
    def _print_status(self, status, detailed):
        """Print status in a human-readable format"""
        self.stdout.write(
            self.style.SUCCESS('Kafka Messaging Service Status')
        )
        self.stdout.write('=' * 40)
        
        # Producer status
        producer_status = 'Connected' if status['producer_connected'] else 'Disconnected'
        self.stdout.write(f'Producer: {producer_status}')
        
        # Consumer status
        total_consumers = status['total_consumers']
        consumers_running = status['consumers_running']
        
        self.stdout.write(f'Total Consumers: {total_consumers}')
        
        if consumers_running:
            self.stdout.write('Running Consumers:')
            for topic in consumers_running:
                self.stdout.write(f'  - {topic}')
        else:
            self.stdout.write('No consumers running')
        
        # Overall status
        overall_status = 'Running' if status['running'] else 'Stopped'
        self.stdout.write(f'Overall Status: {overall_status}')
        
        if detailed:
            self.stdout.write('\nDetailed Information:')
            self.stdout.write('-' * 20)
            for key, value in status.items():
                if key not in ['producer_connected', 'consumers_running', 'total_consumers', 'running']:
                    self.stdout.write(f'{key}: {value}')
