from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    ScrapydDeployment, ScrapydServer, ScrapydTask, 
    ScrapydTaskQueue, ScrapydHealthLog
)


@admin.register(ScrapydDeployment)
class ScrapydDeploymentAdmin(admin.ModelAdmin):
    list_display = [
        'deployment_id_short', 'node_name', 'project_name', 'host_port', 
        'status', 'health_status', 'uptime_formatted', 'job_counts', 'last_update'
    ]
    list_filter = [
        'status', 'is_healthy', 'node_name', 'project_name', 'host'
    ]
    search_fields = ['deployment_id', 'node_name', 'project_name', 'host']
    readonly_fields = [
        'deployment_id', 'created_at', 'updated_at', 'uptime_formatted'
    ]
    ordering = ['-last_status_update']
    
    fieldsets = (
        ('Identification', {
            'fields': ('deployment_id', 'node_name', 'project_name')
        }),
        ('Server Details', {
            'fields': ('host', 'port', 'bind_address')
        }),
        ('Status & Health', {
            'fields': ('status', 'is_healthy', 'health_score', 'error_count', 'last_error')
        }),
        ('Job Metrics', {
            'fields': ('active_jobs', 'finished_jobs', 'pending_jobs', 'uptime_seconds')
        }),
        ('Timestamps', {
            'fields': ('start_time', 'stop_time', 'last_status_update', 'last_health_check')
        }),
        ('Configuration', {
            'fields': ('pid', 'config_hash', 'environment_vars')
        }),
        ('System', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def deployment_id_short(self, obj):
        return obj.deployment_id[:8] + '...'
    deployment_id_short.short_description = 'Deployment ID'
    
    def host_port(self, obj):
        return f"{obj.host}:{obj.port}"
    host_port.short_description = 'Host:Port'
    
    def health_status(self, obj):
        if obj.is_healthy:
            return format_html('<span style="color: green;">✅ Healthy</span>')
        else:
            return format_html('<span style="color: red;">❌ Unhealthy</span>')
    health_status.short_description = 'Health'
    
    def job_counts(self, obj):
        return f"A:{obj.active_jobs} P:{obj.pending_jobs} F:{obj.finished_jobs}"
    job_counts.short_description = 'Jobs (Active/Pending/Finished)'
    
    def last_update(self, obj):
        return obj.last_status_update.strftime('%Y-%m-%d %H:%M:%S')
    last_update.short_description = 'Last Update'


@admin.register(ScrapydServer)
class ScrapydServerAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'host_port', 'is_active', 'deployment_status', 
        'health_status', 'created_at'
    ]
    list_filter = ['is_active', 'use_https']
    search_fields = ['name', 'host']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Server Information', {
            'fields': ('name', 'host', 'port', 'use_https', 'is_active')
        }),
        ('Deployment Link', {
            'fields': ('active_deployment',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def host_port(self, obj):
        scheme = 'https' if obj.use_https else 'http'
        return f"{scheme}://{obj.host}:{obj.port}"
    host_port.short_description = 'Server URL'
    
    def deployment_status(self, obj):
        if obj.active_deployment:
            return obj.active_deployment.status
        return 'No deployment'
    deployment_status.short_description = 'Deployment Status'
    
    def health_status(self, obj):
        if obj.active_deployment and obj.active_deployment.is_healthy:
            return format_html('<span style="color: green;">✅ Healthy</span>')
        elif obj.active_deployment:
            return format_html('<span style="color: red;">❌ Unhealthy</span>')
        else:
            return format_html('<span style="color: gray;">⚪ Unknown</span>')
    health_status.short_description = 'Health'


@admin.register(ScrapydTask)
class ScrapydTaskAdmin(admin.ModelAdmin):
    list_display = [
        'task_id_short', 'name', 'portal_name', 'status', 'priority',
        'target_deployment_short', 'items_scraped', 'created_at'
    ]
    list_filter = ['status', 'priority', 'use_async', 'debug_mode']
    search_fields = ['name', 'portal_name', 'portal_domain', 'worker_id']
    readonly_fields = ['task_id', 'created_at', 'updated_at', 'duration_minutes']
    ordering = ['-priority', '-created_at']
    
    fieldsets = (
        ('Task Information', {
            'fields': ('task_id', 'name', 'portal_name', 'portal_domain')
        }),
        ('Configuration', {
            'fields': ('start_urls', 'allowed_domains', 'selectors', 'custom_settings')
        }),
        ('Settings', {
            'fields': ('worker_id', 'use_async', 'debug_mode', 'priority', 'estimated_duration')
        }),
        ('Execution', {
            'fields': ('status', 'target_deployment', 'scrapyd_job_id')
        }),
        ('Results', {
            'fields': ('items_scraped', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at', 'duration_minutes')
        }),
        ('System', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def task_id_short(self, obj):
        return obj.task_id[:8] + '...'
    task_id_short.short_description = 'Task ID'
    
    def target_deployment_short(self, obj):
        if obj.target_deployment:
            return f"{obj.target_deployment.node_name} ({obj.target_deployment.host}:{obj.target_deployment.port})"
        return 'Not assigned'
    target_deployment_short.short_description = 'Target Deployment'


@admin.register(ScrapydTaskQueue)
class ScrapydTaskQueueAdmin(admin.ModelAdmin):
    list_display = [
        'queue_id_short', 'task_name', 'status', 'priority', 
        'assigned_deployment_short', 'retry_count', 'queued_at'
    ]
    list_filter = ['status', 'priority']
    search_fields = ['task__name', 'task__portal_name']
    readonly_fields = ['queue_id', 'queued_at', 'last_retry_at']
    ordering = ['priority', 'queued_at']
    
    fieldsets = (
        ('Queue Information', {
            'fields': ('queue_id', 'task', 'priority', 'status')
        }),
        ('Assignment', {
            'fields': ('assigned_deployment', 'scheduled_for')
        }),
        ('Retry Logic', {
            'fields': ('retry_count', 'max_retries', 'last_retry_at')
        }),
        ('Timestamps', {
            'fields': ('queued_at',)
        })
    )
    
    def queue_id_short(self, obj):
        return obj.queue_id[:8] + '...'
    queue_id_short.short_description = 'Queue ID'
    
    def task_name(self, obj):
        return obj.task.name
    task_name.short_description = 'Task Name'
    
    def assigned_deployment_short(self, obj):
        if obj.assigned_deployment:
            return f"{obj.assigned_deployment.node_name} ({obj.assigned_deployment.host}:{obj.assigned_deployment.port})"
        return 'Not assigned'
    assigned_deployment_short.short_description = 'Assigned Deployment'


@admin.register(ScrapydHealthLog)
class ScrapydHealthLogAdmin(admin.ModelAdmin):
    list_display = [
        'log_id_short', 'deployment_short', 'health_status', 'health_score',
        'response_time', 'job_counts', 'timestamp'
    ]
    list_filter = ['is_healthy', 'timestamp']
    search_fields = ['deployment__node_name', 'deployment__host']
    readonly_fields = ['log_id', 'timestamp']
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Log Information', {
            'fields': ('log_id', 'deployment', 'timestamp')
        }),
        ('Health Check Results', {
            'fields': ('is_healthy', 'health_score', 'response_time_ms')
        }),
        ('Response Details', {
            'fields': ('status_code', 'error_message')
        }),
        ('Job Metrics', {
            'fields': ('active_jobs', 'pending_jobs', 'finished_jobs', 'error_count')
        })
    )
    
    def log_id_short(self, obj):
        return obj.log_id[:8] + '...'
    log_id_short.short_description = 'Log ID'
    
    def deployment_short(self, obj):
        return f"{obj.deployment.node_name} ({obj.deployment.host}:{obj.deployment.port})"
    deployment_short.short_description = 'Deployment'
    
    def health_status(self, obj):
        if obj.is_healthy:
            return format_html('<span style="color: green;">✅ Healthy</span>')
        else:
            return format_html('<span style="color: red;">❌ Unhealthy</span>')
    health_status.short_description = 'Health'
    
    def response_time(self, obj):
        return f"{obj.response_time_ms}ms"
    response_time.short_description = 'Response Time'
    
    def job_counts(self, obj):
        return f"A:{obj.active_jobs} P:{obj.pending_jobs} F:{obj.finished_jobs}"
    job_counts.short_description = 'Jobs (Active/Pending/Finished)'
