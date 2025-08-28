"""
Django management command for comprehensive task management.
This command provides a CLI interface for creating, executing, monitoring, and managing crawler tasks.
"""

import json
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta

from apps.common.models import CrawlerConfig, CrawlerTask, CrawlerScheduledTask
from apps.tasks.models import ScrapydTask, ScrapydTaskQueue
from apps.tasks.scrapyd_service import ScrapydService
from apps.tasks.tasks import execute_crawler_task


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Comprehensive task management for crawler tasks'
    
    def add_arguments(self, parser):
        # Main action commands
        parser.add_argument(
            'action',
            choices=['create', 'execute', 'list', 'status', 'cancel', 'schedule', 'monitor', 'cleanup'],
            help='Action to perform'
        )
        
        # Task creation parameters
        parser.add_argument(
            '--config-name',
            type=str,
            help='Name of the crawler configuration to use'
        )
        
        parser.add_argument(
            '--portal-name',
            type=str,
            help='Portal name (if not using config)'
        )
        
        parser.add_argument(
            '--portal-domain',
            type=str,
            help='Portal domain (if not using config)'
        )
        
        # Task execution parameters
        parser.add_argument(
            '--task-id',
            type=int,
            help='Task ID for specific operations'
        )
        
        parser.add_argument(
            '--worker-id',
            type=str,
            help='Worker identifier for the task'
        )
        
        parser.add_argument(
            '--priority',
            type=int,
            default=5,
            help='Task priority (1=highest, 10=lowest)'
        )
        
        # Scheduling parameters
        parser.add_argument(
            '--cron-expression',
            type=str,
            help='Cron expression for scheduled tasks (e.g., "0 0 * * *")'
        )
        
        parser.add_argument(
            '--schedule-name',
            type=str,
            help='Name for the scheduled task'
        )
        
        # Monitoring parameters
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Watch task status in real-time'
        )
        
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Watch interval in seconds'
        )
        
        # Output formatting
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output results in JSON format'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output'
        )
    
    def handle(self, *args, **options):
        """Handle the command execution."""
        action = options['action']
        
        try:
            if action == 'create':
                self.create_task(options)
            elif action == 'execute':
                self.execute_task(options)
            elif action == 'list':
                self.list_tasks(options)
            elif action == 'status':
                self.show_status(options)
            elif action == 'cancel':
                self.cancel_task(options)
            elif action == 'schedule':
                self.schedule_task(options)
            elif action == 'monitor':
                self.monitor_tasks(options)
            elif action == 'cleanup':
                self.cleanup_tasks(options)
            else:
                raise CommandError(f'Unknown action: {action}')
                
        except Exception as e:
            if options['verbose']:
                raise
            else:
                raise CommandError(f'Operation failed: {str(e)}')
    
    def create_task(self, options):
        """Create a new crawler task."""
        config_name = options['config_name']
        
        if not config_name:
            raise CommandError('--config-name is required for task creation')
        
        try:
            config = CrawlerConfig.objects.get(name=config_name)
        except CrawlerConfig.DoesNotExist:
            raise CommandError(f'Crawler configuration "{config_name}" not found')
        
        # Create the task
        task = CrawlerTask.objects.create(
            crawler_config=config,
            status='pending'
        )
        
        if options['json']:
            result = {
                'success': True,
                'task_id': task.id,
                'config_name': config.name,
                'portal_name': config.portal.name,
                'status': task.status,
                'created_at': task.created_at.isoformat()
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Created task {task.id} for config "{config_name}" '
                    f'(Portal: {config.portal.name})'
                )
            )
    
    def execute_task(self, options):
        """Execute a crawler task."""
        task_id = options['task_id']
        config_name = options['config_name']
        
        if not task_id and not config_name:
            raise CommandError('Either --task-id or --config-name is required')
        
        if task_id:
            # Execute existing task
            try:
                task = CrawlerTask.objects.get(id=task_id)
            except CrawlerTask.DoesNotExist:
                raise CommandError(f'Task {task_id} not found')
        else:
            # Create and execute new task
            try:
                config = CrawlerConfig.objects.get(name=config_name)
                task = CrawlerTask.objects.create(
                    crawler_config=config,
                    status='pending'
                )
            except CrawlerConfig.DoesNotExist:
                raise CommandError(f'Crawler configuration "{config_name}" not found')
        
        # Execute the task
        if options['verbose']:
            self.stdout.write(f'🚀 Executing task {task.id}...')
        
        result = execute_crawler_task.delay(task.id)
        
        if options['json']:
            result_data = {
                'success': True,
                'task_id': task.id,
                'celery_task_id': result.id,
                'status': 'queued',
                'message': 'Task queued for execution'
            }
            self.stdout.write(json.dumps(result_data, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Task {task.id} queued for execution (Celery ID: {result.id})'
                )
            )
    
    def list_tasks(self, options):
        """List all tasks with filtering options."""
        tasks = CrawlerTask.objects.select_related(
            'crawler_config', 'crawler_config__portal'
        ).order_by('-created_at')
        
        if options['config_name']:
            tasks = tasks.filter(crawler_config__name=options['config_name'])
        
        if options['json']:
            task_list = []
            for task in tasks:
                task_data = {
                    'id': task.id,
                    'config_name': task.crawler_config.name,
                    'portal_name': task.crawler_config.portal.name,
                    'status': task.status,
                    'created_at': task.created_at.isoformat(),
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'scrapyd_job_id': task.scrapyd_job_id,
                    'error_message': task.error_message
                }
                task_list.append(task_data)
            
            result = {
                'total_tasks': len(task_list),
                'tasks': task_list
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(f'📋 Found {tasks.count()} tasks:\n')
            
            for task in tasks:
                status_icon = {
                    'pending': '⏳',
                    'running': '🔄',
                    'completed': '✅',
                    'failed': '❌',
                    'cancelled': '🚫'
                }.get(task.status, '❓')
                
                self.stdout.write(
                    f'{status_icon} Task {task.id}: {task.crawler_config.name} '
                    f'({task.crawler_config.portal.name}) - {task.status}'
                )
                
                if task.scrapyd_job_id:
                    self.stdout.write(f'   Scrapyd Job ID: {task.scrapyd_job_id}')
                
                if task.error_message:
                    self.stdout.write(f'   Error: {task.error_message}')
    
    def show_status(self, options):
        """Show detailed status of a specific task."""
        task_id = options['task_id']
        
        if not task_id:
            raise CommandError('--task-id is required for status command')
        
        try:
            task = CrawlerTask.objects.select_related(
                'crawler_config', 'crawler_config__portal'
            ).get(id=task_id)
        except CrawlerTask.DoesNotExist:
            raise CommandError(f'Task {task_id} not found')
        
        if options['json']:
            status_data = {
                'task_id': task.id,
                'config_name': task.crawler_config.name,
                'portal_name': task.crawler_config.portal.name,
                'status': task.status,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'execution_time': str(task.execution_time) if task.execution_time else None,
                'scrapyd_job_id': task.scrapyd_job_id,
                'error_message': task.error_message
            }
            self.stdout.write(json.dumps(status_data, indent=2))
        else:
            self.stdout.write(f'📊 Task {task_id} Status:\n')
            self.stdout.write(f'   Configuration: {task.crawler_config.name}')
            self.stdout.write(f'   Portal: {task.crawler_config.portal.name}')
            self.stdout.write(f'   Status: {task.status}')
            self.stdout.write(f'   Created: {task.created_at}')
            
            if task.started_at:
                self.stdout.write(f'   Started: {task.started_at}')
            
            if task.completed_at:
                self.stdout.write(f'   Completed: {task.completed_at}')
            
            if task.execution_time:
                self.stdout.write(f'   Duration: {task.execution_time}')
            
            if task.scrapyd_job_id:
                self.stdout.write(f'   Scrapyd Job ID: {task.scrapyd_job_id}')
            
            if task.error_message:
                self.stdout.write(f'   Error: {task.error_message}')
    
    def cancel_task(self, options):
        """Cancel a running task."""
        task_id = options['task_id']
        
        if not task_id:
            raise CommandError('--task-id is required for cancel command')
        
        try:
            task = CrawlerTask.objects.get(id=task_id)
        except CrawlerTask.DoesNotExist:
            raise CommandError(f'Task {task_id} not found')
        
        if task.status not in ['pending', 'running']:
            raise CommandError(f'Cannot cancel task in {task.status} status')
        
        # Cancel the task
        task.status = 'cancelled'
        task.completed_at = timezone.now()
        task.save()
        
        if options['json']:
            result = {
                'success': True,
                'task_id': task.id,
                'status': task.status,
                'message': 'Task cancelled successfully'
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Task {task_id} cancelled successfully')
            )
    
    def schedule_task(self, options):
        """Schedule a recurring task."""
        config_name = options['config_name']
        cron_expression = options['cron_expression']
        schedule_name = options['schedule_name']
        
        if not all([config_name, cron_expression, schedule_name]):
            raise CommandError('--config-name, --cron-expression, and --schedule-name are required')
        
        try:
            config = CrawlerConfig.objects.get(name=config_name)
        except CrawlerConfig.DoesNotExist:
            raise CommandError(f'Crawler configuration "{config_name}" not found')
        
        # Create scheduled task
        scheduled_task = CrawlerScheduledTask.objects.create(
            crawler_config=config,
            name=schedule_name,
            cron_expression=cron_expression,
            is_active=True
        )
        
        if options['json']:
            result = {
                'success': True,
                'scheduled_task_id': scheduled_task.id,
                'name': scheduled_task.name,
                'config_name': config.name,
                'cron_expression': scheduled_task.cron_expression,
                'is_active': scheduled_task.is_active
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Scheduled task "{schedule_name}" created for config "{config_name}" '
                    f'(Cron: {cron_expression})'
                )
            )
    
    def monitor_tasks(self, options):
        """Monitor tasks in real-time."""
        if options['watch']:
            self.stdout.write('👀 Monitoring tasks in real-time (Press Ctrl+C to stop)...\n')
            
            try:
                while True:
                    self._display_task_summary()
                    time.sleep(options['interval'])
                    
            except KeyboardInterrupt:
                self.stdout.write('\n🛑 Monitoring stopped')
        else:
            self._display_task_summary()
    
    def _display_task_summary(self):
        """Display a summary of current task status."""
        total_tasks = CrawlerTask.objects.count()
        pending_tasks = CrawlerTask.objects.filter(status='pending').count()
        running_tasks = CrawlerTask.objects.filter(status='running').count()
        completed_tasks = CrawlerTask.objects.filter(status='completed').count()
        failed_tasks = CrawlerTask.objects.filter(status='failed').count()
        
        self.stdout.write(f'\r📊 Tasks: {total_tasks} total | '
                         f'⏳ {pending_tasks} pending | '
                         f'🔄 {running_tasks} running | '
                         f'✅ {completed_tasks} completed | '
                         f'❌ {failed_tasks} failed', ending='')
    
    def cleanup_tasks(self, options):
        """Clean up old completed/failed tasks."""
        # Clean up tasks older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        
        old_tasks = CrawlerTask.objects.filter(
            status__in=['completed', 'failed', 'cancelled'],
            created_at__lt=cutoff_date
        )
        
        count = old_tasks.count()
        
        if count > 0:
            old_tasks.delete()
            
            if options['json']:
                result = {
                    'success': True,
                    'cleaned_tasks': count,
                    'message': f'Cleaned up {count} old tasks'
                }
                self.stdout.write(json.dumps(result, indent=2))
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'🧹 Cleaned up {count} old tasks')
                )
        else:
            if options['json']:
                result = {
                    'success': True,
                    'cleaned_tasks': 0,
                    'message': 'No old tasks to clean up'
                }
                self.stdout.write(json.dumps(result, indent=2))
            else:
                self.stdout.write('✨ No old tasks to clean up')
