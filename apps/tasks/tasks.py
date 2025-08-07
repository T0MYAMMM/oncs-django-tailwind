import os, time, subprocess
import datetime
import json
import requests
from os import listdir
from os.path import isfile, join

from .celery import app
from celery.contrib.abortable import AbortableTask
from django_celery_results.models import TaskResult

from django.contrib.auth.models import User
from django.conf import settings
from celery.exceptions import Ignore, TaskError

# Import crawler models
from apps.common.models import CrawlerConfig, CrawlerTask, CrawlerScheduledTask
from django.utils import timezone


def get_scripts():
    """
    Returns all scripts from 'ROOT_DIR/celery_scripts'
    """
    raw_scripts = []
    scripts     = []
    ignored_ext = ['db', 'txt']

    try:
        raw_scripts = [f for f in listdir(settings.CELERY_SCRIPTS_DIR) if isfile(join(settings.CELERY_SCRIPTS_DIR, f))]
    except Exception as e:
        return None, 'Error CELERY_SCRIPTS_DIR: ' + str( e ) 

    for filename in raw_scripts:

        ext = filename.split(".")[-1]
        if ext not in ignored_ext:
           scripts.append( filename )

    return scripts, None           

def write_to_log_file(logs, script_name):
    """
    Writes logs to a log file with formatted name in the CELERY_LOGS_DIR directory.
    """
    script_base_name = os.path.splitext(script_name)[0]  # Remove the .py extension
    current_time = datetime.datetime.now().strftime("%y%m%d-%H%M%S")
    log_file_name = f"{script_base_name}-{current_time}.log"
    log_file_path = os.path.join(settings.CELERY_LOGS_DIR, log_file_name)
    
    with open(log_file_path, 'w') as log_file:
        log_file.write(logs)
    
    return log_file_path

@app.task(bind=True, base=AbortableTask)
def execute_script(self, data: dict):
    """
    This task executes scripts found in settings.CELERY_SCRIPTS_DIR and logs are later generated and stored in settings.CELERY_LOGS_DIR
    :param data dict: contains data needed for task execution. Example `input` which is the script to be executed.
    :rtype: None
    """
    script = data.get("script")
    args   = data.get("args")

    print( '> EXEC [' + script + '] -> ('+args+')' ) 

    scripts, ErrInfo = get_scripts()

    if script and script in scripts:
        # Executing related script
        script_path = os.path.join(settings.CELERY_SCRIPTS_DIR, script)
        process = subprocess.Popen(
            f"python {script_path} {args}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(8)

        exit_code = process.wait()
        error = False
        status = "STARTED"
        if exit_code == 0:  # If script execution successfull
            logs = process.stdout.read().decode()
            status = "SUCCESS"
        else:
            logs = process.stderr.read().decode()
            error = True
            status = "FAILURE"


        log_file = write_to_log_file(logs, script)

        return {"logs": logs, "input": script, "error": error, "output": "", "status": status, "log_file": log_file}


@app.task(bind=True, base=AbortableTask)
def execute_crawler_task(self, crawler_task_id: int):
    """
    Execute a crawler task using ScrapyD
    :param crawler_task_id: ID of the CrawlerTask to execute
    :rtype: dict
    """
    try:
        # Get the crawler task
        crawler_task = CrawlerTask.objects.get(id=crawler_task_id)
        crawler_config = crawler_task.crawler_config
        
        # Update task status to running
        crawler_task.status = 'running'
        crawler_task.started_at = timezone.now()
        crawler_task.save()
        
        print(f"DEBUG: Executing crawler task {crawler_task.id} for config: {crawler_config.name}")
        
        # Prepare ScrapyD request data
        scrapyd_data = {
            'project': 'news_crawler',
            'spider': f"{crawler_config.portal.name.lower()}_spider",
            'settings': json.dumps(crawler_config.custom_settings or {}),
            'jobid': f"crawler_task_{crawler_task.id}_{int(time.time())}"
        }
        
        # For now, just simulate the ScrapyD request (console log)
        print(f"DEBUG: Would send POST request to ScrapyD schedule.json with:")
        print(f"  - Project: {scrapyd_data['project']}")
        print(f"  - Spider: {scrapyd_data['spider']}")
        print(f"  - Settings: {scrapyd_data['settings']}")
        print(f"  - Job ID: {scrapyd_data['jobid']}")
        
        # Simulate processing time
        time.sleep(2)
        
        # Update task status to completed
        crawler_task.status = 'completed'
        crawler_task.completed_at = timezone.now()
        crawler_task.execution_time = crawler_task.completed_at - crawler_task.started_at
        crawler_task.scrapyd_job_id = scrapyd_data['jobid']
        crawler_task.save()
        
        logs = f"Crawler task {crawler_task.id} completed successfully\n"
        logs += f"Config: {crawler_config.name}\n"
        logs += f"Portal: {crawler_config.portal.name}\n"
        logs += f"Execution time: {crawler_task.execution_time}\n"
        
        log_file = write_to_log_file(logs, f"crawler_task_{crawler_task.id}")
        
        return {
            "logs": logs,
            "input": f"crawler_task_{crawler_task.id}",
            "error": False,
            "output": f"Task completed successfully. Job ID: {scrapyd_data['jobid']}",
            "status": "SUCCESS",
            "log_file": log_file
        }
        
    except CrawlerTask.DoesNotExist:
        error_msg = f"Crawler task {crawler_task_id} not found"
        print(f"ERROR: {error_msg}")
        return {
            "logs": error_msg,
            "input": f"crawler_task_{crawler_task_id}",
            "error": True,
            "output": "",
            "status": "FAILURE",
            "log_file": ""
        }
    except Exception as e:
        error_msg = f"Error executing crawler task {crawler_task_id}: {str(e)}"
        print(f"ERROR: {error_msg}")
        
        # Update task status to failed
        try:
            crawler_task = CrawlerTask.objects.get(id=crawler_task_id)
            crawler_task.status = 'failed'
            crawler_task.error_message = str(e)
            crawler_task.completed_at = timezone.now()
            crawler_task.save()
        except:
            pass
        
        return {
            "logs": error_msg,
            "input": f"crawler_task_{crawler_task_id}",
            "error": True,
            "output": "",
            "status": "FAILURE",
            "log_file": ""
        }


@app.task(bind=True, base=AbortableTask)
def execute_scheduled_crawler_task(self, scheduled_task_id: int):
    """
    Execute a scheduled crawler task
    :param scheduled_task_id: ID of the CrawlerScheduledTask to execute
    :rtype: dict
    """
    try:
        # Get the scheduled task
        scheduled_task = CrawlerScheduledTask.objects.get(id=scheduled_task_id)
        
        if not scheduled_task.is_active:
            return {
                "logs": f"Scheduled task {scheduled_task_id} is not active",
                "input": f"scheduled_task_{scheduled_task_id}",
                "error": False,
                "output": "Task skipped - not active",
                "status": "SUCCESS",
                "log_file": ""
            }
        
        # Create a new crawler task
        crawler_task = CrawlerTask.objects.create(
            crawler_config=scheduled_task.crawler_config,
            status='pending'
        )
        
        # Execute the crawler task
        result = execute_crawler_task.delay(crawler_task.id)
        
        # Update scheduled task last_run
        scheduled_task.last_run = timezone.now()
        scheduled_task.save()
        
        logs = f"Scheduled task {scheduled_task_id} executed successfully\n"
        logs += f"Created crawler task: {crawler_task.id}\n"
        logs += f"Celery task ID: {result.id}\n"
        
        log_file = write_to_log_file(logs, f"scheduled_task_{scheduled_task_id}")
        
        return {
            "logs": logs,
            "input": f"scheduled_task_{scheduled_task_id}",
            "error": False,
            "output": f"Scheduled task executed. Crawler task: {crawler_task.id}",
            "status": "SUCCESS",
            "log_file": log_file
        }
        
    except CrawlerScheduledTask.DoesNotExist:
        error_msg = f"Scheduled task {scheduled_task_id} not found"
        print(f"ERROR: {error_msg}")
        return {
            "logs": error_msg,
            "input": f"scheduled_task_{scheduled_task_id}",
            "error": True,
            "output": "",
            "status": "FAILURE",
            "log_file": ""
        }
    except Exception as e:
        error_msg = f"Error executing scheduled task {scheduled_task_id}: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {
            "logs": error_msg,
            "input": f"scheduled_task_{scheduled_task_id}",
            "error": True,
            "output": "",
            "status": "FAILURE",
            "log_file": ""
        }