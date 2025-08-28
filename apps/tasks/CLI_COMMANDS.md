# Tasks App CLI Commands

This document provides comprehensive documentation for all CLI commands available in the tasks app.

## 🚀 **Quick Start Examples**

### **Basic Task Management**
```bash
# Create a task for a specific config
python manage.py task_manager create --config-name "kompas_news"

# Execute a task immediately
python manage.py task_manager execute --config-name "kompas_news"

# List all tasks
python manage.py task_manager list

# Check task status
python manage.py task_manager status --task-id 123
```

### **Scheduled Task Management**
```bash
# Create a daily scheduled task
python manage.py schedule_manager create \
  --config-name "kompas_news" \
  --schedule-name "daily_kompas" \
  --cron-expression "0 0 * * *"

# List all scheduled tasks
python manage.py schedule_manager list

# Enable/disable a scheduled task
python manage.py schedule_manager enable --schedule-name "daily_kompas"
python manage.py schedule_manager disable --schedule-name "daily_kompas"
```

### **Monitoring and Health**
```bash
# Get system overview
python manage.py task_monitor overview

# Monitor health status
python manage.py task_monitor health

# Watch metrics in real-time
python manage.py task_monitor watch --interval 5

# Check for system alerts
python manage.py task_monitor alerts
```

## 📋 **Command Reference**

### **1. task_manager - Comprehensive Task Management**

The main command for managing crawler tasks.

#### **Actions Available:**
- `create` - Create a new task
- `execute` - Execute a task
- `list` - List all tasks
- `status` - Show detailed task status
- `cancel` - Cancel a running task
- `schedule` - Schedule a recurring task
- `monitor` - Monitor task status
- `cleanup` - Clean up old tasks

#### **Usage Examples:**

**Create a Task:**
```bash
python manage.py task_manager create --config-name "kompas_news"
```

**Execute a Task:**
```bash
# Execute existing task
python manage.py task_manager execute --task-id 123

# Create and execute new task
python manage.py task_manager execute --config-name "kompas_news"
```

**List Tasks:**
```bash
# List all tasks
python manage.py task_manager list

# List tasks for specific config
python manage.py task_manager list --config-name "kompas_news"

# JSON output
python manage.py task_manager list --json
```

**Task Status:**
```bash
python manage.py task_manager status --task-id 123
```

**Cancel Task:**
```bash
python manage.py task_manager cancel --task-id 123
```

**Schedule Task:**
```bash
python manage.py task_manager schedule \
  --config-name "kompas_news" \
  --schedule-name "daily_kompas" \
  --cron-expression "0 0 * * *"
```

**Monitor Tasks:**
```bash
# Show current status
python manage.py task_manager monitor

# Watch in real-time
python manage.py task_manager monitor --watch --interval 5
```

**Cleanup Tasks:**
```bash
python manage.py task_manager cleanup
```

#### **Parameters:**
- `--config-name` - Name of crawler configuration
- `--task-id` - Task ID for specific operations
- `--worker-id` - Worker identifier
- `--priority` - Task priority (1-10, default: 5)
- `--cron-expression` - Cron expression for scheduling
- `--schedule-name` - Name for scheduled task
- `--watch` - Watch in real-time
- `--interval` - Watch interval in seconds
- `--json` - Output in JSON format
- `--verbose` - Verbose output

---

### **2. schedule_manager - Scheduled Task Management**

Specialized command for managing scheduled tasks.

#### **Actions Available:**
- `create` - Create a new scheduled task
- `list` - List all scheduled tasks
- `enable` - Enable a scheduled task
- `disable` - Disable a scheduled task
- `execute` - Execute a scheduled task immediately
- `delete` - Delete a scheduled task
- `next-run` - Show when task will run next
- `validate` - Validate cron expression

#### **Usage Examples:**

**Create Scheduled Task:**
```bash
python manage.py schedule_manager create \
  --config-name "kompas_news" \
  --schedule-name "daily_kompas" \
  --cron-expression "0 0 * * *" \
  --description "Daily news crawl for Kompas"
```

**List Scheduled Tasks:**
```bash
python manage.py schedule_manager list
```

**Enable/Disable Task:**
```bash
python manage.py schedule_manager enable --schedule-name "daily_kompas"
python manage.py schedule_manager disable --schedule-name "daily_kompas"
```

**Execute Scheduled Task:**
```bash
# Normal execution
python manage.py schedule_manager execute --schedule-name "daily_kompas"

# Force execution even if inactive
python manage.py schedule_manager execute --schedule-name "daily_kompas" --force
```

**Delete Scheduled Task:**
```bash
python manage.py schedule_manager delete --schedule-name "daily_kompas"
```

**Check Next Run:**
```bash
python manage.py schedule_manager next-run --schedule-name "daily_kompas"
```

**Validate Cron Expression:**
```bash
python manage.py schedule_manager validate --cron-expression "0 0 * * *"
```

#### **Parameters:**
- `--schedule-id` - Scheduled task ID
- `--schedule-name` - Scheduled task name
- `--config-name` - Crawler configuration name
- `--cron-expression` - Cron expression
- `--description` - Task description
- `--force` - Force execution
- `--json` - JSON output
- `--verbose` - Verbose output

---

### **3. task_monitor - System Monitoring and Health**

Command for monitoring system health, performance, and status.

#### **Actions Available:**
- `overview` - System overview
- `health` - Health status
- `performance` - Performance metrics
- `deployments` - Deployment status
- `watch` - Real-time monitoring
- `alerts` - System alerts

#### **Usage Examples:**

**System Overview:**
```bash
# Default 24h view
python manage.py task_monitor overview

# Custom time range
python manage.py task_monitor overview --time-range 7d
```

**Health Status:**
```bash
python manage.py task_monitor health --time-range 6h
```

**Performance Metrics:**
```bash
# All portals
python manage.py task_monitor performance

# Specific portal
python manage.py task_monitor performance --portal "kompas"

# Specific config
python manage.py task_monitor performance --config "news"
```

**Deployment Status:**
```bash
python manage.py task_monitor deployments
```

**Real-time Monitoring:**
```bash
# Default 10s interval
python manage.py task_monitor watch

# Custom interval
python manage.py task_monitor watch --interval 5
```

**System Alerts:**
```bash
python manage.py task_monitor alerts --time-range 24h
```

#### **Parameters:**
- `--watch` - Watch in real-time
- `--interval` - Watch interval (default: 10s)
- `--time-range` - Time range: 1h, 6h, 24h, 7d, 30d (default: 24h)
- `--portal` - Filter by portal name
- `--config` - Filter by config name
- `--json` - JSON output
- `--verbose` - Verbose output

---

## ⏰ **Cron Expression Examples**

### **Common Patterns:**
```bash
# Daily at midnight
"0 0 * * *"

# Every hour
"0 * * * *"

# Every 6 hours
"0 */6 * * *"

# Weekdays at 9 AM
"0 9 * * 1-5"

# Every 30 minutes
"*/30 * * * *"

# Twice daily (6 AM and 6 PM)
"0 6,18 * * *"

# Every Monday at 8 AM
"0 8 * * 1"
```

### **Cron Format:**
```
minute hour day month weekday
  |     |    |    |      |
  |     |    |    |      +-- Day of week (0-7, Sunday = 0 or 7)
  |     |    |    +-------- Month (1-12)
  |     |    +------------- Day of month (1-31)
  |     +------------------ Hour (0-23)
  +------------------------ Minute (0-59)
```

---

## 🔧 **Advanced Usage**

### **JSON Output for Scripting:**
```bash
# Get task list in JSON format
python manage.py task_manager list --json > tasks.json

# Get system overview in JSON
python manage.py task_monitor overview --json > overview.json

# Parse in Python
import json
import subprocess

result = subprocess.run([
    'python', 'manage.py', 'task_manager', 'list', '--json'
], capture_output=True, text=True)

tasks = json.loads(result.stdout)
print(f"Total tasks: {tasks['total_tasks']}")
```

### **Real-time Monitoring:**
```bash
# Watch system metrics every 5 seconds
python manage.py task_monitor watch --interval 5

# Monitor specific portal performance
python manage.py task_monitor performance --portal "kompas" --watch --interval 10
```

### **Batch Operations:**
```bash
# Create multiple tasks
for config in "kompas_news" "detik_news" "cnn_news"; do
    python manage.py task_manager create --config-name "$config"
done

# Execute all pending tasks
python manage.py task_manager list --json | \
  jq -r '.tasks[] | select(.status == "pending") | .id' | \
  xargs -I {} python manage.py task_manager execute --task-id {}
```

---

## 🚨 **Troubleshooting**

### **Common Issues:**

**Task Not Found:**
```bash
# Check if config exists
python manage.py task_manager list --config-name "config_name"

# Verify config name spelling
python manage.py task_manager create --config-name "exact_config_name"
```

**Scheduled Task Not Running:**
```bash
# Check if task is active
python manage.py schedule_manager list

# Validate cron expression
python manage.py schedule_manager validate --cron-expression "0 0 * * *"

# Check next run time
python manage.py schedule_manager next-run --schedule-name "task_name"
```

**System Health Issues:**
```bash
# Check overall health
python manage.py task_monitor health

# Look for alerts
python manage.py task_monitor alerts

# Check deployment status
python manage.py task_monitor deployments
```

### **Debug Mode:**
```bash
# Enable verbose output
python manage.py task_manager list --verbose

# Get detailed error information
python manage.py task_monitor overview --verbose
```

---

## 📊 **Performance Tips**

### **For Large Task Lists:**
```bash
# Use JSON output for better parsing
python manage.py task_manager list --json

# Filter by specific config to reduce output
python manage.py task_manager list --config-name "specific_config"
```

### **For Real-time Monitoring:**
```bash
# Use longer intervals for production
python manage.py task_monitor watch --interval 30

# Monitor specific metrics only
python manage.py task_monitor health --time-range 1h
```

### **For Batch Operations:**
```bash
# Use JSON output for scripting
python manage.py task_manager list --json | jq '.tasks[] | .id'

# Combine commands for efficiency
python manage.py task_manager list --json | \
  jq -r '.tasks[] | select(.status == "pending") | "\(.id) \(.crawler_config.name)"'
```

---

## 🔐 **Security Considerations**

- **Access Control**: Ensure only authorized users can run these commands
- **Logging**: All command executions are logged for audit purposes
- **Validation**: Input parameters are validated to prevent injection attacks
- **Environment**: Commands respect Django's environment and settings

---

## 📚 **Integration Examples**

### **With Cron (System Level):**
```bash
# Add to crontab for regular health checks
*/15 * * * * cd /path/to/project && python manage.py task_monitor alerts --time-range 1h
```

### **With Monitoring Systems:**
```bash
# Nagios check
python manage.py task_monitor health --json | jq '.overall_health.health_rate'

# Prometheus metrics
python manage.py task_monitor overview --json | jq '.task_statistics.total_tasks'
```

### **With CI/CD Pipelines:**
```bash
# Pre-deployment health check
python manage.py task_monitor health --time-range 1h

# Post-deployment verification
python manage.py task_monitor overview --time-range 1h
```

---

## 🆘 **Getting Help**

### **Command Help:**
```bash
# General help
python manage.py help

# Command-specific help
python manage.py task_manager --help
python manage.py schedule_manager --help
python manage.py task_monitor --help
```

### **Available Commands:**
```bash
# List all available commands
python manage.py help

# Look for tasks-related commands
python manage.py help | grep -i task
```

---

## 📝 **Notes**

- All commands support both human-readable and JSON output formats
- Commands are designed to be scriptable and automation-friendly
- Real-time monitoring can be stopped with Ctrl+C
- Time ranges are relative to the current time
- All commands respect Django's database transactions and error handling
- Commands automatically handle database connections and cleanup
