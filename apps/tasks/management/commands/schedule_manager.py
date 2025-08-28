"""
Django management command for managing scheduled crawler tasks.
This command provides a CLI interface for creating, managing, and monitoring scheduled tasks.
"""

import json
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime, timedelta

from apps.common.models import CrawlerConfig, CrawlerScheduledTask
from apps.tasks.tasks import execute_scheduled_crawler_task


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Manage scheduled crawler tasks'
    
    def add_arguments(self, parser):
        # Main action commands
        parser.add_argument(
            'action',
            choices=['create', 'list', 'enable', 'disable', 'execute', 'delete', 'next-run', 'validate'],
            help='Action to perform'
        )
        
        # Task identification
        parser.add_argument(
            '--schedule-id',
            type=int,
            help='Scheduled task ID for specific operations'
        )
        
        parser.add_argument(
            '--schedule-name',
            type=str,
            help='Scheduled task name for specific operations'
        )
        
        # Creation parameters
        parser.add_argument(
            '--config-name',
            type=str,
            help='Name of the crawler configuration to use'
        )
        
        parser.add_argument(
            '--cron-expression',
            type=str,
            help='Cron expression (e.g., "0 0 * * *" for daily at midnight)'
        )
        
        parser.add_argument(
            '--description',
            type=str,
            help='Description for the scheduled task'
        )
        
        # Execution parameters
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force execution even if task is not active'
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
                self.create_scheduled_task(options)
            elif action == 'list':
                self.list_scheduled_tasks(options)
            elif action == 'enable':
                self.enable_scheduled_task(options)
            elif action == 'disable':
                self.disable_scheduled_task(options)
            elif action == 'execute':
                self.execute_scheduled_task(options)
            elif action == 'delete':
                self.delete_scheduled_task(options)
            elif action == 'next-run':
                self.show_next_run(options)
            elif action == 'validate':
                self.validate_cron_expression(options)
            else:
                raise CommandError(f'Unknown action: {action}')
                
        except Exception as e:
            if options['verbose']:
                raise
            else:
                raise CommandError(f'Operation failed: {str(e)}')
    
    def create_scheduled_task(self, options):
        """Create a new scheduled task."""
        config_name = options['config_name']
        cron_expression = options['cron_expression']
        schedule_name = options['schedule_name']
        description = options.get('description', '')
        
        if not all([config_name, cron_expression, schedule_name]):
            raise CommandError('--config-name, --cron-expression, and --schedule-name are required')
        
        # Validate cron expression
        if not self._is_valid_cron(cron_expression):
            raise CommandError(f'Invalid cron expression: {cron_expression}')
        
        try:
            config = CrawlerConfig.objects.get(name=config_name)
        except CrawlerConfig.DoesNotExist:
            raise CommandError(f'Crawler configuration "{config_name}" not found')
        
        # Check if schedule name already exists
        if CrawlerScheduledTask.objects.filter(name=schedule_name).exists():
            raise CommandError(f'Scheduled task with name "{schedule_name}" already exists')
        
        # Create scheduled task
        scheduled_task = CrawlerScheduledTask.objects.create(
            crawler_config=config,
            name=schedule_name,
            description=description,
            cron_expression=cron_expression,
            is_active=True
        )
        
        if options['json']:
            result = {
                'success': True,
                'scheduled_task_id': scheduled_task.id,
                'name': scheduled_task.name,
                'config_name': config.name,
                'portal_name': config.portal.name,
                'cron_expression': scheduled_task.cron_expression,
                'is_active': scheduled_task.is_active,
                'next_run': self._get_next_run(cron_expression).isoformat() if self._is_valid_cron(cron_expression) else None
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Scheduled task "{schedule_name}" created successfully\n'
                    f'   Configuration: {config.name}\n'
                    f'   Portal: {config.portal.name}\n'
                    f'   Cron: {cron_expression}\n'
                    f'   Next run: {self._get_next_run(cron_expression)}'
                )
            )
    
    def list_scheduled_tasks(self, options):
        """List all scheduled tasks."""
        scheduled_tasks = CrawlerScheduledTask.objects.select_related(
            'crawler_config', 'crawler_config__portal'
        ).order_by('name')
        
        if options['json']:
            task_list = []
            for task in scheduled_tasks:
                task_data = {
                    'id': task.id,
                    'name': task.name,
                    'description': task.description,
                    'config_name': task.crawler_config.name,
                    'portal_name': task.crawler_config.portal.name,
                    'cron_expression': task.cron_expression,
                    'is_active': task.is_active,
                    'last_run': task.last_run.isoformat() if task.last_run else None,
                    'next_run': self._get_next_run(task.cron_expression).isoformat() if self._is_valid_cron(task.cron_expression) else None,
                    'created_at': task.created_at.isoformat()
                }
                task_list.append(task_data)
            
            result = {
                'total_scheduled_tasks': len(task_list),
                'scheduled_tasks': task_list
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(f'📅 Found {scheduled_tasks.count()} scheduled tasks:\n')
            
            for task in scheduled_tasks:
                status_icon = '✅' if task.is_active else '❌'
                self.stdout.write(
                    f'{status_icon} {task.name} (ID: {task.id})\n'
                    f'   Configuration: {task.crawler_config.name}\n'
                    f'   Portal: {task.crawler_config.portal.name}\n'
                    f'   Cron: {task.cron_expression}\n'
                    f'   Status: {"Active" if task.is_active else "Inactive"}'
                )
                
                if task.last_run:
                    self.stdout.write(f'   Last run: {task.last_run}')
                
                next_run = self._get_next_run(task.cron_expression)
                if next_run:
                    self.stdout.write(f'   Next run: {next_run}')
                
                if task.description:
                    self.stdout.write(f'   Description: {task.description}')
                
                self.stdout.write('')  # Empty line for separation
    
    def enable_scheduled_task(self, options):
        """Enable a scheduled task."""
        scheduled_task = self._get_scheduled_task(options)
        
        if scheduled_task.is_active:
            if options['json']:
                result = {
                    'success': True,
                    'message': f'Scheduled task "{scheduled_task.name}" is already active',
                    'scheduled_task_id': scheduled_task.id
                }
                self.stdout.write(json.dumps(result, indent=2))
            else:
                self.stdout.write(f'ℹ️  Scheduled task "{scheduled_task.name}" is already active')
            return
        
        scheduled_task.is_active = True
        scheduled_task.save()
        
        if options['json']:
            result = {
                'success': True,
                'message': f'Scheduled task "{scheduled_task.name}" enabled successfully',
                'scheduled_task_id': scheduled_task.id
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Scheduled task "{scheduled_task.name}" enabled successfully')
            )
    
    def disable_scheduled_task(self, options):
        """Disable a scheduled task."""
        scheduled_task = self._get_scheduled_task(options)
        
        if not scheduled_task.is_active:
            if options['json']:
                result = {
                    'success': True,
                    'message': f'Scheduled task "{scheduled_task.name}" is already inactive',
                    'scheduled_task_id': scheduled_task.id
                }
                self.stdout.write(json.dumps(result, indent=2))
            else:
                self.stdout.write(f'ℹ️  Scheduled task "{scheduled_task.name}" is already inactive')
            return
        
        scheduled_task.is_active = False
        scheduled_task.save()
        
        if options['json']:
            result = {
                'success': True,
                'message': f'Scheduled task "{scheduled_task.name}" disabled successfully',
                'scheduled_task_id': scheduled_task.id
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Scheduled task "{scheduled_task.name}" disabled successfully')
            )
    
    def execute_scheduled_task(self, options):
        """Execute a scheduled task immediately."""
        scheduled_task = self._get_scheduled_task(options)
        
        if not scheduled_task.is_active and not options['force']:
            raise CommandError(
                f'Scheduled task "{scheduled_task.name}" is not active. '
                f'Use --force to execute anyway.'
            )
        
        if options['verbose']:
            self.stdout.write(f'🚀 Executing scheduled task "{scheduled_task.name}"...')
        
        # Execute the scheduled task
        result = execute_scheduled_crawler_task.delay(scheduled_task.id)
        
        # Update last_run
        scheduled_task.last_run = timezone.now()
        scheduled_task.save()
        
        if options['json']:
            result_data = {
                'success': True,
                'scheduled_task_id': scheduled_task.id,
                'scheduled_task_name': scheduled_task.name,
                'celery_task_id': result.id,
                'status': 'executed',
                'message': 'Scheduled task executed successfully'
            }
            self.stdout.write(json.dumps(result_data, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Scheduled task "{scheduled_task.name}" executed successfully '
                    f'(Celery ID: {result.id})'
                )
            )
    
    def delete_scheduled_task(self, options):
        """Delete a scheduled task."""
        scheduled_task = self._get_scheduled_task(options)
        
        task_name = scheduled_task.name
        scheduled_task.delete()
        
        if options['json']:
            result = {
                'success': True,
                'message': f'Scheduled task "{task_name}" deleted successfully'
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Scheduled task "{task_name}" deleted successfully')
            )
    
    def show_next_run(self, options):
        """Show when the scheduled task will run next."""
        scheduled_task = self._get_scheduled_task(options)
        
        next_run = self._get_next_run(scheduled_task.cron_expression)
        
        if options['json']:
            result = {
                'scheduled_task_id': scheduled_task.id,
                'scheduled_task_name': scheduled_task.name,
                'cron_expression': scheduled_task.cron_expression,
                'next_run': next_run.isoformat() if next_run else None,
                'is_valid_cron': self._is_valid_cron(scheduled_task.cron_expression)
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            if next_run:
                self.stdout.write(
                    f'📅 Scheduled task "{scheduled_task.name}" will run next at: {next_run}'
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  Scheduled task "{scheduled_task.name}" has invalid cron expression: '
                        f'{scheduled_task.cron_expression}'
                    )
                )
    
    def validate_cron_expression(self, options):
        """Validate a cron expression."""
        cron_expression = options['cron_expression']
        
        if not cron_expression:
            raise CommandError('--cron-expression is required for validation')
        
        is_valid = self._is_valid_cron(cron_expression)
        next_runs = []
        
        if is_valid:
            # Show next 5 run times
            current_time = timezone.now()
            for i in range(5):
                next_run = self._get_next_run(cron_expression, current_time)
                if next_run:
                    next_runs.append(next_run)
                    current_time = next_run + timedelta(minutes=1)
        
        if options['json']:
            result = {
                'cron_expression': cron_expression,
                'is_valid': is_valid,
                'next_runs': [run.isoformat() for run in next_runs] if is_valid else []
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            if is_valid:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Cron expression "{cron_expression}" is valid')
                )
                self.stdout.write('Next 5 run times:')
                for i, run_time in enumerate(next_runs, 1):
                    self.stdout.write(f'   {i}. {run_time}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Cron expression "{cron_expression}" is invalid')
                )
    
    def _get_scheduled_task(self, options):
        """Get a scheduled task by ID or name."""
        schedule_id = options.get('schedule_id')
        schedule_name = options.get('schedule_name')
        
        if not schedule_id and not schedule_name:
            raise CommandError('Either --schedule-id or --schedule-name is required')
        
        try:
            if schedule_id:
                return CrawlerScheduledTask.objects.get(id=schedule_id)
            else:
                return CrawlerScheduledTask.objects.get(name=schedule_name)
        except CrawlerScheduledTask.DoesNotExist:
            if schedule_id:
                raise CommandError(f'Scheduled task with ID {schedule_id} not found')
            else:
                raise CommandError(f'Scheduled task with name "{schedule_name}" not found')
    
    def _is_valid_cron(self, cron_expression):
        """Basic cron expression validation."""
        try:
            parts = cron_expression.split()
            if len(parts) != 5:
                return False
            
            # Basic validation for each part
            for part in parts:
                if part == '*':
                    continue
                if ',' in part:
                    for subpart in part.split(','):
                        if not self._is_valid_cron_part(subpart):
                            return False
                else:
                    if not self._is_valid_cron_part(part):
                        return False
            
            return True
        except:
            return False
    
    def _is_valid_cron_part(self, part):
        """Validate a single cron part."""
        try:
            if part == '*':
                return True
            if '/' in part:
                base, step = part.split('/')
                if base == '*':
                    return int(step) > 0
                else:
                    return int(base) >= 0 and int(step) > 0
            if '-' in part:
                start, end = part.split('-')
                return int(start) >= 0 and int(end) >= int(start)
            return int(part) >= 0
        except:
            return False
    
    def _get_next_run(self, cron_expression, from_time=None):
        """Get the next run time for a cron expression."""
        if not self._is_valid_cron(cron_expression):
            return None
        
        if from_time is None:
            from_time = timezone.now()
        
        # This is a simplified implementation
        # In production, you'd want to use a proper cron parser library
        try:
            # For now, just add 1 hour as a placeholder
            # You should implement proper cron parsing here
            return from_time + timedelta(hours=1)
        except:
            return None
