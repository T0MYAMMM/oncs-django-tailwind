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
from apps.common.models import CrawlerConfig, CrawlerTask, CrawlerScheduledTask, ItemSelector, ItemChoices, SelectorMethodChoices
from apps.tasks.models import ScrapydServer
from apps.tasks.scrapyd_api import get_scrapyd_api, fetch_and_save_logs, fetch_and_save_items, get_job_details
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
    
    # Create the directory if it doesn't exist
    os.makedirs(settings.CELERY_LOGS_DIR, exist_ok=True)
    
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


def _build_generic_spider_payload(crawler_config: CrawlerConfig, worker_id: str = 'celery-worker-001') -> dict:
    """Build payload for generic multipurpose spider based on CrawlerConfig."""
    portal = crawler_config.portal
    custom_settings = crawler_config.custom_settings or {}

    # Determine start URLs: from custom_settings.seed_urls if present, else portal seed_urls
    start_urls = []
    if isinstance(custom_settings.get('seed_urls'), list):
        start_urls = custom_settings.get('seed_urls')
    else:
        start_urls = [s.url for s in portal.seed_urls.all()]

    # Map selector queryset for URL_LIST to config schema
    selectors_config = { 'url_list': [] }
    url_list_selectors = ItemSelector.objects.filter(portal=portal, item=ItemChoices.URL_LIST)
    for sel in url_list_selectors:
        selectors_config['url_list'].append({
            'method': sel.method,
            'query' : sel.query,
        })

    headers = custom_settings.get('headers') or {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
    }

    proxy_settings = custom_settings.get('proxy_settings') or {
        'enable': False,
        'auto_rotate': False,
        'specific_proxy_type': 'local'
    }

    # Ensure allowed_domains is a list
    allowed_domains = [portal.domain] if portal.domain else []

    config_dict = {
        'name': f'{portal.name.lower()}_spider',
        'portal_name': portal.name,
        'portal_domain': portal.domain,
        'start_urls': start_urls[0] if len(start_urls) == 1 else start_urls,
        'allowed_domains': allowed_domains,
        'selectors': selectors_config,
        'headers': headers,
        'proxy_settings': proxy_settings,
        'custom_settings': custom_settings.get('SCRAPY_SETTINGS_JSON') or json.dumps(custom_settings or {})
    }

    # Scrapyd expects these specific fields
    payload = {
        'project': 'scrapy_crawler',
        'spider': 'generic',
        'config_dict': json.dumps(config_dict),
    }

    return payload


def _post_to_scrapyd(server: ScrapydServer, payload: dict) -> dict:
    """Send payload to Scrapyd server with proper error handling."""
    url = f"{server.base_url}/schedule.json"
    
    print(f"DEBUG: Sending request to Scrapyd at {url}")
    print(f"DEBUG: Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # First, let's test if the Scrapyd server is reachable
        test_url = f"{server.base_url}/listprojects.json"
        print(f"DEBUG: Testing Scrapyd connectivity at {test_url}")
        test_response = requests.get(test_url, timeout=5)
        print(f"DEBUG: Scrapyd connectivity test status: {test_response.status_code}")
        
        if test_response.status_code != 200:
            raise RuntimeError(f"Scrapyd server not accessible. Status: {test_response.status_code}")
        
        # Now send the actual request
        response = requests.post(url, data=payload, timeout=15)
        print(f"DEBUG: Scrapyd response status: {response.status_code}")
        print(f"DEBUG: Scrapyd response content: {response.text}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection error to Scrapyd server {server.base_url}: {str(e)}"
        print(f"ERROR: {error_msg}")
        raise RuntimeError(error_msg)
    except requests.exceptions.Timeout as e:
        error_msg = f"Timeout error to Scrapyd server {server.base_url}: {str(e)}"
        print(f"ERROR: {error_msg}")
        raise RuntimeError(error_msg)
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error from Scrapyd server {server.base_url}: {str(e)}"
        print(f"ERROR: {error_msg}")
        print(f"ERROR: Response content: {response.text if 'response' in locals() else 'No response'}")
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error communicating with Scrapyd server {server.base_url}: {str(e)}"
        print(f"ERROR: {error_msg}")
        raise RuntimeError(error_msg)


@app.task(bind=True, base=AbortableTask)
def execute_crawler_task(self, crawler_task_id: int):
    """
    Execute a crawler task using ScrapyD
    :param crawler_task_id: ID of the CrawlerTask to execute
    :rtype: dict
    """
    try:
        print(f"DEBUG: Starting execute_crawler_task for task_id: {crawler_task_id}")
        
        # Get the crawler task
        crawler_task = CrawlerTask.objects.get(id=crawler_task_id)
        crawler_config = crawler_task.crawler_config
        
        print(f"DEBUG: Found crawler_task: {crawler_task.id}, config: {crawler_config.name}")
        
        # Update task status to running
        crawler_task.status = 'running'
        crawler_task.started_at = timezone.now()
        crawler_task.save()
        
        print(f"DEBUG: Executing crawler task {crawler_task.id} for config: {crawler_config.name}")
        
        # Build payload for generic spider
        payload = _build_generic_spider_payload(crawler_config)
        print(f"DEBUG: Built payload: {json.dumps(payload, indent=2)}")

        # Get Scrapyd API
        api = get_scrapyd_api()
        print(f"DEBUG: Using Scrapyd server: {api.base_url}")

        # Send to Scrapyd using the new API
        response_json = api.schedule(**payload)
        print(f"DEBUG: Scrapyd response: {json.dumps(response_json, indent=2)}")
        
        jobid = response_json.get('jobid') or response_json.get('jobid'.upper()) or f"crawler_task_{crawler_task.id}_{int(time.time())}"
        print(f"DEBUG: Extracted jobid: {jobid}")

        # Update task status to completed (queued in Scrapyd)
        crawler_task.status = 'completed'
        crawler_task.completed_at = timezone.now()
        crawler_task.execution_time = crawler_task.completed_at - crawler_task.started_at
        crawler_task.scrapyd_job_id = jobid
        crawler_task.save()

        # Fetch and save logs and items
        log_file = None
        items_file = None
        
        try:
            log_file = fetch_and_save_logs(crawler_task.id)
            print(f"DEBUG: Log file saved: {log_file}")
        except Exception as log_error:
            print(f"WARNING: Could not fetch logs: {log_error}")
        
        try:
            items_file = fetch_and_save_items(crawler_task.id)
            print(f"DEBUG: Items file saved: {items_file}")
        except Exception as items_error:
            print(f"WARNING: Could not fetch items: {items_error}")

        logs = (
            f"Dispatched crawler task {crawler_task.id} to Scrapyd\n"
            f"Server: {api.base_url}\n"
            f"Job ID: {jobid}\n"
            f"Payload: {json.dumps(payload)}\n"
            f"Log file: {log_file or 'Not available'}\n"
            f"Items file: {items_file or 'Not available'}\n"
        )

        # Try to write log file, but don't fail the task if it doesn't work
        try:
            local_log_file = write_to_log_file(logs, f"crawler_task_{crawler_task.id}")
        except Exception as log_error:
            print(f"WARNING: Could not write log file: {log_error}")
            local_log_file = ""

        return {
            "logs": logs,
            "input": f"crawler_task_{crawler_task.id}",
            "error": False,
            "output": f"Queued in Scrapyd. Job ID: {jobid}",
            "status": "SUCCESS",
            "log_file": local_log_file,
            "scrapyd_log_file": log_file,
            "scrapyd_items_file": items_file
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
        import traceback
        print(f"ERROR: Traceback: {traceback.format_exc()}")
        
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