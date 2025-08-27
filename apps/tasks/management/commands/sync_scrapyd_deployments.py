"""
Django management command to sync Scrapyd deployment data.
This command connects to the scrapyd_tracking database and syncs
deployment information to Django models.
"""

import os
import sys
import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from django.db import connections

from apps.tasks.models import ScrapydDeployment, ScrapydServer
from apps.tasks.db_router import ScrapydDatabaseConfig


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Scrapyd deployment data from the tracking database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if there are errors',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old deployment records',
        )
    
    def handle(self, *args, **options):
        """Handle the command execution."""
        self.stdout.write(
            self.style.SUCCESS('Starting Scrapyd deployment sync...')
        )
        
        try:
            # Get database configuration
            db_config = ScrapydDatabaseConfig.get_database_config()
            self.stdout.write(f"Target database: {db_config['ENGINE']} - {db_config.get('NAME', 'N/A')}")
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('DRY RUN MODE - No changes will be made')
                )
            
            # Sync deployments
            synced_count = self.sync_deployments(db_config, options)
            
            # Clean up if requested
            if options['cleanup']:
                cleaned_count = self.cleanup_old_deployments()
                self.stdout.write(
                    self.style.SUCCESS(f'Cleaned up {cleaned_count} old deployment records')
                )
            
            # Update legacy server references
            updated_servers = self.update_legacy_servers()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully synced {synced_count} deployments, '
                    f'updated {updated_servers} legacy servers'
                )
            )
            
        except Exception as e:
            if options['force']:
                self.stdout.write(
                    self.style.WARNING(f'Sync completed with errors (force mode): {e}')
                )
            else:
                raise CommandError(f'Sync failed: {e}')
    
    def sync_deployments(self, db_config, options):
        """Sync deployment data from the tracking database."""
        try:
            # Create a direct connection to the scrapyd_tracking database
            if db_config['ENGINE'] == 'django.db.backends.postgresql':
                import psycopg2
                
                conn = psycopg2.connect(
                    host=db_config['HOST'],
                    port=db_config['PORT'],
                    database=db_config['NAME'],
                    user=db_config['USER'],
                    password=db_config['PASSWORD']
                )
                
                # Query deployments
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            deployment_id, node_name, project_name, host, port, bind_address,
                            status, last_status_update, last_health_check, pid,
                            start_time, stop_time, is_healthy, health_score, error_count,
                            last_error, uptime_seconds, active_jobs, finished_jobs, pending_jobs,
                            config_hash, environment_vars, created_at, updated_at
                        FROM scrapyd_deployments
                        ORDER BY last_status_update DESC
                    """)
                    
                    rows = cursor.fetchall()
                    synced_count = 0
                    
                    for row in rows:
                        try:
                            deployment_data = {
                                'deployment_id': row[0],
                                'node_name': row[1],
                                'project_name': row[2],
                                'host': row[3],
                                'port': row[4],
                                'bind_address': row[5],
                                'status': row[6],
                                'last_status_update': row[7],
                                'last_health_check': row[8],
                                'pid': row[9],
                                'start_time': row[10],
                                'stop_time': row[11],
                                'is_healthy': row[12],
                                'health_score': row[13] or 0.0,
                                'error_count': row[14] or 0,
                                'last_error': row[15] or '',
                                'uptime_seconds': row[16] or 0.0,
                                'active_jobs': row[17] or 0,
                                'finished_jobs': row[18] or 0,
                                'pending_jobs': row[19] or 0,
                                'config_hash': row[20] or '',
                                'environment_vars': row[21] or {},
                                'created_at': row[22],
                                'updated_at': row[23]
                            }
                            
                            if options['dry_run']:
                                self.stdout.write(
                                    f"Would sync: {deployment_data['node_name']} - "
                                    f"{deployment_data['project_name']} ({deployment_data['host']}:{deployment_data['port']})"
                                )
                            else:
                                # Update or create deployment
                                deployment, created = ScrapydDeployment.objects.update_or_create(
                                    deployment_id=deployment_data['deployment_id'],
                                    defaults=deployment_data
                                )
                                
                                action = 'Created' if created else 'Updated'
                                self.stdout.write(
                                    f"{action}: {deployment.node_name} - "
                                    f"{deployment.project_name} ({deployment.host}:{deployment.port})"
                                )
                            
                            synced_count += 1
                            
                        except Exception as e:
                            if options['force']:
                                self.stdout.write(
                                    self.style.WARNING(f'Error syncing deployment {row[0]}: {e}')
                                )
                            else:
                                raise
                
                conn.close()
                return synced_count
                
            elif db_config['ENGINE'] == 'django.db.backends.sqlite3':
                import sqlite3
                
                conn = sqlite3.connect(db_config['NAME'])
                conn.row_factory = sqlite3.Row
                
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        deployment_id, node_name, project_name, host, port, bind_address,
                        status, last_status_update, last_health_check, pid,
                        start_time, stop_time, is_healthy, health_score, error_count,
                        last_error, uptime_seconds, active_jobs, finished_jobs, pending_jobs,
                        config_hash, environment_vars, created_at, updated_at
                    FROM scrapyd_deployments
                    ORDER BY last_status_update DESC
                """)
                
                rows = cursor.fetchall()
                synced_count = 0
                
                for row in rows:
                    try:
                        deployment_data = {
                            'deployment_id': row[0],
                            'node_name': row[1],
                            'project_name': row[2],
                            'host': row[3],
                            'port': row[4],
                            'bind_address': row[5],
                            'status': row[6],
                            'last_status_update': row[7],
                            'last_health_check': row[8],
                            'pid': row[9],
                            'start_time': row[10],
                            'stop_time': row[11],
                            'is_healthy': bool(row[12]),
                            'health_score': float(row[13]) if row[13] else 0.0,
                            'error_count': int(row[14]) if row[14] else 0,
                            'last_error': row[15] or '',
                            'uptime_seconds': float(row[16]) if row[16] else 0.0,
                            'active_jobs': int(row[17]) if row[17] else 0,
                            'finished_jobs': int(row[18]) if row[18] else 0,
                            'pending_jobs': int(row[19]) if row[19] else 0,
                            'config_hash': row[20] or '',
                            'environment_vars': json.loads(row[21]) if row[21] else {},
                            'created_at': row[22],
                            'updated_at': row[23]
                        }
                        
                        if options['dry_run']:
                            self.stdout.write(
                                f"Would sync: {deployment_data['node_name']} - "
                                f"{deployment_data['project_name']} ({deployment_data['host']}:{deployment_data['port']})"
                            )
                        else:
                            # Update or create deployment
                            deployment, created = ScrapydDeployment.objects.update_or_create(
                                deployment_id=deployment_data['deployment_id'],
                                defaults=deployment_data
                            )
                            
                            action = 'Created' if created else 'Updated'
                            self.stdout.write(
                                f"{action}: {deployment.node_name} - "
                                f"{deployment.project_name} ({deployment.host}:{deployment.port})"
                            )
                        
                        synced_count += 1
                        
                    except Exception as e:
                        if options['force']:
                            self.stdout.write(
                                self.style.WARNING(f'Error syncing deployment {row[0]}: {e}')
                            )
                        else:
                            raise
                
                conn.close()
                return synced_count
                
            else:
                raise CommandError(f'Unsupported database engine: {db_config["ENGINE"]}')
                
        except Exception as e:
            raise CommandError(f'Failed to sync deployments: {e}')
    
    def cleanup_old_deployments(self):
        """Clean up old deployment records."""
        try:
            # Remove deployments that haven't been updated in 7 days
            cutoff_date = timezone.now() - timezone.timedelta(days=7)
            old_deployments = ScrapydDeployment.objects.filter(
                last_status_update__lt=cutoff_date,
                status__in=['stopped', 'error']
            )
            
            count = old_deployments.count()
            old_deployments.delete()
            
            return count
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error during cleanup: {e}')
            )
            return 0
    
    def update_legacy_servers(self):
        """Update legacy server references to point to active deployments."""
        try:
            updated_count = 0
            
            # Get all legacy servers
            legacy_servers = ScrapydServer.objects.all()
            
            for server in legacy_servers:
                # Find matching deployment
                deployment = ScrapydDeployment.objects.filter(
                    host=server.host,
                    port=server.port,
                    is_active=True
                ).first()
                
                if deployment and server.active_deployment != deployment:
                    server.active_deployment = deployment
                    server.save(update_fields=['active_deployment'])
                    updated_count += 1
                    
                    self.stdout.write(
                        f"Updated server {server.name} to reference deployment {deployment.deployment_id}"
                    )
            
            return updated_count
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error updating legacy servers: {e}')
            )
            return 0
