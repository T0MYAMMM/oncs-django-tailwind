from django.db import models
from django.utils import timezone
from django.db.models import JSONField
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class ScrapydDeployment(models.Model):
    """
    Model representing Scrapyd deployments from the scrapyd_tracking database.
    This model mirrors the scrapyd_deployments table structure.
    """
    
    # Deployment identification
    deployment_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    node_name = models.CharField(max_length=255, help_text="Scrapyd node identifier")
    project_name = models.CharField(max_length=255, help_text="Scrapy project name")
    
    # Server connection details
    host = models.CharField(max_length=255, help_text="Scrapyd host address")
    port = models.PositiveIntegerField(help_text="Scrapyd port number")
    bind_address = models.CharField(max_length=255, help_text="Bind address for Scrapyd")
    
    # Status and health information
    STATUS_CHOICES = [
        ('starting', 'Starting'),
        ('running', 'Running'),
        ('stopping', 'Stopping'),
        ('stopped', 'Stopped'),
        ('error', 'Error'),
        ('healthy', 'Healthy'),
        ('unhealthy', 'Unhealthy'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='starting')
    
    # Timestamps
    last_status_update = models.DateTimeField(default=timezone.now)
    last_health_check = models.DateTimeField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    stop_time = models.DateTimeField(null=True, blank=True)
    
    # Process information
    pid = models.PositiveIntegerField(null=True, blank=True)
    
    # Health metrics
    is_healthy = models.BooleanField(default=False)
    health_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Health score from 0.0 (unhealthy) to 1.0 (healthy)"
    )
    error_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    
    # Performance metrics
    uptime_seconds = models.FloatField(default=0.0, help_text="Current uptime in seconds")
    active_jobs = models.PositiveIntegerField(default=0)
    finished_jobs = models.PositiveIntegerField(default=0)
    pending_jobs = models.PositiveIntegerField(default=0)
    
    # Configuration
    config_hash = models.CharField(max_length=64, blank=True)
    environment_vars = JSONField(null=True, blank=True)
    
    # Django timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'scrapyd_deployments'
        ordering = ['-last_status_update', '-created_at']
        indexes = [
            models.Index(fields=['node_name']),
            models.Index(fields=['status']),
            models.Index(fields=['is_healthy']),
            models.Index(fields=['host', 'port']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]
    
    def __str__(self):
        return f"{self.node_name} - {self.project_name} ({self.host}:{self.port})"
    
    @property
    def base_url(self):
        """Get the base URL for this Scrapyd instance."""
        return f"http://{self.host}:{self.port}"
    
    @property
    def is_active(self):
        """Check if the deployment is currently active."""
        return self.status in ['running', 'healthy']
    
    @property
    def can_accept_tasks(self):
        """Check if the deployment can accept new tasks."""
        return (self.is_active and 
                self.is_healthy and 
                self.pending_jobs < 100 and  # Reasonable limit
                self.error_count < 10)  # Not too many errors
    
    @property
    def uptime_formatted(self):
        """Get formatted uptime string."""
        if self.uptime_seconds < 60:
            return f"{self.uptime_seconds:.0f}s"
        elif self.uptime_seconds < 3600:
            minutes = self.uptime_seconds / 60
            return f"{minutes:.0f}m"
        else:
            hours = self.uptime_seconds / 3600
            return f"{hours:.1f}h"
    
    def update_health(self, is_healthy, health_score, error_count=None, last_error=None):
        """Update health status and metrics."""
        self.is_healthy = is_healthy
        self.health_score = health_score
        if error_count is not None:
            self.error_count = error_count
        if last_error is not None:
            self.last_error = last_error
        self.last_health_check = timezone.now()
        self.save(update_fields=['is_healthy', 'health_score', 'error_count', 'last_error', 'last_health_check'])
    
    def update_job_counts(self, active, finished, pending):
        """Update job count metrics."""
        self.active_jobs = active
        self.finished_jobs = finished
        self.pending_jobs = pending
        self.save(update_fields=['active_jobs', 'finished_jobs', 'pending_jobs'])


class ScrapydServer(models.Model):
    """
    Legacy model for backward compatibility - now references ScrapydDeployment.
    This model provides a simplified interface for existing code.
    """
    name = models.CharField(max_length=100, help_text="Friendly name, e.g., Production Node")
    host = models.CharField(max_length=255, help_text="Hostname or IP")
    port = models.PositiveIntegerField(default=6800)
    is_active = models.BooleanField(default=True)
    use_https = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Reference to the active deployment
    active_deployment = models.ForeignKey(
        ScrapydDeployment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='legacy_server'
    )
    
    class Meta:
        db_table = 'scrapyd_server'
        ordering = ['-is_active', 'name']
    
    def __str__(self) -> str:
        scheme = 'https' if self.use_https else 'http'
        return f"{self.name} ({scheme}://{self.host}:{self.port})"
    
    @property
    def base_url(self) -> str:
        scheme = 'https' if self.use_https else 'http'
        return f"{scheme}://{self.host}:{self.port}"
    
    @property
    def deployment_status(self):
        """Get the status from the active deployment if available."""
        if self.active_deployment:
            return self.active_deployment.status
        return 'unknown'
    
    @property
    def is_healthy(self):
        """Get health status from the active deployment if available."""
        if self.active_deployment:
            return self.active_deployment.is_healthy
        return False


class ScrapydTask(models.Model):
    """
    Model for managing tasks sent to Scrapyd instances.
    """
    
    # Task identification
    task_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255, help_text="Task/spider name")
    
    # Task configuration
    portal_name = models.CharField(max_length=255, help_text="Portal display name")
    portal_domain = models.CharField(max_length=255, help_text="Target domain")
    start_urls = models.TextField(help_text="Starting URLs (comma-separated)")
    allowed_domains = models.TextField(help_text="Allowed domains (comma-separated)")
    
    # Selector configuration (stored as JSON)
    selectors = JSONField(help_text="CSS/XPath selector configuration")
    
    # Task settings
    worker_id = models.CharField(max_length=100, blank=True, help_text="Worker identifier")
    use_async = models.BooleanField(default=True)
    debug_mode = models.BooleanField(default=False)
    custom_settings = JSONField(null=True, blank=True)
    
    # Task status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    
    # Scrapyd integration
    target_deployment = models.ForeignKey(
        ScrapydDeployment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        help_text="Target Scrapyd deployment for this task"
    )
    scrapyd_job_id = models.CharField(max_length=100, blank=True, help_text="Scrapyd job ID")
    
    # Task metadata
    priority = models.PositiveIntegerField(default=1, help_text="Task priority (1=highest)")
    estimated_duration = models.PositiveIntegerField(null=True, blank=True, help_text="Estimated duration in minutes")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    items_scraped = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    
    class Meta:
        db_table = 'scrapyd_tasks'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['target_deployment']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.portal_name} ({self.status})"
    
    @property
    def duration_minutes(self):
        """Calculate task duration in minutes."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() / 60
        elif self.started_at:
            return (timezone.now() - self.started_at).total_seconds() / 60
        return 0
    
    def assign_to_deployment(self, deployment):
        """Assign this task to a specific Scrapyd deployment."""
        self.target_deployment = deployment
        self.status = 'queued'
        self.save(update_fields=['target_deployment', 'status'])
    
    def start_execution(self):
        """Mark task as started."""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def complete_execution(self, items_scraped=0, error_message=''):
        """Mark task as completed."""
        self.status = 'completed' if not error_message else 'failed'
        self.completed_at = timezone.now()
        self.items_scraped = items_scraped
        if error_message:
            self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'items_scraped', 'error_message'])


class ScrapydTaskQueue(models.Model):
    """
    Model for managing the task queue and load balancing across Scrapyd instances.
    """
    
    # Queue entry
    queue_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    task = models.ForeignKey(ScrapydTask, on_delete=models.CASCADE, related_name='queue_entries')
    
    # Queue management
    priority = models.PositiveIntegerField(default=1, help_text="Queue priority (1=highest)")
    queued_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True, help_text="When to execute this task")
    
    # Assignment
    assigned_deployment = models.ForeignKey(
        ScrapydDeployment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='queued_tasks'
    )
    
    # Status
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('assigned', 'Assigned'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='waiting')
    
    # Retry logic
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'scrapyd_task_queue'
        ordering = ['priority', 'queued_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assigned_deployment']),
            models.Index(fields=['scheduled_for']),
        ]
    
    def __str__(self):
        return f"Queue {self.queue_id} - {self.task.name} ({self.status})"
    
    def assign_to_deployment(self, deployment):
        """Assign this queue entry to a specific deployment."""
        self.assigned_deployment = deployment
        self.status = 'assigned'
        self.save(update_fields=['assigned_deployment', 'status'])
    
    def mark_processing(self):
        """Mark as processing."""
        self.status = 'processing'
        self.save(update_fields=['status'])
    
    def mark_completed(self):
        """Mark as completed."""
        self.status = 'completed'
        self.save(update_fields=['status'])
    
    def mark_failed(self):
        """Mark as failed and handle retry logic."""
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            self.status = 'waiting'
            self.last_retry_at = timezone.now()
            # Exponential backoff: 1min, 2min, 4min, 8min...
            delay_minutes = 2 ** (self.retry_count - 1)
            self.scheduled_for = timezone.now() + timezone.timedelta(minutes=delay_minutes)
            self.save(update_fields=['status', 'retry_count', 'last_retry_at', 'scheduled_for'])
        else:
            self.status = 'failed'
            self.save(update_fields=['status'])


class ScrapydHealthLog(models.Model):
    """
    Model for logging health check results and performance metrics.
    """
    
    log_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    deployment = models.ForeignKey(ScrapydDeployment, on_delete=models.CASCADE, related_name='health_logs')
    
    # Health check results
    timestamp = models.DateTimeField(auto_now_add=True)
    is_healthy = models.BooleanField()
    health_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    
    # Response metrics
    response_time_ms = models.PositiveIntegerField(help_text="Response time in milliseconds")
    status_code = models.PositiveIntegerField(null=True, blank=True)
    
    # Job metrics
    active_jobs = models.PositiveIntegerField()
    pending_jobs = models.PositiveIntegerField()
    finished_jobs = models.PositiveIntegerField()
    
    # Error information
    error_message = models.TextField(blank=True)
    error_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'scrapyd_health_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['deployment', 'timestamp']),
            models.Index(fields=['is_healthy']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        status = "✅" if self.is_healthy else "❌"
        return f"{status} {self.deployment.node_name} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

