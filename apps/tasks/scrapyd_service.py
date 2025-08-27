"""
Service class for integrating with Scrapyd deployment tracking and task management.
This service provides methods to monitor Scrapyd instances and push tasks based on availability.
"""

import os
import json
import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings

from .models import (
    ScrapydDeployment, ScrapydTask, ScrapydTaskQueue, 
    ScrapydHealthLog, ScrapydServer
)
from .db_router import ScrapydDatabaseConfig


logger = logging.getLogger(__name__)


class ScrapydService:
    """
    Service class for managing Scrapyd deployments and tasks.
    Integrates with the deployment tracking system to monitor server health
    and distribute tasks based on availability.
    """
    
    def __init__(self):
        """Initialize the Scrapyd service."""
        self.auth = None
        if hasattr(settings, 'SCRAPYD_USERNAME') and hasattr(settings, 'SCRAPYD_PASSWORD'):
            self.auth = (settings.SCRAPYD_USERNAME, settings.SCRAPYD_PASSWORD)
    
    def sync_deployments_from_tracking_db(self) -> List[ScrapydDeployment]:
        """
        Sync deployment information from the scrapyd_tracking database.
        This method should be called periodically to keep Django models in sync.
        """
        try:
            # This would typically involve direct database queries or API calls
            # to the scrapyd_tracking database to get current deployment status
            logger.info("Syncing deployments from tracking database...")
            
            # For now, we'll return existing deployments
            # In a real implementation, you'd query the external database
            return list(ScrapydDeployment.objects.filter(is_active=True))
            
        except Exception as e:
            logger.error(f"Error syncing deployments: {e}")
            return []
    
    def check_deployment_health(self, deployment: ScrapydDeployment) -> Dict[str, Any]:
        """
        Check the health of a specific Scrapyd deployment.
        """
        try:
            url = f"{deployment.base_url}/daemonstatus.json"
            response = requests.get(
                url, 
                auth=self.auth, 
                timeout=10,
                headers={'User-Agent': 'Django-ScrapydService/1.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                is_healthy = data.get('status') == 'ok'
                health_score = 1.0 if is_healthy else 0.0
                
                # Update deployment health
                deployment.update_health(
                    is_healthy=is_healthy,
                    health_score=health_score,
                    error_count=0
                )
                
                # Update job counts
                deployment.update_job_counts(
                    active=data.get('running', 0),
                    finished=data.get('finished', 0),
                    pending=data.get('pending', 0)
                )
                
                # Log health check
                ScrapydHealthLog.objects.create(
                    deployment=deployment,
                    is_healthy=is_healthy,
                    health_score=health_score,
                    response_time_ms=int(response.elapsed.total_seconds() * 1000),
                    status_code=response.status_code,
                    active_jobs=data.get('running', 0),
                    pending_jobs=data.get('pending', 0),
                    finished_jobs=data.get('finished', 0),
                    error_count=0
                )
                
                return {
                    'is_healthy': is_healthy,
                    'health_score': health_score,
                    'status': data.get('status'),
                    'active_jobs': data.get('running', 0),
                    'pending_jobs': data.get('pending', 0),
                    'finished_jobs': data.get('finished', 0),
                    'response_time_ms': int(response.elapsed.total_seconds() * 1000)
                }
            else:
                # Health check failed
                deployment.update_health(
                    is_healthy=False,
                    health_score=0.0,
                    error_count=deployment.error_count + 1,
                    last_error=f"HTTP {response.status_code}: {response.text}"
                )
                
                # Log failed health check
                ScrapydHealthLog.objects.create(
                    deployment=deployment,
                    is_healthy=False,
                    health_score=0.0,
                    response_time_ms=int(response.elapsed.total_seconds() * 1000),
                    status_code=response.status_code,
                    active_jobs=0,
                    pending_jobs=0,
                    finished_jobs=0,
                    error_count=deployment.error_count,
                    error_message=f"HTTP {response.status_code}: {response.text}"
                )
                
                return {
                    'is_healthy': False,
                    'health_score': 0.0,
                    'status': 'error',
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.RequestException as e:
            # Network or connection error
            error_msg = f"Connection error: {str(e)}"
            deployment.update_health(
                is_healthy=False,
                health_score=0.0,
                error_count=deployment.error_count + 1,
                last_error=error_msg
            )
            
            # Log connection error
            ScrapydHealthLog.objects.create(
                deployment=deployment,
                is_healthy=False,
                health_score=0.0,
                response_time_ms=0,
                status_code=None,
                active_jobs=0,
                pending_jobs=0,
                finished_jobs=0,
                error_count=deployment.error_count,
                error_message=error_msg
            )
            
            return {
                'is_healthy': False,
                'health_score': 0.0,
                'status': 'error',
                'error': error_msg
            }
    
    def get_available_deployments(self) -> List[ScrapydDeployment]:
        """
        Get list of deployments that can accept new tasks.
        """
        return list(ScrapydDeployment.objects.filter(
            is_active=True,
            is_healthy=True,
            pending_jobs__lt=100,  # Not too many pending jobs
            error_count__lt=10     # Not too many errors
        ).order_by('pending_jobs', '-health_score'))
    
    def find_best_deployment_for_task(self, task: ScrapydTask) -> Optional[ScrapydDeployment]:
        """
        Find the best deployment for a specific task based on:
        - Health status
        - Current load
        - Error rate
        - Performance metrics
        """
        available_deployments = self.get_available_deployments()
        
        if not available_deployments:
            return None
        
        # Score each deployment based on multiple factors
        scored_deployments = []
        for deployment in available_deployments:
            score = 0
            
            # Health score (0-1) contributes 40% to total score
            score += deployment.health_score * 0.4
            
            # Load factor (fewer pending jobs = higher score) contributes 30%
            load_factor = max(0, 1 - (deployment.pending_jobs / 100))
            score += load_factor * 0.3
            
            # Error factor (fewer errors = higher score) contributes 20%
            error_factor = max(0, 1 - (deployment.error_count / 10))
            score += error_factor * 0.2
            
            # Uptime factor (longer uptime = higher score) contributes 10%
            uptime_factor = min(1, deployment.uptime_seconds / 3600)  # Normalize to hours
            score += uptime_factor * 0.1
            
            scored_deployments.append((deployment, score))
        
        # Sort by score (highest first) and return the best
        scored_deployments.sort(key=lambda x: x[1], reverse=True)
        return scored_deployments[0][0] if scored_deployments else None
    
    def send_task_to_deployment(self, task: ScrapydTask, deployment: ScrapydDeployment) -> Optional[str]:
        """
        Send a task to a specific Scrapyd deployment.
        Returns the Scrapyd job ID if successful, None otherwise.
        """
        try:
            url = f"{deployment.base_url}/schedule.json"
            
            # Prepare the task payload
            payload = {
                'project': deployment.project_name,
                'spider': 'generic',  # Using the generic spider
                'worker_id': task.worker_id or f'worker-{task.task_id[:8]}',
                'use_async': str(task.use_async).lower(),
                'debug_mode': str(task.debug_mode).lower(),
                'config_dict': json.dumps({
                    'name': task.name,
                    'portal_name': task.portal_name,
                    'portal_domain': task.portal_domain,
                    'start_urls': task.start_urls,
                    'allowed_domains': task.allowed_domains,
                    'selectors': task.selectors,
                    'custom_settings': task.custom_settings or {}
                })
            }
            
            # Send the request
            response = requests.post(
                url,
                data=payload,
                auth=self.auth,
                timeout=30,
                headers={'User-Agent': 'Django-ScrapydService/1.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    job_id = data.get('jobid')
                    
                    # Update task with deployment and job ID
                    task.assign_to_deployment(deployment)
                    task.scrapyd_job_id = job_id
                    task.save()
                    
                    # Create queue entry
                    ScrapydTaskQueue.objects.create(
                        task=task,
                        assigned_deployment=deployment,
                        status='assigned',
                        priority=task.priority
                    )
                    
                    logger.info(f"Task {task.task_id} sent to deployment {deployment.deployment_id}, job ID: {job_id}")
                    return job_id
                else:
                    error_msg = f"Scrapyd error: {data.get('message', 'Unknown error')}"
                    logger.error(f"Failed to send task {task.task_id}: {error_msg}")
                    task.error_message = error_msg
                    task.save()
                    return None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Failed to send task {task.task_id}: {error_msg}")
                task.error_message = error_msg
                task.save()
                return None
                
        except Exception as e:
            error_msg = f"Error sending task: {str(e)}"
            logger.error(f"Failed to send task {task.task_id}: {error_msg}")
            task.error_message = error_msg
            task.save()
            return None
    
    def queue_task(self, task: ScrapydTask) -> bool:
        """
        Queue a task for execution by finding the best available deployment.
        """
        try:
            # Find the best deployment for this task
            deployment = self.find_best_deployment_for_task(task)
            
            if not deployment:
                logger.warning(f"No available deployment found for task {task.task_id}")
                # Create queue entry in waiting status
                ScrapydTaskQueue.objects.create(
                    task=task,
                    status='waiting',
                    priority=task.priority
                )
                return False
            
            # Send task to deployment
            job_id = self.send_task_to_deployment(task, deployment)
            return job_id is not None
            
        except Exception as e:
            logger.error(f"Error queuing task {task.task_id}: {e}")
            return False
    
    def monitor_task_status(self, task: ScrapydTask) -> Dict[str, Any]:
        """
        Monitor the status of a running task.
        """
        if not task.scrapyd_job_id or not task.target_deployment:
            return {'status': 'unknown', 'error': 'No deployment or job ID'}
        
        try:
            url = f"{task.target_deployment.base_url}/listjobs.json"
            params = {'project': task.target_deployment.project_name}
            
            response = requests.get(
                url,
                params=params,
                auth=self.auth,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Find our job in the lists
                job_id = task.scrapyd_job_id
                
                # Check running jobs
                for job in data.get('running', []):
                    if job.get('id') == job_id:
                        return {
                            'status': 'running',
                            'start_time': job.get('start_time'),
                            'spider': job.get('spider')
                        }
                
                # Check finished jobs
                for job in data.get('finished', []):
                    if job.get('id') == job_id:
                        # Task completed
                        task.complete_execution(
                            items_scraped=job.get('items_scraped', 0)
                        )
                        
                        # Update queue status
                        queue_entry = task.queue_entries.filter(status='processing').first()
                        if queue_entry:
                            queue_entry.mark_completed()
                        
                        return {
                            'status': 'completed',
                            'items_scraped': job.get('items_scraped', 0),
                            'end_time': job.get('end_time')
                        }
                
                # Check pending jobs
                for job in data.get('pending', []):
                    if job.get('id') == job_id:
                        return {
                            'status': 'pending',
                            'spider': job.get('spider')
                        }
                
                # Job not found in any list
                return {'status': 'unknown', 'error': 'Job not found'}
                
            else:
                return {'status': 'error', 'error': f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_deployment_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all deployments and their status.
        """
        deployments = ScrapydDeployment.objects.all()
        
        summary = {
            'total_deployments': deployments.count(),
            'active_deployments': deployments.filter(is_active=True).count(),
            'healthy_deployments': deployments.filter(is_healthy=True).count(),
            'total_active_jobs': sum(d.active_jobs for d in deployments),
            'total_pending_jobs': sum(d.pending_jobs for d in deployments),
            'deployments': []
        }
        
        for deployment in deployments:
            summary['deployments'].append({
                'deployment_id': deployment.deployment_id,
                'node_name': deployment.node_name,
                'project_name': deployment.project_name,
                'host': deployment.host,
                'port': deployment.port,
                'status': deployment.status,
                'is_healthy': deployment.is_healthy,
                'health_score': deployment.health_score,
                'uptime': deployment.uptime_formatted,
                'active_jobs': deployment.active_jobs,
                'pending_jobs': deployment.pending_jobs,
                'can_accept_tasks': deployment.can_accept_tasks
            })
        
        return summary
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """
        Clean up old health logs and completed tasks.
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Clean up old health logs
        health_logs_deleted = ScrapydHealthLog.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]
        
        # Clean up old completed/failed tasks
        old_tasks_deleted = ScrapydTask.objects.filter(
            status__in=['completed', 'failed'],
            completed_at__lt=cutoff_date
        ).delete()[0]
        
        # Clean up old queue entries
        old_queue_deleted = ScrapydTaskQueue.objects.filter(
            status__in=['completed', 'failed'],
            queued_at__lt=cutoff_date
        ).delete()[0]
        
        total_deleted = health_logs_deleted + old_tasks_deleted + old_queue_deleted
        
        logger.info(f"Cleaned up {total_deleted} old records (older than {days} days)")
        return total_deleted
