import os
import time
import json

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from celery import current_app
from apps.tasks.tasks import execute_script, get_scripts, execute_crawler_task, execute_scheduled_crawler_task
from django_celery_results.models import TaskResult
from celery.contrib.abortable import AbortableAsyncResult
from apps.tasks.celery import app
from django.http import HttpResponse, Http404
from os import listdir
from os.path import isfile, join
from django.conf import settings

from django.template  import loader

# Import crawler models
from apps.common.models import CrawlerConfig, CrawlerTask, CrawlerScheduledTask, NewsPortalSeedUrl

# Import Scrapyd API
from apps.tasks.scrapyd_api import get_scrapyd_api, fetch_and_save_logs, fetch_and_save_items, get_job_details, ScrapydAPIError

# Create your views here.

def index(request):
    return HttpResponse("INDEX Tasks")



# @login_required(login_url="/login/")
def summary(request):

    scripts, ErrInfo = get_scripts()
 
    context = {
            'cfgError' : ErrInfo,
            'tasks'    : get_celery_all_tasks(),
            'scripts'  : scripts,
            'segment'  : 'tasks',
            'parent'   : 'tasks',
        }

    # django_celery_results_task_result
    task_results = TaskResult.objects.all()
    context["task_results"] = task_results
    
    # Add crawler tasks and scheduled tasks
    crawler_tasks = CrawlerTask.objects.select_related('crawler_config', 'crawler_config__portal').all().order_by('-created_at')[:10]
    scheduled_tasks = CrawlerScheduledTask.objects.select_related('crawler_config', 'crawler_config__portal').all().order_by('-created_at')[:10]
    crawler_configs = CrawlerConfig.objects.select_related('portal').all()
    
    # Add seed URLs data
    seed_urls = NewsPortalSeedUrl.objects.select_related('portal').all()
    
    context["crawler_tasks"] = crawler_tasks
    context["scheduled_tasks"] = scheduled_tasks
    context["crawler_configs"] = crawler_configs
    context["seed_urls"] = seed_urls

    return render(request, 'pages/tasks/summary.html', context)


def crawler(request):
    scripts, ErrInfo = get_scripts()
    crawler_tasks = CrawlerTask.objects.select_related('crawler_config', 'crawler_config__portal').all().order_by('-created_at')[:10]
    scheduled_tasks = CrawlerScheduledTask.objects.select_related('crawler_config', 'crawler_config__portal').all().order_by('-created_at')[:10]
    crawler_configs = CrawlerConfig.objects.select_related('portal').all()
    seed_urls = NewsPortalSeedUrl.objects.select_related('portal').all()

    context = {
        'cfgError': ErrInfo,
        'scripts': scripts,
        'crawler_tasks': crawler_tasks,
        'scheduled_tasks': scheduled_tasks,
        'crawler_configs': crawler_configs,
        'seed_urls': seed_urls,
        'segment': 'crawler',
        'parent': 'tasks',
    }

    return render(request, 'pages/tasks/crawler.html', context)

def run_task(request, task_name):
    '''
    Runs a celery task
    :param request HttpRequest: Request
    :param task_name str: Name of task to execute
    :rtype: (HttpResponseRedirect | HttpResponsePermanentRedirect)
    '''
    tasks = [execute_script]
    _script = request.POST.get("script")
    _args   = request.POST.get("args")
    for task in tasks:
        if task.__name__ == task_name:
            task.delay({"script": _script, "args": _args})
    time.sleep(1)  # Waiting for task status to update in db

    return redirect("tasks:tasks") 

def cancel_task(request, task_id):
    '''
    Cancels a celery task using its task id
    :param request HttpRequest: Request
    :param task_id str: task_id of result to cancel execution
    :rtype: (HttpResponseRedirect | HttpResponsePermanentRedirect)
    '''
    result = TaskResult.objects.get(task_id=task_id)
    abortable_result = AbortableAsyncResult(
        result.task_id, task_name=result.task_name, app=app)
    if not abortable_result.is_aborted():
        abortable_result.revoke(terminate=True)
    time.sleep(1)
    return redirect("tasks:tasks")

def get_celery_all_tasks():
    current_app.loader.import_default_modules()
    tasks = list(sorted(name for name in current_app.tasks
                        if not name.startswith('celery.')))
    tasks = [{"name": name.split(".")[-1], "script":name} for name in tasks]
    for task in tasks:
        last_task = TaskResult.objects.filter(
            task_name=task["script"]).order_by("date_created").last()
        if last_task:
            task["id"] = last_task.task_id
            task["has_result"] = True
            task["status"] = last_task.status
            task["successfull"] = last_task.status == "SUCCESS" or last_task.status == "STARTED"
            task["date_created"] = last_task.date_created
            task["date_done"] = last_task.date_done
            task["result"] = last_task.result

            try:
                task["input"] = json.loads(last_task.result).get("input")
            except:
                task["input"] = ''
                
    return tasks

def task_output(request):
    '''
    Returns a task output 
    '''

    task_id = request.GET.get('task_id')
    task    = TaskResult.objects.get(id=task_id)

    if not task:
        return ''

    # task.result -> JSON Format
    return HttpResponse( task.result )

def task_log(request):
    '''
    Returns a task LOG file (if located on disk) 
    '''

    task_id  = request.GET.get('task_id')
    task     = TaskResult.objects.get(id=task_id)
    task_log = 'NOT FOUND'

    if not task: 
        return ''

    try: 

        # Get logs file
        all_logs = [f for f in listdir(settings.CELERY_LOGS_DIR) if isfile(join(settings.CELERY_LOGS_DIR, f))]
        
        for log in all_logs:

            # Task HASH name is saved in the log name
            if task.task_id in log:
                
                with open( os.path.join( settings.CELERY_LOGS_DIR, log) ) as f:
                    
                    # task_log -> JSON Format
                    task_log = f.readlines() 

                break    
    
    except Exception as e:

         task_log = json.dumps( { 'Error CELERY_LOGS_DIR: ' : str( e) } )

    return HttpResponse(task_log)

def download_log_file(request, file_path):
    """
    Downloads a log file
    :param request HttpRequest: Request
    :param file_path str: Path to the log file
    :rtype: HttpResponse
    """
    try:
        # Construct the full path to the log file
        log_file_path = os.path.join(settings.CELERY_LOGS_DIR, file_path)
        
        # Check if the file exists
        if not os.path.exists(log_file_path):
            raise Http404("Log file not found")
        
        # Read the file content
        with open(log_file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{file_path}"'
            return response
            
    except Exception as e:
        raise Http404(f"Error downloading log file: {str(e)}")


# Crawler Task Management Views
def create_crawler_task(request):
    """
    Create a new crawler task
    """
    if request.method == 'POST':
        crawler_config_id = request.POST.get('crawler_config')
        try:
            crawler_config = CrawlerConfig.objects.get(id=crawler_config_id)
            crawler_task = CrawlerTask.objects.create(
                crawler_config=crawler_config,
                status='pending'
            )
            
            # Execute the task using Celery
            result = execute_crawler_task.delay(crawler_task.id)
            
            print(f"Created crawler task {crawler_task.id} with Celery task {result.id}")
            
        except CrawlerConfig.DoesNotExist:
            print(f"Crawler config {crawler_config_id} not found")
        except Exception as e:
            print(f"Error creating crawler task: {str(e)}")
    
    return redirect('tasks:tasks')


def create_scheduled_crawler_task(request):
    """
    Create a new scheduled crawler task
    """
    if request.method == 'POST':
        crawler_config_id = request.POST.get('crawler_config')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        cron_expression = request.POST.get('cron_expression')
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            crawler_config = CrawlerConfig.objects.get(id=crawler_config_id)
            scheduled_task = CrawlerScheduledTask.objects.create(
                crawler_config=crawler_config,
                name=name,
                description=description,
                cron_expression=cron_expression,
                is_active=is_active
            )
            
            print(f"Created scheduled crawler task {scheduled_task.id}")
            
        except CrawlerConfig.DoesNotExist:
            print(f"Crawler config {crawler_config_id} not found")
        except Exception as e:
            print(f"Error creating scheduled crawler task: {str(e)}")
    
    return redirect('tasks:tasks')


def execute_crawler_task_view(request, task_id):
    """
    Execute a specific crawler task
    """
    if request.method == 'POST':
        try:
            crawler_task = CrawlerTask.objects.get(id=task_id)
            if crawler_task.status == 'pending':
                # Execute the task using Celery
                result = execute_crawler_task.delay(crawler_task.id)
                print(f"Executing crawler task {crawler_task.id} with Celery task {result.id}")
            else:
                print(f"Crawler task {crawler_task.id} is not in pending status")
        except CrawlerTask.DoesNotExist:
            print(f"Crawler task {task_id} not found")
        except Exception as e:
            print(f"Error executing crawler task: {str(e)}")
    
    return redirect('tasks:tasks')


def execute_scheduled_crawler_task_view(request, scheduled_task_id):
    """
    Execute a specific scheduled crawler task
    """
    if request.method == 'POST':
        try:
            scheduled_task = CrawlerScheduledTask.objects.get(id=scheduled_task_id)
            if scheduled_task.is_active:
                # Execute the scheduled task using Celery
                result = execute_scheduled_crawler_task.delay(scheduled_task.id)
                print(f"Executing scheduled crawler task {scheduled_task.id} with Celery task {result.id}")
            else:
                print(f"Scheduled crawler task {scheduled_task.id} is not active")
        except CrawlerScheduledTask.DoesNotExist:
            print(f"Scheduled crawler task {scheduled_task_id} not found")
        except Exception as e:
            print(f"Error executing scheduled crawler task: {str(e)}")
    
    return redirect('tasks:tasks')


# Scrapyd API Views
def scrapyd_job_details(request, task_id):
    """
    Get comprehensive job details including status, logs, and items
    """
    try:
        crawler_task = get_object_or_404(CrawlerTask, id=task_id)
        job_details = get_job_details(task_id)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(job_details)
        
        context = {
            'task': crawler_task,
            'job_details': job_details,
            'segment': 'tasks',
            'parent': 'tasks',
        }
        return render(request, 'pages/tasks/job_details.html', context)
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=500)
        return HttpResponse(f"Error: {str(e)}", status=500)


def scrapyd_fetch_logs(request, task_id):
    """
    Fetch and save logs from Scrapyd
    """
    try:
        crawler_task = get_object_or_404(CrawlerTask, id=task_id)
        
        if not crawler_task.scrapyd_job_id:
            return JsonResponse({'error': 'No Scrapyd job ID found'}, status=400)
        
        log_file = fetch_and_save_logs(task_id)
        
        if log_file:
            return JsonResponse({
                'success': True,
                'message': 'Logs fetched and saved successfully',
                'log_file': log_file
            })
        else:
            return JsonResponse({'error': 'Failed to fetch logs'}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def scrapyd_fetch_items(request, task_id):
    """
    Fetch and save items from Scrapyd
    """
    try:
        crawler_task = get_object_or_404(CrawlerTask, id=task_id)
        
        if not crawler_task.scrapyd_job_id:
            return JsonResponse({'error': 'No Scrapyd job ID found'}, status=400)
        
        items_file = fetch_and_save_items(task_id)
        
        if items_file:
            return JsonResponse({
                'success': True,
                'message': 'Items fetched and saved successfully',
                'items_file': items_file
            })
        else:
            return JsonResponse({'error': 'Failed to fetch items'}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def scrapyd_cancel_job(request, task_id):
    """
    Cancel a running Scrapyd job
    """
    try:
        crawler_task = get_object_or_404(CrawlerTask, id=task_id)
        
        if not crawler_task.scrapyd_job_id:
            return JsonResponse({'error': 'No Scrapyd job ID found'}, status=400)
        
        api = get_scrapyd_api()
        result = api.cancel('scrapy_crawler', crawler_task.scrapyd_job_id)
        
        # Update task status
        crawler_task.status = 'cancelled'
        crawler_task.completed_at = timezone.now()
        crawler_task.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Job cancelled successfully',
            'result': result
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def scrapyd_list_jobs(request):
    """
    List all jobs from Scrapyd
    """
    try:
        api = get_scrapyd_api()
        jobs = api.listjobs('scrapy_crawler')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(jobs)
        
        context = {
            'jobs': jobs,
            'segment': 'tasks',
            'parent': 'tasks',
        }
        return render(request, 'pages/tasks/scrapyd_jobs.html', context)
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=500)
        return HttpResponse(f"Error: {str(e)}", status=500)


def scrapyd_server_status(request):
    """
    Get Scrapyd server status and information
    """
    try:
        api = get_scrapyd_api()
        
        # Get various server information
        projects = api.listprojects()
        jobs = api.listjobs('scrapy_crawler') if 'scrapy_crawler' in projects.get('projects', []) else {}
        
        server_info = {
            'server_url': api.base_url,
            'projects': projects,
            'jobs': jobs,
            'total_jobs': sum(len(jobs.get(status, [])) for status in ['pending', 'running', 'finished'])
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(server_info)
        
        context = {
            'server_info': server_info,
            'segment': 'tasks',
            'parent': 'tasks',
        }
        return render(request, 'pages/tasks/scrapyd_status.html', context)
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=500)
        return HttpResponse(f"Error: {str(e)}", status=500)