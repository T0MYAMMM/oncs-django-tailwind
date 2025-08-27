# Tasks App - Scrapyd Integration

The Tasks app has been enhanced with comprehensive Scrapyd integration capabilities, allowing you to monitor Scrapyd deployments, manage tasks, and automatically distribute work based on server availability and health.

## Overview

This system integrates with the Scrapyd Generic Crawler deployment tracking system to provide:

- **Real-time Deployment Monitoring**: Track Scrapyd server health and status
- **Intelligent Task Distribution**: Automatically assign tasks to the best available servers
- **Load Balancing**: Distribute tasks based on server capacity and health
- **Health Monitoring**: Continuous health checks with detailed metrics
- **Task Queue Management**: Robust queuing system with retry logic

## Architecture

### Models

1. **ScrapydDeployment**: Mirrors the `scrapyd_deployments` table from the tracking database
2. **ScrapydTask**: Represents individual crawling tasks
3. **ScrapydTaskQueue**: Manages task queuing and load balancing
4. **ScrapydHealthLog**: Tracks health check results and performance metrics
5. **ScrapydServer**: Legacy model for backward compatibility

### Database Structure

The system uses two databases:
- **Default Django Database**: Contains legacy models and Django-specific data
- **Scrapyd Tracking Database**: Contains deployment tracking information

## Setup

### 1. Environment Variables

Add these variables to your `.env` file:

```bash
# Scrapyd Tracking Database
SCRAPYD_DB_ENGINE=postgresql
SCRAPYD_DB_NAME=scrapyd_tracking
SCRAPYD_DB_USER=scrapyd_admin
SCRAPYD_DB_PASS=your_password
SCRAPYD_DB_HOST=localhost
SCRAPYD_DB_PORT=5432

# Scrapyd Authentication (if enabled)
SCRAPYD_USERNAME=admin
SCRAPYD_PASSWORD=secure_password
```

### 2. Database Configuration

Add the scrapyd_tracking database to your Django settings:

```python
# settings.py
DATABASES = {
    'default': {
        # Your existing database configuration
    },
    'scrapyd_tracking': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'scrapyd_tracking',
        'USER': 'scrapyd_admin',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Database Router
DATABASE_ROUTERS = ['apps.tasks.db_router.ScrapydRouter']
```

### 3. Install Dependencies

```bash
pip install psycopg2-binary  # For PostgreSQL support
```

## Usage

### 1. Sync Deployment Data

First, sync deployment information from the tracking database:

```bash
# Dry run to see what would be synced
python manage.py sync_scrapyd_deployments --dry-run

# Sync deployments
python manage.py sync_scrapyd_deployments

# Sync with cleanup of old records
python manage.py sync_scrapyd_deployments --cleanup

# Force sync even with errors
python manage.py sync_scrapyd_deployments --force
```

### 2. Monitor Deployments

```python
from apps.tasks.scrapyd_service import ScrapydService

service = ScrapydService()

# Get deployment summary
summary = service.get_deployment_summary()
print(f"Active deployments: {summary['active_deployments']}")
print(f"Healthy deployments: {summary['healthy_deployments']}")

# Check specific deployment health
deployment = ScrapydDeployment.objects.first()
health = service.check_deployment_health(deployment)
print(f"Health: {health['is_healthy']}")
```

### 3. Create and Queue Tasks

```python
from apps.tasks.models import ScrapydTask

# Create a new task
task = ScrapydTask.objects.create(
    name='kompas_news_spider',
    portal_name='Kompas News',
    portal_domain='kompas.com',
    start_urls='https://indeks.kompas.com',
    allowed_domains='kompas.com',
    selectors={
        'url_list': [
            {'method': 'css', 'query': 'a.article-link::attr(href)'}
        ]
    },
    worker_id='worker-kompas-001',
    priority=1
)

# Queue the task for execution
service = ScrapydService()
success = service.queue_task(task)

if success:
    print(f"Task queued successfully with job ID: {task.scrapyd_job_id}")
else:
    print("Task queued but waiting for available deployment")
```

### 4. Monitor Task Status

```python
# Monitor task execution
status = service.monitor_task_status(task)
print(f"Task status: {status['status']}")

if status['status'] == 'completed':
    print(f"Items scraped: {status['items_scraped']}")
elif status['status'] == 'running':
    print(f"Started at: {status['start_time']}")
```

## API Endpoints

### Deployment Status

```python
# Get all deployments
deployments = ScrapydDeployment.objects.all()

# Get healthy deployments
healthy = ScrapydDeployment.objects.filter(is_healthy=True)

# Get deployments that can accept tasks
available = ScrapydDeployment.objects.filter(
    is_active=True,
    is_healthy=True,
    pending_jobs__lt=100
)
```

### Task Management

```python
# Get all tasks
tasks = ScrapydTask.objects.all()

# Get tasks by status
pending = ScrapydTask.objects.filter(status='pending')
running = ScrapydTask.objects.filter(status='running')
completed = ScrapydTask.objects.filter(status='completed')

# Get tasks by priority
high_priority = ScrapydTask.objects.filter(priority=1)
```

### Queue Management

```python
# Get queue entries
queue = ScrapydTaskQueue.objects.all()

# Get waiting tasks
waiting = ScrapydTaskQueue.objects.filter(status='waiting')

# Get assigned tasks
assigned = ScrapydTaskQueue.objects.filter(status='assigned')
```

## Load Balancing

The system automatically balances tasks across available deployments based on:

1. **Health Score** (40% weight): Overall deployment health
2. **Load Factor** (30% weight): Number of pending jobs
3. **Error Rate** (20% weight): Recent error count
4. **Uptime** (10% weight): Deployment stability

```python
# Find best deployment for a task
best_deployment = service.find_best_deployment_for_task(task)

if best_deployment:
    print(f"Best deployment: {best_deployment.node_name}")
    print(f"Health score: {best_deployment.health_score}")
    print(f"Pending jobs: {best_deployment.pending_jobs}")
```

## Health Monitoring

### Automatic Health Checks

The system performs health checks by calling Scrapyd's `/daemonstatus.json` endpoint:

```python
# Check deployment health
health = service.check_deployment_health(deployment)

# Health check results
print(f"Healthy: {health['is_healthy']}")
print(f"Response time: {health['response_time_ms']}ms")
print(f"Active jobs: {health['active_jobs']}")
print(f"Pending jobs: {health['pending_jobs']}")
```

### Health Logs

All health check results are logged with detailed metrics:

```python
# Get recent health logs
recent_logs = ScrapydHealthLog.objects.filter(
    deployment=deployment
).order_by('-timestamp')[:10]

for log in recent_logs:
    print(f"{log.timestamp}: {log.is_healthy} - {log.response_time_ms}ms")
```

## Task Configuration

### Task Definition

Tasks are defined using a JSON configuration structure:

```json
{
    "name": "spider_name",
    "portal_name": "Portal Display Name",
    "portal_domain": "example.com",
    "start_urls": "https://example.com",
    "allowed_domains": "example.com",
    "selectors": {
        "url_list": [
            {"method": "css", "query": "a[href]"},
            {"method": "xpath", "query": "//a/@href"}
        ]
    },
    "worker_id": "worker-001",
    "use_async": true,
    "debug_mode": false,
    "custom_settings": {
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS": 16
    }
}
```

### Priority System

Tasks support priority levels (1 = highest):

```python
# High priority task
high_priority_task = ScrapydTask.objects.create(
    name='urgent_spider',
    priority=1,
    # ... other fields
)

# Normal priority task
normal_task = ScrapydTask.objects.create(
    name='normal_spider',
    priority=5,
    # ... other fields
)
```

## Error Handling

### Retry Logic

The queue system includes automatic retry with exponential backoff:

```python
# Queue entry with retry logic
queue_entry = ScrapydTaskQueue.objects.create(
    task=task,
    max_retries=3
)

# Failed tasks are automatically retried
if queue_entry.status == 'failed' and queue_entry.retry_count < queue_entry.max_retries:
    # System will retry with increasing delays: 1min, 2min, 4min
    pass
```

### Error Tracking

All errors are logged and tracked:

```python
# Get deployments with errors
error_deployments = ScrapydDeployment.objects.filter(
    error_count__gt=0
).order_by('-error_count')

for deployment in error_deployments:
    print(f"{deployment.node_name}: {deployment.error_count} errors")
    print(f"Last error: {deployment.last_error}")
```

## Maintenance

### Cleanup Operations

```python
# Clean up old records
deleted_count = service.cleanup_old_records(days=30)
print(f"Cleaned up {deleted_count} old records")

# Manual cleanup via management command
python manage.py sync_scrapyd_deployments --cleanup
```

### Database Maintenance

```bash
# Sync deployments
python manage.py sync_scrapyd_deployments

# Check database connections
python manage.py dbshell --database=scrapyd_tracking
```

## Monitoring and Alerts

### Health Status Dashboard

The admin interface provides a comprehensive view of:

- Deployment health and status
- Task execution progress
- Queue status and load
- Performance metrics
- Error rates and logs

### Key Metrics

Monitor these key performance indicators:

1. **Deployment Health**: Percentage of healthy deployments
2. **Task Success Rate**: Completed vs failed tasks
3. **Queue Length**: Number of waiting tasks
4. **Response Times**: Health check response times
5. **Error Rates**: Error counts per deployment

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check database credentials and network connectivity
   - Verify the scrapyd_tracking database exists

2. **Deployments Not Syncing**
   - Run the sync command with `--verbose` flag
   - Check database permissions for the scrapyd_admin user

3. **Tasks Not Executing**
   - Verify Scrapyd instances are running and healthy
   - Check deployment health status
   - Review task configuration

4. **Authentication Errors**
   - Set SCRAPYD_USERNAME and SCRAPYD_PASSWORD if authentication is enabled
   - Verify credentials are correct

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.getLogger('apps.tasks').setLevel(logging.DEBUG)
```

## Integration with Existing Systems

### Legacy Compatibility

The system maintains backward compatibility with existing ScrapydServer models:

```python
# Legacy server now references active deployment
server = ScrapydServer.objects.first()
if server.active_deployment:
    print(f"Server health: {server.active_deployment.is_healthy}")
    print(f"Deployment status: {server.active_deployment.status}")
```

### Migration Path

1. **Phase 1**: Deploy new models alongside existing ones
2. **Phase 2**: Sync deployment data from tracking database
3. **Phase 3**: Update legacy server references
4. **Phase 4**: Gradually migrate to new task management system

## Performance Considerations

### Database Optimization

- Use database indexes for frequently queried fields
- Implement connection pooling for external database connections
- Regular cleanup of old health logs and completed tasks

### Task Distribution

- Limit concurrent tasks per deployment based on capacity
- Implement rate limiting for health checks
- Use background tasks for non-critical operations

## Security

### Authentication

- Support for Scrapyd username/password authentication
- Secure storage of database credentials
- Network-level security for database connections

### Access Control

- Admin interface access control
- API endpoint protection
- Database user permissions

## Future Enhancements

### Planned Features

1. **Real-time Monitoring**: WebSocket-based live updates
2. **Advanced Load Balancing**: Machine learning-based task distribution
3. **Auto-scaling**: Automatic deployment scaling based on load
4. **Metrics Export**: Prometheus/Grafana integration
5. **Alert System**: Email/Slack notifications for critical issues

### API Extensions

1. **REST API**: Full REST API for task management
2. **Webhook Support**: Notifications for task status changes
3. **Batch Operations**: Bulk task creation and management
4. **Scheduling**: Cron-like task scheduling

## Support

For issues and questions:

1. Check the admin interface for deployment status
2. Review health logs for error details
3. Use the management commands for troubleshooting
4. Check the Scrapyd Generic Crawler documentation

## License

This system is part of the ONCS project and follows the same licensing terms.
