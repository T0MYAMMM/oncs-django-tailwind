"""
Django management command for monitoring task health and performance.
This command provides real-time monitoring, health checks, and performance metrics.
"""

import json
import logging
import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Count, Avg, Max, Min
from datetime import datetime, timedelta

from apps.common.models import CrawlerTask, CrawlerConfig
from apps.tasks.models import ScrapydDeployment, ScrapydHealthLog
from apps.tasks.scrapyd_service import ScrapydService


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Monitor task health, performance, and system status'
    
    def add_arguments(self, parser):
        # Main action commands
        parser.add_argument(
            'action',
            choices=['overview', 'health', 'performance', 'deployments', 'watch', 'alerts'],
            help='Action to perform'
        )
        
        # Monitoring parameters
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Watch metrics in real-time'
        )
        
        parser.add_argument(
            '--interval',
            type=int,
            default=10,
            help='Watch interval in seconds'
        )
        
        parser.add_argument(
            '--time-range',
            choices=['1h', '6h', '24h', '7d', '30d'],
            default='24h',
            help='Time range for metrics'
        )
        
        parser.add_argument(
            '--portal',
            type=str,
            help='Filter by portal name'
        )
        
        parser.add_argument(
            '--config',
            type=str,
            help='Filter by crawler configuration name'
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
            if action == 'overview':
                self.show_overview(options)
            elif action == 'health':
                self.show_health_status(options)
            elif action == 'performance':
                self.show_performance_metrics(options)
            elif action == 'deployments':
                self.show_deployment_status(options)
            elif action == 'watch':
                self.watch_metrics(options)
            elif action == 'alerts':
                self.show_alerts(options)
            else:
                raise CommandError(f'Unknown action: {action}')
                
        except Exception as e:
            if options['verbose']:
                raise
            else:
                raise CommandError(f'Operation failed: {str(e)}')
    
    def show_overview(self, options):
        """Show a comprehensive overview of the task system."""
        time_range = self._get_time_range(options['time_range'])
        
        # Task statistics
        total_tasks = CrawlerTask.objects.count()
        recent_tasks = CrawlerTask.objects.filter(created_at__gte=time_range).count()
        
        # Status breakdown
        status_counts = CrawlerTask.objects.values('status').annotate(count=Count('id'))
        status_summary = {item['status']: item['count'] for item in status_counts}
        
        # Portal statistics
        portal_stats = CrawlerTask.objects.filter(
            created_at__gte=time_range
        ).values(
            'crawler_config__portal__name'
        ).annotate(
            total=Count('id'),
            completed=Count('id', filter={'status': 'completed'}),
            failed=Count('id', filter={'status': 'failed'})
        )
        
        # Deployment health
        deployment_service = ScrapydService()
        deployment_summary = deployment_service.get_deployment_summary()
        
        if options['json']:
            result = {
                'timestamp': timezone.now().isoformat(),
                'time_range': options['time_range'],
                'task_statistics': {
                    'total_tasks': total_tasks,
                    'recent_tasks': recent_tasks,
                    'status_breakdown': status_summary
                },
                'portal_statistics': list(portal_stats),
                'deployment_summary': deployment_summary
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write('📊 Task System Overview\n')
            self.stdout.write('=' * 50)
            
            # Task statistics
            self.stdout.write(f'\n📋 Task Statistics ({options["time_range"]}):')
            self.stdout.write(f'   Total tasks: {total_tasks}')
            self.stdout.write(f'   Recent tasks: {recent_tasks}')
            
            # Status breakdown
            self.stdout.write('\n📈 Status Breakdown:')
            for status, count in status_summary.items():
                icon = self._get_status_icon(status)
                self.stdout.write(f'   {icon} {status.title()}: {count}')
            
            # Portal statistics
            self.stdout.write('\n🌐 Portal Statistics:')
            for portal in portal_stats:
                portal_name = portal['crawler_config__portal__name']
                total = portal['total']
                completed = portal['completed']
                failed = portal['failed']
                success_rate = (completed / total * 100) if total > 0 else 0
                
                self.stdout.write(f'   {portal_name}: {total} tasks, {success_rate:.1f}% success')
            
            # Deployment status
            self.stdout.write('\n🖥️  Deployment Status:')
            self.stdout.write(f'   Total deployments: {deployment_summary["total_deployments"]}')
            self.stdout.write(f'   Active deployments: {deployment_summary["active_deployments"]}')
            self.stdout.write(f'   Healthy deployments: {deployment_summary["healthy_deployments"]}')
            self.stdout.write(f'   Total active jobs: {deployment_summary["total_active_jobs"]}')
            self.stdout.write(f'   Total pending jobs: {deployment_summary["total_pending_jobs"]}')
    
    def show_health_status(self, options):
        """Show detailed health status of the system."""
        time_range = self._get_time_range(options['time_range'])
        
        # Get deployment health
        deployment_service = ScrapydService()
        deployment_summary = deployment_service.get_deployment_summary()
        
        # Get recent health logs
        recent_health_logs = ScrapydHealthLog.objects.filter(
            timestamp__gte=time_range
        ).select_related('deployment').order_by('-timestamp')[:20]
        
        # Calculate health metrics
        total_health_checks = recent_health_logs.count()
        healthy_checks = recent_health_logs.filter(is_healthy=True).count()
        health_rate = (healthy_checks / total_health_checks * 100) if total_health_checks > 0 else 0
        
        if options['json']:
            result = {
                'timestamp': timezone.now().isoformat(),
                'time_range': options['time_range'],
                'overall_health': {
                    'health_rate': health_rate,
                    'total_checks': total_health_checks,
                    'healthy_checks': healthy_checks
                },
                'deployment_summary': deployment_summary,
                'recent_health_logs': [
                    {
                        'deployment_name': log.deployment.node_name,
                        'timestamp': log.timestamp.isoformat(),
                        'is_healthy': log.is_healthy,
                        'health_score': log.health_score,
                        'response_time_ms': log.response_time_ms
                    }
                    for log in recent_health_logs
                ]
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write('🏥 System Health Status\n')
            self.stdout.write('=' * 50)
            
            # Overall health
            self.stdout.write(f'\n📊 Overall Health ({options["time_range"]}):')
            health_icon = '✅' if health_rate >= 90 else '⚠️' if health_rate >= 70 else '❌'
            self.stdout.write(f'   {health_icon} Health Rate: {health_rate:.1f}%')
            self.stdout.write(f'   Total health checks: {total_health_checks}')
            self.stdout.write(f'   Healthy checks: {healthy_checks}')
            
            # Deployment health
            self.stdout.write('\n🖥️  Deployment Health:')
            for deployment in deployment_summary['deployments']:
                health_icon = '✅' if deployment['is_healthy'] else '❌'
                self.stdout.write(
                    f'   {health_icon} {deployment["node_name"]} '
                    f'({deployment["host"]}:{deployment["port"]})'
                )
                self.stdout.write(f'      Status: {deployment["status"]}')
                self.stdout.write(f'      Health Score: {deployment["health_score"]:.2f}')
                self.stdout.write(f'      Active Jobs: {deployment["active_jobs"]}')
                self.stdout.write(f'      Pending Jobs: {deployment["pending_jobs"]}')
            
            # Recent health logs
            self.stdout.write('\n📝 Recent Health Logs:')
            for log in recent_health_logs[:10]:
                health_icon = '✅' if log.is_healthy else '❌'
                self.stdout.write(
                    f'   {health_icon} {log.deployment.node_name} - '
                    f'{log.timestamp.strftime("%H:%M:%S")} - '
                    f'Score: {log.health_score:.2f} - '
                    f'{log.response_time_ms}ms'
                )
    
    def show_performance_metrics(self, options):
        """Show performance metrics for tasks."""
        time_range = self._get_time_range(options['time_range'])
        
        # Filter by portal/config if specified
        task_filter = {'created_at__gte': time_range}
        if options['portal']:
            task_filter['crawler_config__portal__name__icontains'] = options['portal']
        if options['config']:
            task_filter['crawler_config__name__icontains'] = options['config']
        
        # Get performance metrics
        tasks = CrawlerTask.objects.filter(**task_filter)
        
        # Calculate metrics
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='completed')
        failed_tasks = tasks.filter(status='failed')
        
        # Success rate
        success_rate = (completed_tasks.count() / total_tasks * 100) if total_tasks > 0 else 0
        
        # Average execution time
        avg_execution_time = completed_tasks.aggregate(
            avg_time=Avg('execution_time')
        )['avg_time']
        
        # Portal performance
        portal_performance = tasks.values(
            'crawler_config__portal__name'
        ).annotate(
            total=Count('id'),
            completed=Count('id', filter={'status': 'completed'}),
            failed=Count('id', filter={'status': 'failed'}),
            avg_time=Avg('execution_time')
        )
        
        if options['json']:
            result = {
                'timestamp': timezone.now().isoformat(),
                'time_range': options['time_range'],
                'filters': {
                    'portal': options.get('portal'),
                    'config': options.get('config')
                },
                'overall_metrics': {
                    'total_tasks': total_tasks,
                    'success_rate': success_rate,
                    'avg_execution_time': str(avg_execution_time) if avg_execution_time else None
                },
                'portal_performance': list(portal_performance)
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write('📈 Performance Metrics\n')
            self.stdout.write('=' * 50)
            
            # Filters
            if options['portal'] or options['config']:
                self.stdout.write(f'\n🔍 Filters:')
                if options['portal']:
                    self.stdout.write(f'   Portal: {options["portal"]}')
                if options['config']:
                    self.stdout.write(f'   Config: {options["config"]}')
            
            # Overall metrics
            self.stdout.write(f'\n📊 Overall Performance ({options["time_range"]}):')
            self.stdout.write(f'   Total tasks: {total_tasks}')
            self.stdout.write(f'   Success rate: {success_rate:.1f}%')
            
            if avg_execution_time:
                avg_minutes = avg_execution_time.total_seconds() / 60
                self.stdout.write(f'   Average execution time: {avg_minutes:.1f} minutes')
            else:
                self.stdout.write('   Average execution time: N/A')
            
            # Portal performance
            self.stdout.write('\n🌐 Portal Performance:')
            for portal in portal_performance:
                portal_name = portal['crawler_config__portal__name']
                total = portal['total']
                completed = portal['completed']
                failed = portal['failed']
                success_rate = (completed / total * 100) if total > 0 else 0
                avg_time = portal['avg_time']
                
                self.stdout.write(f'   {portal_name}:')
                self.stdout.write(f'     Total: {total}, Success: {success_rate:.1f}%')
                
                if avg_time:
                    avg_minutes = avg_time.total_seconds() / 60
                    self.stdout.write(f'     Avg time: {avg_minutes:.1f} minutes')
                else:
                    self.stdout.write('     Avg time: N/A')
    
    def show_deployment_status(self, options):
        """Show detailed deployment status."""
        deployment_service = ScrapydService()
        deployment_summary = deployment_service.get_deployment_summary()
        
        if options['json']:
            self.stdout.write(json.dumps(deployment_summary, indent=2))
        else:
            self.stdout.write('🖥️  Deployment Status\n')
            self.stdout.write('=' * 50)
            
            self.stdout.write(f'\n📊 Summary:')
            self.stdout.write(f'   Total deployments: {deployment_summary["total_deployments"]}')
            self.stdout.write(f'   Active deployments: {deployment_summary["active_deployments"]}')
            self.stdout.write(f'   Healthy deployments: {deployment_summary["healthy_deployments"]}')
            self.stdout.write(f'   Total active jobs: {deployment_summary["total_active_jobs"]}')
            self.stdout.write(f'   Total pending jobs: {deployment_summary["total_pending_jobs"]}')
            
            self.stdout.write(f'\n📋 Individual Deployments:')
            for deployment in deployment_summary['deployments']:
                health_icon = '✅' if deployment['is_healthy'] else '❌'
                status_icon = self._get_status_icon(deployment['status'])
                
                self.stdout.write(f'\n   {health_icon} {deployment["node_name"]}')
                self.stdout.write(f'     Host: {deployment["host"]}:{deployment["port"]}')
                self.stdout.write(f'     Status: {status_icon} {deployment["status"]}')
                self.stdout.write(f'     Health Score: {deployment["health_score"]:.2f}')
                self.stdout.write(f'     Uptime: {deployment["uptime"]}')
                self.stdout.write(f'     Jobs: {deployment["active_jobs"]} active, {deployment["pending_jobs"]} pending')
                self.stdout.write(f'     Can accept tasks: {"Yes" if deployment["can_accept_tasks"] else "No"}')
    
    def watch_metrics(self, options):
        """Watch metrics in real-time."""
        self.stdout.write('👀 Watching metrics in real-time (Press Ctrl+C to stop)...\n')
        
        try:
            while True:
                self._display_live_metrics(options)
                time.sleep(options['interval'])
                
        except KeyboardInterrupt:
            self.stdout.write('\n🛑 Monitoring stopped')
    
    def _display_live_metrics(self, options):
        """Display live metrics."""
        # Get current metrics
        total_tasks = CrawlerTask.objects.count()
        pending_tasks = CrawlerTask.objects.filter(status='pending').count()
        running_tasks = CrawlerTask.objects.filter(status='running').count()
        completed_tasks = CrawlerTask.objects.filter(status='completed').count()
        failed_tasks = CrawlerTask.objects.filter(status='failed').count()
        
        # Get deployment status
        deployment_service = ScrapydService()
        deployment_summary = deployment_service.get_deployment_summary()
        
        # Clear line and display metrics
        timestamp = timezone.now().strftime('%H:%M:%S')
        self.stdout.write(
            f'\r[{timestamp}] 📊 Tasks: {total_tasks} total | '
            f'⏳ {pending_tasks} pending | '
            f'🔄 {running_tasks} running | '
            f'✅ {completed_tasks} completed | '
            f'❌ {failed_tasks} failed | '
            f'🖥️  Deployments: {deployment_summary["healthy_deployments"]}/{deployment_summary["total_deployments"]} healthy',
            ending=''
        )
    
    def show_alerts(self, options):
        """Show system alerts and warnings."""
        time_range = self._get_time_range(options['time_range'])
        
        alerts = []
        
        # Check for failed tasks
        recent_failed_tasks = CrawlerTask.objects.filter(
            status='failed',
            created_at__gte=time_range
        ).count()
        
        if recent_failed_tasks > 0:
            alerts.append({
                'level': 'warning',
                'message': f'{recent_failed_tasks} tasks failed in the last {options["time_range"]}',
                'type': 'failed_tasks'
            })
        
        # Check for unhealthy deployments
        unhealthy_deployments = ScrapydDeployment.objects.filter(is_healthy=False).count()
        if unhealthy_deployments > 0:
            alerts.append({
                'level': 'error',
                'message': f'{unhealthy_deployments} deployments are unhealthy',
                'type': 'unhealthy_deployments'
            })
        
        # Check for high pending jobs
        high_pending_deployments = ScrapydDeployment.objects.filter(pending_jobs__gt=50).count()
        if high_pending_deployments > 0:
            alerts.append({
                'level': 'warning',
                'message': f'{high_pending_deployments} deployments have high pending job counts',
                'type': 'high_pending_jobs'
            })
        
        # Check for long-running tasks
        long_running_threshold = timezone.now() - timedelta(hours=2)
        long_running_tasks = CrawlerTask.objects.filter(
            status='running',
            started_at__lt=long_running_threshold
        ).count()
        
        if long_running_tasks > 0:
            alerts.append({
                'level': 'warning',
                'message': f'{long_running_tasks} tasks have been running for more than 2 hours',
                'type': 'long_running_tasks'
            })
        
        if options['json']:
            result = {
                'timestamp': timezone.now().isoformat(),
                'time_range': options['time_range'],
                'alerts': alerts,
                'total_alerts': len(alerts)
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            if not alerts:
                self.stdout.write('✅ No alerts - system is healthy!')
                return
            
            self.stdout.write('🚨 System Alerts\n')
            self.stdout.write('=' * 50)
            
            for alert in alerts:
                level_icon = {
                    'error': '❌',
                    'warning': '⚠️',
                    'info': 'ℹ️'
                }.get(alert['level'], '❓')
                
                self.stdout.write(f'\n{level_icon} {alert["message"]}')
                self.stdout.write(f'   Type: {alert["type"]}')
                self.stdout.write(f'   Level: {alert["level"].upper()}')
    
    def _get_time_range(self, time_range_str):
        """Get datetime for the specified time range."""
        now = timezone.now()
        
        if time_range_str == '1h':
            return now - timedelta(hours=1)
        elif time_range_str == '6h':
            return now - timedelta(hours=6)
        elif time_range_str == '24h':
            return now - timedelta(days=1)
        elif time_range_str == '7d':
            return now - timedelta(days=7)
        elif time_range_str == '30d':
            return now - timedelta(days=30)
        else:
            return now - timedelta(days=1)  # Default to 24h
    
    def _get_status_icon(self, status):
        """Get icon for a status."""
        return {
            'pending': '⏳',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '🚫',
            'starting': '🚀',
            'stopping': '🛑',
            'stopped': '⏹️',
            'error': '💥',
            'healthy': '💚',
            'unhealthy': '💔'
        }.get(status, '❓')
